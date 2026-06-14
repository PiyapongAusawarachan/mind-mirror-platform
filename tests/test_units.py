"""Unit tests for AI mock layer, analytics, and i18n (no network)."""

from app import config, i18n
from app.ai import analyze, assess


def test_mock_analysis_classifies_topics():
    source = "A function is a reusable block of code. Scope and recursion matter."
    explanation = "A function is a reusable block of code."
    result = analyze.analyze_understanding(source, explanation)
    assert result["topics"]
    for t in result["topics"]:
        assert t["level"] in config.LEVELS


def test_generate_questions_makes_open_and_mcq():
    weak = [{"name": "Recursion", "level": config.NOT_UNDERSTOOD}]
    questions = assess.generate_questions("source", weak)
    qtypes = {q["qtype"] for q in questions}
    assert config.QUESTION_OPEN in qtypes
    assert config.QUESTION_MCQ in qtypes
    mcq = next(q for q in questions if q["qtype"] == config.QUESTION_MCQ)
    assert len(mcq["options"]) >= 2
    assert 0 <= mcq["correct_index"] < len(mcq["options"])


def test_grade_mcq():
    assert assess.grade_mcq(0, 0)["level"] == config.UNDERSTOOD
    assert assess.grade_mcq(0, 1)["level"] == config.NOT_UNDERSTOOD
    assert assess.grade_mcq(0, None)["score"] == 0.0


def test_grade_open_mock():
    short = assess.grade_answer("Q", "no")
    long = assess.grade_answer("Q", " ".join(["word"] * 40))
    assert short["score"] < long["score"]


def test_mastery_from_distribution():
    from app import analytics

    assert analytics.mastery_from_distribution({"understood": 0, "confused": 0, "not_understood": 0}) == 0.0
    full = analytics.mastery_from_distribution({"understood": 2, "confused": 0, "not_understood": 0})
    assert full == 100.0
    mixed = analytics.mastery_from_distribution({"understood": 1, "confused": 1, "not_understood": 0})
    assert mixed == 75.0


def test_i18n_translation_and_fallback():
    assert i18n.translate("th", "nav.login") == "เข้าสู่ระบบ"
    assert i18n.translate("en", "nav.login") == "Log in"
    # Unknown key returns the key itself.
    assert i18n.translate("en", "does.not.exist") == "does.not.exist"
    # Unknown language normalizes to default.
    assert i18n.normalize_lang("xx") in i18n.LANGUAGES
