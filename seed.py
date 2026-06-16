"""Populate demo data: one teacher, one course, two students with sample work.

Run with:  python seed.py
Logins (password for all): demo1234
  teacher@example.com  ·  alice@example.com  ·  bob@example.com
"""

from __future__ import annotations

import json
from datetime import datetime, timedelta, timezone

from app import analytics, config
from app.ai import analyze, assess
from app.auth import hash_password
from app.database import SessionLocal, init_db
from app.models import (
    Analysis,
    Answer,
    Assessment,
    Course,
    Enrollment,
    Explanation,
    LearningContext,
    MasterySnapshot,
    Question,
    Topic,
    TopicEdge,
    User,
)

SOURCE = (
    "A function is a reusable block of code that performs a task. Functions take "
    "parameters as input and may return a value. Scope determines where variables are "
    "visible: local variables live inside a function, global variables outside. "
    "Recursion is when a function calls itself. Arguments are the values passed to "
    "parameters when calling the function."
)


def _add_analysis(db, ctx: LearningContext, explanation: str) -> Analysis:
    result = analyze.analyze_understanding(ctx.source_text, explanation)
    analysis = Analysis(context_id=ctx.id, summary=result["summary"])
    db.add(analysis)
    db.flush()
    dist = analytics.empty_distribution()
    for t in result["topics"]:
        db.add(Topic(analysis_id=analysis.id, name=t["name"], level=t["level"], detail=t["detail"]))
        if t["level"] in dist:
            dist[t["level"]] += 1
    for e in result["edges"]:
        db.add(TopicEdge(analysis_id=analysis.id, source=e["source"], target=e["target"], relation=e["relation"]))
    db.flush()
    return analysis, dist


def _backdated_snapshots(db, ctx: LearningContext, base_dist: dict, weeks: int = 4) -> None:
    """Create a few weekly snapshots so the timeline shows multi-week progress."""

    now = datetime.now(timezone.utc)
    understood = base_dist.get(config.UNDERSTOOD, 0)
    confused = base_dist.get(config.CONFUSED, 0)
    not_u = base_dist.get(config.NOT_UNDERSTOOD, 0)
    total = max(1, understood + confused + not_u)
    for i in range(weeks):
        # Simulate steady improvement: not-understood migrates to understood over weeks.
        shift = round((not_u + confused) * i / max(1, weeks))
        u = min(total, understood + shift)
        n = max(0, not_u - shift)
        c = max(0, total - u - n)
        dist = {config.UNDERSTOOD: u, config.CONFUSED: c, config.NOT_UNDERSTOOD: n}
        snap = MasterySnapshot(
            context_id=ctx.id,
            source="analysis",
            understood=u, confused=c, not_understood=n,
            mastery_pct=analytics.mastery_from_distribution(dist),
            created_at=now - timedelta(weeks=(weeks - i)),
        )
        db.add(snap)
    db.flush()


def main() -> None:
    config.ensure_dirs()
    init_db()
    db = SessionLocal()
    try:
        if db.query(User).filter(User.email == "teacher@example.com").first():
            print("Demo data already present. Skipping.")
            return

        pw = hash_password("demo1234")
        teacher = User(name="Dr. Smith", email="teacher@example.com", password_hash=pw, role="teacher")
        db.add(teacher)
        db.flush()

        course = Course(name="Computer Programming II", teacher_id=teacher.id)
        db.add(course)
        db.flush()

        for name, email, expl in [
            ("Alice", "alice@example.com",
             "A function is a reusable block of code that takes parameters and returns a value. "
             "Scope means local variables are inside a function. Recursion is a function calling itself."),
            ("Bob", "bob@example.com",
             "A function does something. You give it stuff and it works."),
        ]:
            student = User(name=name, email=email, password_hash=pw, role="student", course_id=course.id)
            db.add(student)
            db.flush()
            db.add(Enrollment(student_id=student.id, course_id=course.id))
            db.flush()

            ctx = LearningContext(student_id=student.id, title="Functions", source_text=SOURCE, course_id=course.id)
            db.add(ctx)
            db.flush()
            db.add(Explanation(context_id=ctx.id, modality="typing", text=expl))
            db.flush()

            analysis, dist = _add_analysis(db, ctx, expl)
            _backdated_snapshots(db, ctx, dist, weeks=4)

            weak = [{"name": t.name, "level": t.level}
                    for t in analysis.topics if t.level in (config.CONFUSED, config.NOT_UNDERSTOOD)]
            questions = assess.generate_questions(ctx.source_text, weak)
            if questions:
                assessment = Assessment(context_id=ctx.id)
                db.add(assessment)
                db.flush()
                scores = []
                post_dist = analytics.empty_distribution()
                for q in questions:
                    question = Question(
                        assessment_id=assessment.id, topic_name=q["topic"], text=q["question"],
                        target_level=q["target_level"], qtype=q["qtype"],
                        options_json=json.dumps(q["options"]) if q["qtype"] == config.QUESTION_MCQ else "",
                        correct_index=q.get("correct_index") if q["qtype"] == config.QUESTION_MCQ else None,
                    )
                    db.add(question)
                    db.flush()
                    if q["qtype"] == config.QUESTION_MCQ:
                        chosen = 0 if name == "Alice" else 1
                        graded = assess.grade_mcq(q["correct_index"], chosen)
                        db.add(Answer(question_id=question.id, modality="choice", text="", selected_index=chosen,
                                      score=graded["score"], feedback=graded["feedback"], resulting_level=graded["level"]))
                    else:
                        ans = "It is explained in detail in my own words with examples and reasoning." \
                            if name == "Alice" else "idk"
                        graded = assess.grade_answer(q["question"], ans, ctx.source_text)
                        db.add(Answer(question_id=question.id, modality="typing", text=ans,
                                      score=graded["score"], feedback=graded["feedback"], resulting_level=graded["level"]))
                    scores.append(graded["score"])
                    if graded["level"] in post_dist:
                        post_dist[graded["level"]] += 1
                assessment.score = round(sum(scores) / len(scores), 1)
                assessment.completed_at = datetime.now(timezone.utc)
                analytics.record_snapshot(db, ctx, "assessment", post_dist)

        db.commit()
        print("Seeded demo data. Log in as teacher@example.com / demo1234 (password for all).")
    finally:
        db.close()


if __name__ == "__main__":
    main()
