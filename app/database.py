"""SQLAlchemy engine, session, and base."""

from __future__ import annotations

from collections.abc import Iterator

from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker

from app.config import DATABASE_URL

connect_args = {"check_same_thread": False} if DATABASE_URL.startswith("sqlite") else {}
engine = create_engine(DATABASE_URL, connect_args=connect_args)
SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)


class Base(DeclarativeBase):
    pass


def get_db() -> Iterator[Session]:
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def init_db() -> None:
    from app import models  # noqa: F401  (register mappers)

    Base.metadata.create_all(bind=engine)
    _ensure_columns()
    _backfill_enrollments()


# Columns added after the first release. We add them in-place so existing
# databases keep working without a full migration tool.
_ADDED_COLUMNS = {
    "learning_contexts": {
        "summary": "TEXT DEFAULT ''",
        "summary_points_json": "TEXT DEFAULT ''",
        "course_id": "INTEGER",
    },
    "users": {
        "personality": "VARCHAR(20) DEFAULT 'logical'",
        "theme": "VARCHAR(20) DEFAULT 'indigo'",
        "plan": "VARCHAR(20) DEFAULT 'free'",
    },
}


def _ensure_columns() -> None:
    from sqlalchemy import inspect, text

    inspector = inspect(engine)
    existing_tables = set(inspector.get_table_names())
    with engine.begin() as conn:
        for table, columns in _ADDED_COLUMNS.items():
            if table not in existing_tables:
                continue
            present = {col["name"] for col in inspector.get_columns(table)}
            for name, ddl in columns.items():
                if name not in present:
                    conn.execute(text(f'ALTER TABLE {table} ADD COLUMN {name} {ddl}'))


def _backfill_enrollments() -> None:
    """Migrate legacy single-course students to the enrollments table.

    Earlier versions stored one course per student in ``users.course_id``. Create
    matching enrollment rows (and link their lessons to that course) so existing
    accounts keep working with the new multi-course model.
    """

    from app.models import Enrollment, LearningContext, User

    session = SessionLocal()
    try:
        legacy = session.query(User).filter(User.course_id.isnot(None)).all()
        changed = False
        for user in legacy:
            exists = (
                session.query(Enrollment)
                .filter(Enrollment.student_id == user.id, Enrollment.course_id == user.course_id)
                .first()
            )
            if exists is None:
                session.add(Enrollment(student_id=user.id, course_id=user.course_id))
                changed = True
            for ctx in user.contexts:
                if ctx.course_id is None:
                    ctx.course_id = user.course_id
                    changed = True
        if changed:
            session.commit()
    finally:
        session.close()
