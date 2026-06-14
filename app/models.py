"""ORM models for users, learning contexts, analysis, and assessments."""

from __future__ import annotations

import json
from datetime import datetime, timezone

from sqlalchemy import DateTime, Float, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


def _now() -> datetime:
    return datetime.now(timezone.utc)


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(120))
    email: Mapped[str] = mapped_column(String(255), unique=True, index=True)
    password_hash: Mapped[str] = mapped_column(String(255))
    role: Mapped[str] = mapped_column(String(20))  # "student" | "teacher"
    course_id: Mapped[int | None] = mapped_column(ForeignKey("courses.id"), nullable=True)
    personality: Mapped[str] = mapped_column(String(20), default="logical")
    theme: Mapped[str] = mapped_column(String(20), default="indigo")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=_now)

    course: Mapped["Course | None"] = relationship(
        back_populates="students", foreign_keys=[course_id]
    )
    contexts: Mapped[list["LearningContext"]] = relationship(
        back_populates="student", cascade="all, delete-orphan"
    )


class Course(Base):
    __tablename__ = "courses"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(160))
    teacher_id: Mapped[int] = mapped_column(ForeignKey("users.id"))
    created_at: Mapped[datetime] = mapped_column(DateTime, default=_now)

    teacher: Mapped["User"] = relationship(foreign_keys=[teacher_id])
    students: Mapped[list["User"]] = relationship(
        back_populates="course", foreign_keys="User.course_id"
    )


class LearningContext(Base):
    """A topic/lesson a student is studying, plus their uploaded materials."""

    __tablename__ = "learning_contexts"

    id: Mapped[int] = mapped_column(primary_key=True)
    student_id: Mapped[int] = mapped_column(ForeignKey("users.id"))
    title: Mapped[str] = mapped_column(String(200))
    source_text: Mapped[str] = mapped_column(Text, default="")  # extracted material text
    summary: Mapped[str] = mapped_column(Text, default="")  # AI summary of the material
    summary_points_json: Mapped[str] = mapped_column(Text, default="")  # JSON list[str] key points
    created_at: Mapped[datetime] = mapped_column(DateTime, default=_now)

    student: Mapped["User"] = relationship(back_populates="contexts")

    @property
    def summary_points(self) -> list[str]:
        if not self.summary_points_json:
            return []
        try:
            data = json.loads(self.summary_points_json)
            return [str(p) for p in data] if isinstance(data, list) else []
        except (ValueError, TypeError):
            return []
    materials: Mapped[list["Material"]] = relationship(
        back_populates="context", cascade="all, delete-orphan"
    )
    explanations: Mapped[list["Explanation"]] = relationship(
        back_populates="context", cascade="all, delete-orphan"
    )
    analyses: Mapped[list["Analysis"]] = relationship(
        back_populates="context", cascade="all, delete-orphan", order_by="Analysis.created_at"
    )
    assessments: Mapped[list["Assessment"]] = relationship(
        back_populates="context", cascade="all, delete-orphan", order_by="Assessment.created_at"
    )
    snapshots: Mapped[list["MasterySnapshot"]] = relationship(
        back_populates="context", cascade="all, delete-orphan", order_by="MasterySnapshot.created_at"
    )


class Material(Base):
    __tablename__ = "materials"

    id: Mapped[int] = mapped_column(primary_key=True)
    context_id: Mapped[int] = mapped_column(ForeignKey("learning_contexts.id"))
    filename: Mapped[str] = mapped_column(String(255))
    filepath: Mapped[str] = mapped_column(String(500))
    kind: Mapped[str] = mapped_column(String(20))  # "pdf" | "image"
    extracted_text: Mapped[str] = mapped_column(Text, default="")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=_now)

    context: Mapped["LearningContext"] = relationship(back_populates="materials")


class Explanation(Base):
    """A student's own-words explanation (typed, written photo, or spoken)."""

    __tablename__ = "explanations"

    id: Mapped[int] = mapped_column(primary_key=True)
    context_id: Mapped[int] = mapped_column(ForeignKey("learning_contexts.id"))
    modality: Mapped[str] = mapped_column(String(20))  # "typing" | "writing" | "speaking"
    text: Mapped[str] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=_now)

    context: Mapped["LearningContext"] = relationship(back_populates="explanations")


class Analysis(Base):
    """Result of comparing an explanation against source material."""

    __tablename__ = "analyses"

    id: Mapped[int] = mapped_column(primary_key=True)
    context_id: Mapped[int] = mapped_column(ForeignKey("learning_contexts.id"))
    summary: Mapped[str] = mapped_column(Text, default="")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=_now)

    context: Mapped["LearningContext"] = relationship(back_populates="analyses")
    topics: Mapped[list["Topic"]] = relationship(
        back_populates="analysis", cascade="all, delete-orphan"
    )
    edges: Mapped[list["TopicEdge"]] = relationship(
        back_populates="analysis", cascade="all, delete-orphan"
    )


class Topic(Base):
    """A subtopic node in the knowledge map with an understanding level."""

    __tablename__ = "topics"

    id: Mapped[int] = mapped_column(primary_key=True)
    analysis_id: Mapped[int] = mapped_column(ForeignKey("analyses.id"))
    name: Mapped[str] = mapped_column(String(200))
    level: Mapped[str] = mapped_column(String(20))  # understood | confused | not_understood
    detail: Mapped[str] = mapped_column(Text, default="")

    analysis: Mapped["Analysis"] = relationship(back_populates="topics")


class TopicEdge(Base):
    """A relationship between two subtopics (knowledge map edge)."""

    __tablename__ = "topic_edges"

    id: Mapped[int] = mapped_column(primary_key=True)
    analysis_id: Mapped[int] = mapped_column(ForeignKey("analyses.id"))
    source: Mapped[str] = mapped_column(String(200))
    target: Mapped[str] = mapped_column(String(200))
    relation: Mapped[str] = mapped_column(String(120), default="related to")

    analysis: Mapped["Analysis"] = relationship(back_populates="edges")


class Assessment(Base):
    """A personalized question set targeting a student's weak areas."""

    __tablename__ = "assessments"

    id: Mapped[int] = mapped_column(primary_key=True)
    context_id: Mapped[int] = mapped_column(ForeignKey("learning_contexts.id"))
    score: Mapped[float | None] = mapped_column(Float, nullable=True)  # 0..100
    completed_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=_now)

    context: Mapped["LearningContext"] = relationship(back_populates="assessments")
    questions: Mapped[list["Question"]] = relationship(
        back_populates="assessment", cascade="all, delete-orphan"
    )


class Question(Base):
    __tablename__ = "questions"

    id: Mapped[int] = mapped_column(primary_key=True)
    assessment_id: Mapped[int] = mapped_column(ForeignKey("assessments.id"))
    topic_name: Mapped[str] = mapped_column(String(200))
    text: Mapped[str] = mapped_column(Text)
    target_level: Mapped[str] = mapped_column(String(20))  # the weak level it targets
    qtype: Mapped[str] = mapped_column(String(10), default="open")  # "open" | "mcq"
    options_json: Mapped[str] = mapped_column(Text, default="")  # JSON list[str] for mcq
    correct_index: Mapped[int | None] = mapped_column(Integer, nullable=True)

    assessment: Mapped["Assessment"] = relationship(back_populates="questions")
    answer: Mapped["Answer | None"] = relationship(
        back_populates="question", cascade="all, delete-orphan", uselist=False
    )

    @property
    def options(self) -> list[str]:
        if not self.options_json:
            return []
        try:
            return json.loads(self.options_json)
        except (ValueError, TypeError):
            return []


class Answer(Base):
    __tablename__ = "answers"

    id: Mapped[int] = mapped_column(primary_key=True)
    question_id: Mapped[int] = mapped_column(ForeignKey("questions.id"))
    modality: Mapped[str] = mapped_column(String(20))  # typing | writing | speaking | choice
    text: Mapped[str] = mapped_column(Text)
    selected_index: Mapped[int | None] = mapped_column(Integer, nullable=True)  # for mcq
    score: Mapped[float] = mapped_column(Float, default=0.0)  # 0..100
    feedback: Mapped[str] = mapped_column(Text, default="")
    resulting_level: Mapped[str] = mapped_column(String(20), default="confused")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=_now)

    question: Mapped["Question"] = relationship(back_populates="answer")


class MasterySnapshot(Base):
    """A point-in-time understanding mix for a lesson (powers the timeline)."""

    __tablename__ = "mastery_snapshots"

    id: Mapped[int] = mapped_column(primary_key=True)
    context_id: Mapped[int] = mapped_column(ForeignKey("learning_contexts.id"))
    source: Mapped[str] = mapped_column(String(20))  # "analysis" | "assessment"
    understood: Mapped[int] = mapped_column(Integer, default=0)
    confused: Mapped[int] = mapped_column(Integer, default=0)
    not_understood: Mapped[int] = mapped_column(Integer, default=0)
    mastery_pct: Mapped[float] = mapped_column(Float, default=0.0)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=_now)

    context: Mapped["LearningContext"] = relationship(back_populates="snapshots")
