"""Teacher dashboard: per-student understanding and per-topic distributions."""

from __future__ import annotations

from fastapi import APIRouter, Depends, Form, HTTPException, Request
from fastapi.responses import RedirectResponse
from sqlalchemy import select
from sqlalchemy.orm import Session

from app import analytics
from app.auth import require_teacher
from app.database import get_db
from app.models import Course, LearningContext, User
from app.templating import render

router = APIRouter(prefix="/teacher", tags=["teacher"])


def _student_rows(students: list[User]) -> list[dict]:
    rows = []
    for s in students:
        for ctx in s.contexts:
            assessment = analytics.latest_completed_assessment(ctx)
            rows.append(
                {
                    "student": s,
                    "context": ctx,
                    "distribution": analytics.context_distribution(ctx),
                    "score": assessment.score if assessment else None,
                    "improvement": analytics.improvement(ctx),
                    "analyzed": analytics.latest_analysis(ctx) is not None,
                }
            )
    return rows


@router.get("")
def dashboard(request: Request, teacher: User = Depends(require_teacher), db: Session = Depends(get_db)):
    courses = db.scalars(select(Course).where(Course.teacher_id == teacher.id)).all()

    all_contexts: list[LearningContext] = []
    course_blocks = []
    for course in courses:
        students = list(course.students)
        contexts = [ctx for s in students for ctx in s.contexts]
        all_contexts.extend(contexts)
        course_blocks.append(
            {
                "course": course,
                "students": students,
                "rows": _student_rows(students),
                "topic_distribution": analytics.course_topic_distribution(contexts),
            }
        )

    return render(
        request,
        "teacher/dashboard.html",
        {
            "user": teacher,
            "course_blocks": course_blocks,
            "overall_topics": analytics.course_topic_distribution(all_contexts),
            "course_timeline": analytics.course_timeline(all_contexts),
        },
    )


@router.post("/courses")
def create_course(
    name: str = Form(...),
    teacher: User = Depends(require_teacher),
    db: Session = Depends(get_db),
):
    course = Course(name=name.strip() or "Untitled course", teacher_id=teacher.id)
    db.add(course)
    db.commit()
    return RedirectResponse("/teacher", status_code=303)


@router.get("/lessons/{context_id}")
def student_lesson(
    context_id: int,
    request: Request,
    teacher: User = Depends(require_teacher),
    db: Session = Depends(get_db),
):
    ctx = db.get(LearningContext, context_id)
    if ctx is None:
        raise HTTPException(status_code=404, detail="Lesson not found")
    student = ctx.student
    if student.course is None or student.course.teacher_id != teacher.id:
        raise HTTPException(status_code=403, detail="Not your student")

    return render(
        request,
        "teacher/lesson.html",
        {
            "user": teacher,
            "ctx": ctx,
            "student": student,
            "analysis": analytics.latest_analysis(ctx),
            "pre": analytics.pre_levels(ctx),
            "post": analytics.post_levels(ctx),
            "assessment": analytics.latest_completed_assessment(ctx),
            "improvement": analytics.improvement(ctx),
            "timeline": analytics.timeline(ctx),
        },
    )
