"""Detect blind spots/misconceptions and build a knowledge map.

Returns a plain dict so callers can persist it:
{
  "summary": str,
  "topics": [{"name", "level", "detail"}],
  "edges":  [{"source", "target", "relation"}],
}
"""

from __future__ import annotations

import logging
import re

from app import config
from app.ai import client

logger = logging.getLogger("mindmirror.ai")

_SYSTEM = (
    "You are MindMirror, an expert tutor that compares a student's own-words "
    "explanation against authoritative source material to find gaps in understanding. "
    "Identify the key subtopics of the lesson. For each, judge whether the student "
    "'understood', is 'confused' (partial/imprecise), or 'not_understood' (missing/wrong). "
    "Also infer relationships between subtopics so they form a connected knowledge map. "
    'Respond as JSON: {"summary": str, '
    '"topics": [{"name": str, "level": "understood|confused|not_understood", "detail": str}], '
    '"edges": [{"source": str, "target": str, "relation": str}]}'
)


def analyze_understanding(source_text: str, explanation: str) -> dict:
    if not config.AI_ENABLED:
        return _mock_analysis(source_text, explanation)

    user = (
        f"SOURCE MATERIAL:\n{source_text[:6000]}\n\n"
        f"STUDENT EXPLANATION:\n{explanation[:4000]}"
    )
    try:
        data = client.chat_json(_SYSTEM, user)
    except Exception as exc:  # pragma: no cover - resilient fallback
        logger.warning("analyze_understanding fell back to heuristic: %s", exc)
        data = _mock_analysis(source_text, explanation)
    return _normalize(data)


def _normalize(data: dict) -> dict:
    topics = []
    for t in data.get("topics", []):
        level = str(t.get("level", config.CONFUSED)).lower()
        if level not in config.LEVELS:
            level = config.CONFUSED
        name = str(t.get("name", "")).strip()
        if name:
            topics.append({"name": name, "level": level, "detail": str(t.get("detail", ""))})
    names = {t["name"] for t in topics}
    edges = []
    for e in data.get("edges", []):
        src, tgt = str(e.get("source", "")).strip(), str(e.get("target", "")).strip()
        if src in names and tgt in names and src != tgt:
            edges.append({"source": src, "target": tgt, "relation": str(e.get("relation", "related to"))})
    return {"summary": str(data.get("summary", "")), "topics": topics, "edges": edges}


def _keywords(text: str, limit: int = 8) -> list[str]:
    stop = {
        "the", "and", "for", "that", "this", "with", "from", "are", "was", "have",
        "has", "but", "not", "you", "your", "they", "their", "what", "when", "which",
        "into", "can", "will", "would", "about", "there", "these", "those", "then",
    }
    counts: dict[str, int] = {}
    for word in re.findall(r"[A-Za-z][A-Za-z\-]{3,}", text.lower()):
        if word not in stop:
            counts[word] = counts.get(word, 0) + 1
    ranked = sorted(counts, key=lambda w: counts[w], reverse=True)
    return ranked[:limit]


def _mock_analysis(source_text: str, explanation: str) -> dict:
    """Deterministic heuristic so the app is fully usable without an API key.

    A source keyword the student mentioned -> understood; partially -> confused;
    absent -> not_understood.
    """

    keywords = _keywords(source_text) or ["main concept", "definition", "example"]
    expl = explanation.lower()
    topics = []
    for kw in keywords:
        if kw in expl:
            level = config.UNDERSTOOD
            detail = "Mentioned and used in the explanation."
        elif any(kw.startswith(w[:4]) for w in expl.split()):
            level = config.CONFUSED
            detail = "Touched on but not clearly explained."
        else:
            level = config.NOT_UNDERSTOOD
            detail = "Not addressed in the explanation."
        topics.append({"name": kw.title(), "level": level, "detail": detail})

    edges = [
        {"source": topics[i]["name"], "target": topics[i + 1]["name"], "relation": "related to"}
        for i in range(len(topics) - 1)
    ]
    summary = (
        "Heuristic analysis (no AI key set). Green topics appear understood, "
        "amber are partial, red are missing from your explanation."
    )
    return {"summary": summary, "topics": topics, "edges": edges}
