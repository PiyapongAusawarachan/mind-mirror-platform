"""Unified AI client — routes to Gemini or OpenAI based on ``AI_PROVIDER``.

Higher-level modules call ``chat_json`` and ``transcribe`` only. When no API key
is configured, ``AI_ENABLED`` is False and callers use mock data.
"""

from __future__ import annotations

import base64
import json
import mimetypes
import re
from functools import lru_cache
from pathlib import Path
from typing import Any

from app import config


def _parse_json(text: str) -> dict:
    text = (text or "").strip()
    if not text:
        return {}
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        match = re.search(r"\{.*\}", text, re.DOTALL)
        if match:
            return json.loads(match.group())
        raise


# --- OpenAI ---


@lru_cache(maxsize=1)
def _openai_client():  # pragma: no cover
    from openai import OpenAI

    return OpenAI(api_key=config.OPENAI_API_KEY)


def _openai_chat_json(system: str, user_content: Any, model: str | None) -> dict:
    response = _openai_client().chat.completions.create(
        model=model or config.OPENAI_MODEL,
        response_format={"type": "json_object"},
        messages=[
            {"role": "system", "content": system},
            {"role": "user", "content": user_content},
        ],
    )
    return _parse_json(response.choices[0].message.content or "{}")


def _openai_transcribe(file_path: str) -> str:  # pragma: no cover
    with open(file_path, "rb") as fh:
        result = _openai_client().audio.transcriptions.create(
            model=config.OPENAI_TRANSCRIBE_MODEL,
            file=fh,
        )
    return result.text


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


def _gemini_chat_json(system: str, user_content: Any, model: str | None) -> dict:
    from google.genai import types

    client = _gemini_client()
    parts = _gemini_parts(user_content)
    response = client.models.generate_content(
        model=model or config.GEMINI_MODEL,
        contents=[types.Content(role="user", parts=parts)],
        config=types.GenerateContentConfig(
            system_instruction=system,
            response_mime_type="application/json",
        ),
    )
    return _parse_json(response.text or "{}")


def _gemini_transcribe(file_path: str) -> str:  # pragma: no cover
    from google.genai import types

    path = Path(file_path)
    mime = mimetypes.guess_type(path)[0] or "audio/mp3"
    audio_bytes = path.read_bytes()
    client = _gemini_client()
    response = client.models.generate_content(
        model=config.GEMINI_MODEL,
        contents=[
            types.Part.from_bytes(data=audio_bytes, mime_type=mime),
            types.Part.from_text(text="Transcribe all spoken words. Return only the transcript."),
        ],
    )
    return (response.text or "").strip()


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
