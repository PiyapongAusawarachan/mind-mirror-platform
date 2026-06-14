"""Shared pytest fixtures: isolated DB + test client."""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker


@pytest.fixture(autouse=True)
def force_mock_ai(monkeypatch):
    """Tests must be deterministic and must never spend external API quota."""

    from app import config

    monkeypatch.setattr(config, "AI_ENABLED", False)
    monkeypatch.setattr(config, "GEMINI_API_KEY", "")
    monkeypatch.setattr(config, "OPENAI_API_KEY", "")


@pytest.fixture()
def client(tmp_path, monkeypatch):
    # Use a throwaway SQLite file per test so state never leaks.
    db_file = tmp_path / "test.db"
    engine = create_engine(f"sqlite:///{db_file}", connect_args={"check_same_thread": False})
    TestingSession = sessionmaker(bind=engine, autoflush=False, autocommit=False)

    from app import database
    from app.database import Base
    import app.models  # noqa: F401  register models

    monkeypatch.setattr(database, "engine", engine)
    monkeypatch.setattr(database, "SessionLocal", TestingSession)
    Base.metadata.create_all(bind=engine)

    from app.main import app

    def _get_db():
        db = TestingSession()
        try:
            yield db
        finally:
            db.close()

    app.dependency_overrides[database.get_db] = _get_db
    with TestClient(app) as c:
        yield c
    app.dependency_overrides.clear()


def register(client, name, email, password="password123", role="student", course_id=""):
    return client.post(
        "/register",
        data={"name": name, "email": email, "password": password, "role": role, "course_id": course_id},
        follow_redirects=False,
    )
