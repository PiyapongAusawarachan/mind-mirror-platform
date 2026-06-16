"""Teacher dashboard: per-student understanding and per-topic distributions."""

from __future__ import annotations

from fastapi import APIRouter, Depends, Form, HTTPException, Request
from fastapi.responses import RedirectResponse
from sqlalchemy import select
from sqlalchemy.orm import Session

from app import analytics, plans
from app.auth import require_teacher
from app.database import get_db
from app.models import Course, Enrollment, LearningContext, User
from app.templating import render

router = APIRouter(prefix="/teacher", tags=["teacher"])


def _course_contexts(course: Course, students: list[User]) -> list[LearningContext]:
    """Lessons that belong to this course (course-linked, or legacy unlinked)."""

    contexts = []
    for s in students:
        for ctx in s.contexts:
            if ctx.course_id == course.id or ctx.course_id is None:
                contexts.append(ctx)
    return contexts


def _student_rows(course: Course, students: list[User]) -> list[dict]:
    rows = []
    for s in students:
        for ctx in s.contexts:
            if ctx.course_id not in (course.id, None):
                continue
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
        students = course.enrolled_students
        contexts = _course_contexts(course, students)
        all_contexts.extend(contexts)
        course_blocks.append(
            {
                "course": course,
                "students": students,
                "rows": _student_rows(course, students),
                "topic_distribution": analytics.course_topic_distribution(contexts),
            }
        )

    can_create = plans.can_add(teacher.plan, "max_courses_teacher", len(courses))
    return render(
        request,
        "teacher/dashboard.html",
        {
            "user": teacher,
            "course_blocks": course_blocks,
            "overall_topics": analytics.course_topic_distribution(all_contexts),
            "course_timeline": analytics.course_timeline(all_contexts),
            "can_create": can_create,
            "course_limit": plans.limit(teacher.plan, "max_courses_teacher"),
            "notice": request.query_params.get("notice"),
        },
    )


@router.post("/courses")
def create_course(
    name: str = Form(...),
    teacher: User = Depends(require_teacher),
    db: Session = Depends(get_db),
):
    count = len(db.scalars(select(Course).where(Course.teacher_id == teacher.id)).all())
    if not plans.can_add(teacher.plan, "max_courses_teacher", count):
        return RedirectResponse("/teacher?notice=limit", status_code=303)

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
    teacher_course_ids = {c.id for c in db.scalars(select(Course).where(Course.teacher_id == teacher.id)).all()}
    enrolled_in_teacher_course = any(e.course_id in teacher_course_ids for e in student.enrollments)
    lesson_in_teacher_course = ctx.course_id in teacher_course_ids
    if not (lesson_in_teacher_course or (ctx.course_id is None and enrolled_in_teacher_course)):
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
