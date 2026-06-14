# Mind Mirror Platform

A bilingual (ไทย / English) learning platform that reflects a student's gaps in
understanding back to them, and gives teachers a clear view of who understands what.
Built with FastAPI + OpenAI.

Two roles:

- **Student** — upload material, explain it in their own words (type / photo / audio),
  see a **knowledge map** of understood / confused / missing subtopics, take a
  **personalized quiz** (open-ended **and** multiple-choice, answerable by typing,
  photo, or audio), and track **progress over time**.
- **Teacher** — a dashboard of each student's understanding before vs after assessment,
  quiz scores, improvement, per-topic understanding pie charts, and a long-term mastery trend.

## Quick start (local)

```sh
cd ~/Documents/mind_mirror_platform
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt

cp .env.example .env          # optional: add OPENAI_API_KEY for real AI
python seed.py                # optional: demo teacher + 2 students with multi-week history
python run.py                 # open http://127.0.0.1:8000
```

> Without `OPENAI_API_KEY` the app runs end-to-end with heuristic/mock AI, so it works
> offline. Add a key to `.env` for real analysis, OCR, speech-to-text, and grading.

### Demo logins (after `python seed.py`)

Password for all: `demo1234`

- Teacher: `teacher@example.com`
- Students: `alice@example.com`, `bob@example.com`

## Features

| Area | What it does |
|------|--------------|
| Learning context | Upload PDF (text extracted) or images (OCR) |
| Multi-modal explain | Type, photo of handwriting (OCR), or audio (Whisper) |
| Knowledge map | Subtopics classified + connected (Cytoscape.js) |
| Personalized quiz | Open-ended **+ multiple-choice**, AI/auto graded, no fixed format |
| Quiz answers | Type, upload photo, or upload audio per question |
| Progress timeline | Mastery % over time per lesson + course-wide trend |
| Teacher dashboard | Per-student before/after, scores, improvement, per-topic pies |
| Internationalization | Thai (default) + English, switchable in the top bar |
| Security | Secure session cookies, security headers, trusted hosts, optional HTTPS redirect |

## Tests

```sh
pip install -r requirements-dev.txt
pytest
```

## Production (Docker + Postgres)

```sh
# Set a strong SECRET_KEY (and OPENAI_API_KEY if desired) in your shell or .env
docker compose up --build
# app on http://localhost:8000, Postgres-backed
```

Key production env vars (see `.env.example`):

- `ENV=production`, `SECRET_KEY=<long random>`
- `DATABASE_URL=postgresql+psycopg://user:pass@db:5432/mindmirror`
- `ALLOWED_HOSTS=yourdomain.com`, `SECURE_COOKIES=true`, `FORCE_HTTPS=true`

Without Docker, run under gunicorn + Uvicorn workers:

```sh
gunicorn -c gunicorn.conf.py app.main:app
```

## Structure

| Path | Role |
|------|------|
| `app/main.py` | FastAPI app, security middleware, routing |
| `app/config.py` | Settings, env, levels, paths |
| `app/i18n.py` | Thai/English translation tables |
| `app/database.py`, `app/models.py` | SQLAlchemy (SQLite / Postgres) |
| `app/auth.py` | Session auth + role guards |
| `app/analytics.py` | Distributions, improvement, mastery timeline |
| `app/ai/` | OpenAI layer: `ingest`, `analyze`, `assess` (open + MCQ) |
| `app/routers/` | `auth`, `student`, `teacher`, `common` (lang/health) |
| `app/templates/`, `app/static/` | Jinja2 UI, knowledge map, charts, timeline |
| `tests/` | pytest suite (auth, student, teacher, units) |
| `run.py`, `seed.py` | Dev server, demo data |
| `Dockerfile`, `docker-compose.yml`, `gunicorn.conf.py` | Production deploy |
| `docs/` | Proposal, scope, workflow |

## Tech

Python · FastAPI · SQLAlchemy (SQLite/Postgres) · Jinja2 · OpenAI (chat + vision + Whisper) ·
Cytoscape.js · Chart.js · gunicorn/uvicorn · Docker.
