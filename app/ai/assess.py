"""Generate personalized questions (open-ended + multiple choice) and grade them."""

from __future__ import annotations

import logging

from app import config
from app.ai import client

logger = logging.getLogger("mindmirror.ai")

_GEN_SYSTEM = (
    "You are MindMirror's assessment author. Given a lesson's source material and a list "
    "of subtopics the student is confused about or does not understand, create questions "
    "that probe conceptual understanding of exactly those weak subtopics. For each subtopic "
    "produce BOTH: (a) one short open-ended question (no multiple choice), and (b) one "
    "multiple-choice question with exactly 4 options and the index (0-3) of the correct one. "
    'Respond as JSON: {"items": [{"topic": str, "open": str, '
    '"mcq": {"question": str, "options": [str, str, str, str], "correct_index": int}}]}'
)

_GRADE_SYSTEM = (
    "You are MindMirror's grader. Grade the student's free-text answer to a conceptual "
    "question on a 0-100 scale for conceptual understanding, give one or two sentences of "
    "constructive feedback, and classify the result as 'understood' (>=75), 'confused' "
    "(40-74), or 'not_understood' (<40). "
    'Respond as JSON: {"score": number, "feedback": str, '
    '"level": "understood|confused|not_understood"}'
)


def _mock_items(weak_topics: list[dict]) -> list[dict]:
    items = []
    for t in weak_topics:
        name = t["name"]
        items.append(
            {
                "topic": name,
                "target_level": t["level"],
                "open": f"In your own words, explain {name} and why it matters in this lesson.",
                "mcq": {
                    "question": f"Which statement best describes {name}?",
                    "options": [
                        f"A correct, precise description of {name}.",
                        f"A vague or partially wrong idea about {name}.",
                        f"Something unrelated to {name}.",
                        f"The opposite of what {name} actually means.",
                    ],
                    "correct_index": 0,
                },
            }
        )
    return items


def generate_questions(source_text: str, weak_topics: list[dict]) -> list[dict]:
    """Return a flat list of question dicts.

    Each item is either:
      {"qtype": "open", "topic", "question", "target_level"}
      {"qtype": "mcq",  "topic", "question", "options": [...], "correct_index": int, "target_level"}
    """

    if not weak_topics:
        return []

    level_by_name = {t["name"]: t["level"] for t in weak_topics}

    if not config.AI_ENABLED:
        items = _mock_items(weak_topics)
    else:
        listing = "\n".join(f"- {t['name']} ({t['level']})" for t in weak_topics)
        user = f"SOURCE MATERIAL:\n{source_text[:5000]}\n\nWEAK SUBTOPICS:\n{listing}"
        try:
            data = client.chat_json(_GEN_SYSTEM, user)
            items = data.get("items", []) or _mock_items(weak_topics)
        except Exception as exc:  # pragma: no cover - resilient fallback
            logger.warning("generate_questions fell back to mock: %s", exc)
            items = _mock_items(weak_topics)

    questions: list[dict] = []
    for item in items:
        topic = str(item.get("topic", "")).strip() or "General"
        target = level_by_name.get(topic, config.CONFUSED)

        open_q = str(item.get("open", "")).strip()
        if open_q:
            questions.append(
                {"qtype": config.QUESTION_OPEN, "topic": topic, "question": open_q, "target_level": target}
            )

        mcq = item.get("mcq") or {}
        options = [str(o) for o in mcq.get("options", []) if str(o).strip()]
        mcq_q = str(mcq.get("question", "")).strip()
        if mcq_q and len(options) >= 2:
            try:
                correct = int(mcq.get("correct_index", 0))
            except (ValueError, TypeError):
                correct = 0
            correct = max(0, min(correct, len(options) - 1))
            questions.append(
                {
                    "qtype": config.QUESTION_MCQ,
                    "topic": topic,
                    "question": mcq_q,
                    "options": options,
                    "correct_index": correct,
                    "target_level": target,
                }
            )
    return questions


def grade_mcq(correct_index: int | None, selected_index: int | None) -> dict:
    """Auto-grade a multiple-choice answer."""

    if selected_index is None:
        return {"score": 0.0, "feedback": "No option selected.", "level": config.NOT_UNDERSTOOD}
    if correct_index is not None and selected_index == correct_index:
        return {"score": 100.0, "feedback": "Correct.", "level": config.UNDERSTOOD}
    return {"score": 0.0, "feedback": "Incorrect choice.", "level": config.NOT_UNDERSTOOD}


def grade_answer(question: str, answer: str, source_text: str = "") -> dict:
    """Grade a free-text answer. Returns {"score": float, "feedback": str, "level": str}."""

    if not answer.strip():
        return {"score": 0.0, "feedback": "No answer provided.", "level": config.NOT_UNDERSTOOD}

    if not config.AI_ENABLED:
        words = len(answer.split())
        if words >= 30:
            return {"score": 80.0, "feedback": "[Mock] Detailed answer — looks solid.", "level": config.UNDERSTOOD}
        if words >= 10:
            return {"score": 55.0, "feedback": "[Mock] Partial answer — add more detail.", "level": config.CONFUSED}
        return {"score": 25.0, "feedback": "[Mock] Too brief to show understanding.", "level": config.NOT_UNDERSTOOD}

    user = (
        f"SOURCE MATERIAL:\n{source_text[:4000]}\n\n"
        f"QUESTION:\n{question}\n\nSTUDENT ANSWER:\n{answer[:3000]}"
    )
    try:
        data = client.chat_json(_GRADE_SYSTEM, user)
    except Exception as exc:  # pragma: no cover - resilient fallback
        logger.warning("grade_answer fell back to heuristic: %s", exc)
        words = len(answer.split())
        score = 80.0 if words >= 30 else 55.0 if words >= 10 else 30.0
        level = config.UNDERSTOOD if score >= 75 else config.CONFUSED if score >= 40 else config.NOT_UNDERSTOOD
        return {"score": score, "feedback": "ระบบให้คะแนนเบื้องต้นจากความครบถ้วนของคำตอบ", "level": level}

    score = float(data.get("score", 0) or 0)
    score = max(0.0, min(100.0, score))
    level = str(data.get("level", "")).lower()
    if level not in config.LEVELS:
        level = config.UNDERSTOOD if score >= 75 else config.CONFUSED if score >= 40 else config.NOT_UNDERSTOOD
    return {"score": score, "feedback": str(data.get("feedback", "")), "level": level}
