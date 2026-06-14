"""Unified AI client — routes to Gemini or OpenAI based on ``AI_PROVIDER``.

Higher-level modules call ``chat_json`` and ``transcribe`` only. When no API key
is configured, ``AI_ENABLED`` is False and callers use mock data.

The client is built to be resilient on free-tier APIs:
- transient errors (429 rate limit / 5xx / timeouts) are retried with backoff,
- Gemini 2.5 "thinking" is disabled so reasoning tokens never starve the JSON
  output (a common cause of truncated/empty responses), and
- empty or malformed responses raise a clean error so callers can fall back.
"""

from __future__ import annotations

import base64
import json
import logging
import mimetypes
import re
import time
from functools import lru_cache
from pathlib import Path
from typing import Any, Callable

from app import config

logger = logging.getLogger("mindmirror.ai")

# Generous ceiling so structured JSON answers are never cut off.
_MAX_OUTPUT_TOKENS = 8192
_MAX_ATTEMPTS = 3
_BACKOFF_SECONDS = (1.0, 3.0, 6.0)


class AIError(RuntimeError):
    """Raised when the AI provider cannot return a usable result."""


def _is_retryable(exc: Exception) -> bool:
    text = f"{type(exc).__name__} {exc}".lower()
    needles = (
        "429", "rate limit", "resource_exhausted", "quota",
        "500", "502", "503", "504", "unavailable", "overloaded",
        "deadline", "timeout", "timed out", "connection", "temporarily",
    )
    return any(n in text for n in needles)


def _call_with_retry(fn: Callable[[], Any], *, label: str) -> Any:
    last: Exception | None = None
    for attempt in range(_MAX_ATTEMPTS):
        try:
            return fn()
        except Exception as exc:  # noqa: BLE001 - we re-raise below
            last = exc
            if attempt < _MAX_ATTEMPTS - 1 and _is_retryable(exc):
                delay = _BACKOFF_SECONDS[min(attempt, len(_BACKOFF_SECONDS) - 1)]
                logger.warning("AI %s failed (attempt %s), retrying in %ss: %s",
                               label, attempt + 1, delay, exc)
                time.sleep(delay)
                continue
            break
    raise AIError(str(last) if last else "unknown AI error") from last


def _parse_json(text: str | None) -> dict:
    text = (text or "").strip()
    if not text:
        raise AIError("empty response from AI provider")
    # Strip markdown code fences if the model wrapped the JSON.
    if text.startswith("```"):
        text = re.sub(r"^```[a-zA-Z]*\n?", "", text).rstrip("`").strip()
    try:
        data = json.loads(text)
    except json.JSONDecodeError:
        match = re.search(r"\{.*\}", text, re.DOTALL)
        if not match:
            raise AIError("AI response was not valid JSON")
        try:
            data = json.loads(match.group())
        except json.JSONDecodeError as exc:
            raise AIError(f"AI response was not valid JSON: {exc}") from exc
    if not isinstance(data, dict):
        raise AIError("AI response was not a JSON object")
    return data


# --- OpenAI ---


@lru_cache(maxsize=1)
def _openai_client():  # pragma: no cover
    from openai import OpenAI

    return OpenAI(api_key=config.OPENAI_API_KEY, timeout=60.0)


def _openai_chat_json(system: str, user_content: Any, model: str | None) -> dict:
    def _run():
        response = _openai_client().chat.completions.create(
            model=model or config.OPENAI_MODEL,
            response_format={"type": "json_object"},
            max_tokens=_MAX_OUTPUT_TOKENS,
            messages=[
                {"role": "system", "content": system},
                {"role": "user", "content": user_content},
            ],
        )
        return response.choices[0].message.content

    text = _call_with_retry(_run, label="openai.chat")
    return _parse_json(text)


def _openai_transcribe(file_path: str) -> str:  # pragma: no cover
    def _run():
        with open(file_path, "rb") as fh:
            result = _openai_client().audio.transcriptions.create(
                model=config.OPENAI_TRANSCRIBE_MODEL,
                file=fh,
            )
        return result.text

    return _call_with_retry(_run, label="openai.transcribe")


# --- Gemini ---


@lru_cache(maxsize=1)
def _gemini_client():  # pragma: no cover
    from google import genai

    return genai.Client(api_key=config.GEMINI_API_KEY)


def _gemini_parts(user_content: Any) -> list:
    """Convert a plain string or OpenAI-style multimodal parts to Gemini parts."""

    from google.genai import types

    if isinstance(user_content, str):
        return [types.Part.from_text(text=user_content)]

    parts: list = []
    for item in user_content:
        if item.get("type") == "text":
            parts.append(types.Part.from_text(text=item["text"]))
        elif item.get("type") == "image_url":
            url = item["image_url"]["url"]
            if url.startswith("data:"):
                header, b64 = url.split(",", 1)
                mime = header.split(":")[1].split(";")[0]
                parts.append(types.Part.from_bytes(data=base64.b64decode(b64), mime_type=mime))
    return parts


def _gemini_generate_config(system: str | None, *, model: str, json_out: bool):
    """Build a GenerateContentConfig that disables thinking on 2.5 models.

    Reasoning models (gemini-2.5-*) can spend the whole output budget on hidden
    "thinking" tokens and then return an empty/truncated answer. Setting the
    thinking budget to 0 makes structured JSON output reliable.
    """

    from google.genai import types

    kwargs: dict[str, Any] = {"max_output_tokens": _MAX_OUTPUT_TOKENS}
    if system:
        kwargs["system_instruction"] = system
    if json_out:
        kwargs["response_mime_type"] = "application/json"
    if model.startswith("gemini-2.5"):
        try:
            kwargs["thinking_config"] = types.ThinkingConfig(thinking_budget=0)
        except Exception:  # pragma: no cover - older SDKs
            pass
    return types.GenerateContentConfig(**kwargs)


def _gemini_text(response) -> str:
    """Extract text from a Gemini response, tolerant of SDK quirks."""

    text = getattr(response, "text", None)
    if text:
        return text
    # Fall back to manual extraction across candidate parts.
    chunks: list[str] = []
    for cand in getattr(response, "candidates", None) or []:
        content = getattr(cand, "content", None)
        for part in getattr(content, "parts", None) or []:
            piece = getattr(part, "text", None)
            if piece:
                chunks.append(piece)
    return "".join(chunks)


def _gemini_chat_json(system: str, user_content: Any, model: str | None) -> dict:
    from google.genai import types

    use_model = model or config.GEMINI_MODEL

    def _run():
        client = _gemini_client()
        parts = _gemini_parts(user_content)
        response = client.models.generate_content(
            model=use_model,
            contents=[types.Content(role="user", parts=parts)],
            config=_gemini_generate_config(system, model=use_model, json_out=True),
        )
        return _gemini_text(response)

    text = _call_with_retry(_run, label="gemini.chat")
    return _parse_json(text)


def _gemini_transcribe(file_path: str) -> str:  # pragma: no cover
    from google.genai import types

    path = Path(file_path)
    mime = mimetypes.guess_type(path)[0] or "audio/mp3"
    audio_bytes = path.read_bytes()
    use_model = config.GEMINI_MODEL

    def _run():
        client = _gemini_client()
        response = client.models.generate_content(
            model=use_model,
            contents=[
                types.Part.from_bytes(data=audio_bytes, mime_type=mime),
                types.Part.from_text(text="Transcribe all spoken words. Return only the transcript."),
            ],
            config=_gemini_generate_config(None, model=use_model, json_out=False),
        )
        return _gemini_text(response)

    return _call_with_retry(_run, label="gemini.transcribe").strip()


# --- Public API ---


def chat_json(
    system: str,
    user_content: Any,
    *,
    model: str | None = None,
) -> dict:
    if config.AI_PROVIDER == "gemini":
        return _gemini_chat_json(system, user_content, model)
    return _openai_chat_json(system, user_content, model)


def transcribe(file_path: str) -> str:
    if config.AI_PROVIDER == "gemini":
        return _gemini_transcribe(file_path)
    return _openai_transcribe(file_path)


def vision_model() -> str:
    if config.AI_PROVIDER == "gemini":
        return config.GEMINI_VISION_MODEL
    return config.OPENAI_VISION_MODEL
