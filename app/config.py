"""Application settings and filesystem paths."""

from __future__ import annotations

import os
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()

ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = ROOT / "data"
UPLOAD_DIR = DATA_DIR / "uploads"
DB_PATH = DATA_DIR / "mind_mirror.db"

ENV = os.getenv("ENV", "development").lower()
IS_PRODUCTION = ENV == "production"

_raw_database_url = os.getenv("DATABASE_URL", f"sqlite:///{DB_PATH}")
if _raw_database_url.startswith("postgres://"):
    DATABASE_URL = _raw_database_url.replace("postgres://", "postgresql+psycopg://", 1)
elif _raw_database_url.startswith("postgresql://"):
    DATABASE_URL = _raw_database_url.replace("postgresql://", "postgresql+psycopg://", 1)
else:
    DATABASE_URL = _raw_database_url
USING_SQLITE = DATABASE_URL.startswith("sqlite")
REQUIRE_PERSISTENT_DB = os.getenv(
    "REQUIRE_PERSISTENT_DB",
    "true" if IS_PRODUCTION else "false",
).lower() == "true"
if IS_PRODUCTION and REQUIRE_PERSISTENT_DB and USING_SQLITE:
    raise RuntimeError(
        "Production is configured to require persistent storage, but DATABASE_URL "
        "is missing or points to SQLite. Set DATABASE_URL to a managed Postgres "
        "connection string before deploying."
    )
SECRET_KEY = os.getenv("SECRET_KEY", "dev-insecure-change-me")

ALLOWED_HOSTS = [h.strip() for h in os.getenv("ALLOWED_HOSTS", "*").split(",") if h.strip()]

SECURE_COOKIES = os.getenv("SECURE_COOKIES", "true" if IS_PRODUCTION else "false").lower() == "true"
FORCE_HTTPS = os.getenv("FORCE_HTTPS", "false").lower() == "true"

DEFAULT_LANG = os.getenv("DEFAULT_LANG", "th")

# AI provider: "gemini" (Google) or "openai"
AI_PROVIDER = os.getenv("AI_PROVIDER", "gemini").lower().strip()

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "").strip()
OPENAI_MODEL = os.getenv("OPENAI_MODEL", "gpt-4o-mini")
OPENAI_VISION_MODEL = os.getenv("OPENAI_VISION_MODEL", "gpt-4o-mini")
OPENAI_TRANSCRIBE_MODEL = os.getenv("OPENAI_TRANSCRIBE_MODEL", "whisper-1")

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "").strip()
GEMINI_MODEL = os.getenv("GEMINI_MODEL", "gemini-2.5-flash")
GEMINI_VISION_MODEL = os.getenv("GEMINI_VISION_MODEL", GEMINI_MODEL)

if AI_PROVIDER == "gemini":
    AI_ENABLED = bool(GEMINI_API_KEY)
    AI_PROVIDER_NAME = "Gemini"
else:
    AI_PROVIDER = "openai"
    AI_ENABLED = bool(OPENAI_API_KEY)
    AI_PROVIDER_NAME = "OpenAI"

# Understanding levels used across analysis, the knowledge map, and dashboards.
UNDERSTOOD = "understood"
CONFUSED = "confused"
NOT_UNDERSTOOD = "not_understood"
LEVELS = (UNDERSTOOD, CONFUSED, NOT_UNDERSTOOD)

LEVEL_RANK = {NOT_UNDERSTOOD: 0, CONFUSED: 1, UNDERSTOOD: 2}
LEVEL_WEIGHT = {NOT_UNDERSTOOD: 0.0, CONFUSED: 0.5, UNDERSTOOD: 1.0}

LEVEL_COLORS = {
    UNDERSTOOD: "#16a34a",
    CONFUSED: "#f59e0b",
    NOT_UNDERSTOOD: "#ef4444",
}

QUESTION_OPEN = "open"
QUESTION_MCQ = "mcq"


def ensure_dirs() -> None:
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
