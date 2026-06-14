"""Student flow: learning context, explanations, knowledge map, assessment."""

from __future__ import annotations

import json
import uuid
from datetime import datetime, timezone
from pathlib import Path

from fastapi import APIRouter, Depends, File, Form, HTTPException, Request, UploadFile
from fastapi.responses import RedirectResponse
from sqlalchemy.orm import Session

from app import analytics, config
from app.ai import analyze, assess, ingest, summarize
from app.auth import require_student
from app.database import get_db
from app.models import (
    Analysis,
    Answer,
    Assessment,
    Explanation,
    LearningContext,
    Material,
    Question,
    Topic,
    TopicEdge,
    User,
)
from app.templating import render

router = APIRouter(prefix="/student", tags=["student"])

IMAGE_EXT = {".png", ".jpg", ".jpeg", ".gif", ".webp", ".bmp"}
AUDIO_EXT = {".mp3", ".wav", ".m4a", ".ogg", ".webm", ".mp4"}


def _save_upload(file: UploadFile) -> Path:
    suffix = Path(file.filename or "upload").suffix.lower()
    dest = config.UPLOAD_DIR / f"{uuid.uuid4().hex}{suffix}"
    dest.write_bytes(file.file.read())
    return dest


def _get_owned_context(db: Session, context_id: int, student: User) -> LearningContext:
    ctx = db.get(LearningContext, context_id)
    if ctx is None or ctx.student_id != student.id:
        raise HTTPException(status_code=404, detail="Lesson not found")
    return ctx


@router.get("")
def dashboard(request: Request, student: User = Depends(require_student), db: Session = Depends(get_db)):
    contexts = (
        db.query(LearningContext)
        .filter(LearningContext.student_id == student.id)
        .order_by(LearningContext.created_at.desc())
        .all()
    )
    return render(request, "student/dashboard.html", {"user": student, "contexts": contexts})


@router.post("/lessons")
def create_lesson(
    title: str = Form(...),
    student: User = Depends(require_student),
    db: Session = Depends(get_db),
):
    ctx = LearningContext(student_id=student.id, title=title.strip() or "Untitled lesson")
    db.add(ctx)
    db.commit()
    db.refresh(ctx)
    return RedirectResponse(f"/student/lessons/{ctx.id}", status_code=303)


@router.get("/lessons/{context_id}")
def lesson_detail(
    context_id: int,
    request: Request,
    student: User = Depends(require_student),
    db: Session = Depends(get_db),
):
    ctx = _get_owned_context(db, context_id, student)
    analysis = analytics.latest_analysis(ctx)
    return render(
        request,
        "student/lesson.html",
        {
            "user": student,
            "ctx": ctx,
            "analysis": analysis,
            "distribution": analytics.context_distribution(ctx),
            "timeline": analytics.timeline(ctx),
        },
    )


@router.post("/lessons/{context_id}/materials")
def upload_materials(
    context_id: int,
    files: list[UploadFile] = File(...),
    student: User = Depends(require_student),
    db: Session = Depends(get_db),
):
    ctx = _get_owned_context(db, context_id, student)
    added_text: list[str] = []
    for file in files:
        if not file.filename:
            continue
        path = _save_upload(file)
        ext = path.suffix.lower()
        if ext == ".pdf":
            kind, text = "pdf", ingest.extract_pdf_text(str(path))
        elif ext in IMAGE_EXT:
            kind, text = "image", ingest.extract_image_text(str(path))
        else:
            kind, text = "other", ""
        db.add(
            Material(
                context_id=ctx.id, filename=file.filename, filepath=str(path),
                kind=kind, extracted_text=text,
            )
        )
        if text:
            added_text.append(f"# {file.filename}\n{text}")
    if added_text:
        ctx.source_text = (ctx.source_text + "\n\n" + "\n\n".join(added_text)).strip()
        _refresh_summary(ctx)
    db.commit()
    return RedirectResponse(f"/student/lessons/{ctx.id}", status_code=303)


def _refresh_summary(ctx: LearningContext) -> None:
    """Generate (or regenerate) the AI summary of a lesson's material."""

    result = summarize.summarize_material(ctx.source_text)
    ctx.summary = result["summary"]
    ctx.summary_points_json = json.dumps(result["key_points"], ensure_ascii=False)


@router.post("/lessons/{context_id}/summarize")
def summarize_lesson(
    context_id: int,
    student: User = Depends(require_student),
    db: Session = Depends(get_db),
):
    ctx = _get_owned_context(db, context_id, student)
    if ctx.source_text.strip():
        _refresh_summary(ctx)
        db.commit()
    return RedirectResponse(f"/student/lessons/{ctx.id}#summary", status_code=303)


@router.post("/lessons/{context_id}/explain")
def add_explanation(
    context_id: int,
    modality: str = Form(...),
    text: str = Form(""),
    file: UploadFile | None = File(None),
    student: User = Depends(require_student),
    db: Session = Depends(get_db),
):
    ctx = _get_owned_context(db, context_id, student)
    content = text.strip()
    if modality == "writing" and file and file.filename:
        content = ingest.extract_image_text(str(_save_upload(file)))
    elif modality == "speaking" and file and file.filename:
        content = ingest.transcribe_audio(str(_save_upload(file)))

    if content:
        db.add(Explanation(context_id=ctx.id, modality=modality, text=content))
        db.commit()
    return RedirectResponse(f"/student/lessons/{ctx.id}", status_code=303)


@router.post("/lessons/{context_id}/analyze")
def run_analysis(
    context_id: int,
    student: User = Depends(require_student),
    db: Session = Depends(get_db),
):
    ctx = _get_owned_context(db, context_id, student)
    if not ctx.explanations:
        return RedirectResponse(f"/student/lessons/{ctx.id}", status_code=303)

    explanation_text = "\n\n".join(e.text for e in ctx.explanations)
    source = ctx.source_text or "(No source material uploaded.)"
    result = analyze.analyze_understanding(source, explanation_text)

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
    analytics.record_snapshot(db, ctx, "analysis", dist)
    db.commit()
    return RedirectResponse(f"/student/lessons/{ctx.id}#map", status_code=303)


@router.post("/lessons/{context_id}/quiz")
def create_quiz(
    context_id: int,
    student: User = Depends(require_student),
    db: Session = Depends(get_db),
):
    ctx = _get_owned_context(db, context_id, student)
    analysis = analytics.latest_analysis(ctx)
    if analysis is None:
        return RedirectResponse(f"/student/lessons/{ctx.id}", status_code=303)

    weak = [
        {"name": t.name, "level": t.level}
        for t in analysis.topics
        if t.level in (config.CONFUSED, config.NOT_UNDERSTOOD)
    ]
    questions = assess.generate_questions(ctx.source_text, weak)
    if not questions:
        return RedirectResponse(f"/student/lessons/{ctx.id}", status_code=303)

    assessment = Assessment(context_id=ctx.id)
    db.add(assessment)
    db.flush()
    for q in questions:
        db.add(
            Question(
                assessment_id=assessment.id,
                topic_name=q["topic"],
                text=q["question"],
                target_level=q["target_level"],
                qtype=q["qtype"],
                options_json=json.dumps(q["options"]) if q["qtype"] == config.QUESTION_MCQ else "",
                correct_index=q.get("correct_index") if q["qtype"] == config.QUESTION_MCQ else None,
            )
        )
    db.commit()
    db.refresh(assessment)
    return RedirectResponse(f"/student/quiz/{assessment.id}", status_code=303)


@router.get("/quiz/{assessment_id}")
def take_quiz(
    assessment_id: int,
    request: Request,
    student: User = Depends(require_student),
    db: Session = Depends(get_db),
):
    assessment = db.get(Assessment, assessment_id)
    if assessment is None or assessment.context.student_id != student.id:
        raise HTTPException(status_code=404, detail="Quiz not found")
    return render(request, "student/quiz.html", {"user": student, "assessment": assessment})


@router.post("/quiz/{assessment_id}/submit")
async def submit_quiz(
    assessment_id: int,
    request: Request,
    student: User = Depends(require_student),
    db: Session = Depends(get_db),
):
    assessment = db.get(Assessment, assessment_id)
    if assessment is None or assessment.context.student_id != student.id:
        raise HTTPException(status_code=404, detail="Quiz not found")

    form = await request.form()
    source = assessment.context.source_text
    scores: list[float] = []
    dist = analytics.empty_distribution()

    for q in assessment.questions:
        if q.answer is None:
            q.answer = Answer(question_id=q.id)

        if q.qtype == config.QUESTION_MCQ:
            raw = form.get(f"choice_{q.id}")
            selected = int(raw) if raw not in (None, "") else None
            graded = assess.grade_mcq(q.correct_index, selected)
            q.answer.modality = "choice"
            q.answer.selected_index = selected
            q.answer.text = q.options[selected] if selected is not None and 0 <= selected < len(q.options) else ""
        else:
            modality = str(form.get(f"modality_{q.id}", "typing"))
            answer_text = str(form.get(f"answer_{q.id}", "")).strip()
            upload = form.get(f"file_{q.id}")
            if hasattr(upload, "filename") and upload.filename:
                path = str(_save_upload(upload))
                if modality == "writing":
                    answer_text = ingest.extract_image_text(path)
                elif modality == "speaking":
                    answer_text = ingest.transcribe_audio(path)
            graded = assess.grade_answer(q.text, answer_text, source)
            q.answer.modality = modality
            q.answer.text = answer_text

        q.answer.score = graded["score"]
        q.answer.feedback = graded["feedback"]
        q.answer.resulting_level = graded["level"]
        scores.append(graded["score"])
        if graded["level"] in dist:
            dist[graded["level"]] += 1

    assessment.score = round(sum(scores) / len(scores), 1) if scores else 0.0
    assessment.completed_at = datetime.now(timezone.utc)
    analytics.record_snapshot(db, assessment.context, "assessment", dist)
    db.commit()
    return RedirectResponse(f"/student/quiz/{assessment.id}", status_code=303)
