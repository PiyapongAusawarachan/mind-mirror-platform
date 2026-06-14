"""Summarize uploaded learning material into a short overview + key points.

Returns a plain dict so callers can persist it:
{
  "summary": str,          # 2-4 sentence overview of the material
  "key_points": [str],     # the main concepts a learner should master
}

When no API key is configured (``AI_ENABLED`` is False) a deterministic
heuristic summary is produced so the feature is always usable.
"""

from __future__ import annotations

import re

from app import config
from app.ai import client

_SYSTEM = (
    "You are MindMirror's study assistant. Read the learning material and produce a "
    "concise, faithful overview a student can use to grasp the scope of the lesson. "
    "Write in the same language as the material. Keep the summary to 2-4 sentences and "
    "list the 4-7 most important concepts to master. "
    'Respond as JSON: {"summary": str, "key_points": [str, ...]}'
)


def summarize_material(source_text: str) -> dict:
    source_text = (source_text or "").strip()
    if not source_text:
        return {"summary": "", "key_points": []}

    if not config.AI_ENABLED:
        return _mock_summary(source_text)

    user = f"LEARNING MATERIAL:\n{source_text[:8000]}"
    try:
        data = client.chat_json(_SYSTEM, user)
    except Exception:  # pragma: no cover - falls back to heuristic
        return _mock_summary(source_text)
    return _normalize(data, source_text)


def _normalize(data: dict, source_text: str) -> dict:
    summary = str(data.get("summary", "")).strip()
    points: list[str] = []
    for p in data.get("key_points", []):
        text = str(p).strip()
        if text and text not in points:
            points.append(text)
    if not summary and not points:
        return _mock_summary(source_text)
    return {"summary": summary, "key_points": points[:8]}


def _sentences(text: str) -> list[str]:
    parts = re.split(r"(?<=[.!?\u0e2f])\s+|\n+", text)
    return [s.strip() for s in parts if len(s.strip()) > 20]


def _mock_summary(source_text: str) -> dict:
    sentences = _sentences(source_text)
    summary = " ".join(sentences[:3]) if sentences else source_text[:280]
    points = [s[:120] for s in sentences[1:6]] or [source_text[:120]]
    return {"summary": summary.strip(), "key_points": points}
