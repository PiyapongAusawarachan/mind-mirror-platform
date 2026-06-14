FROM python:3.11-slim

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1

WORKDIR /app

# Install dependencies first for better layer caching.
COPY requirements.txt .
RUN pip install --upgrade pip && pip install -r requirements.txt

COPY . .

# Runtime data dir for SQLite + uploads (mount a volume in production).
RUN mkdir -p data/uploads

EXPOSE 8000

# entrypoint creates tables, then starts gunicorn.
CMD ["sh", "-c", "python -c 'from app.database import init_db; init_db()' && gunicorn -c gunicorn.conf.py app.main:app"]
