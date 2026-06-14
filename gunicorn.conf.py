"""Gunicorn config for production: Uvicorn workers serving the ASGI app."""

import multiprocessing
import os

port = os.getenv("PORT", "8000")
bind = os.getenv("BIND", f"0.0.0.0:{port}")
workers = int(os.getenv("WEB_CONCURRENCY", multiprocessing.cpu_count() * 2 + 1))
worker_class = "uvicorn.workers.UvicornWorker"
timeout = int(os.getenv("TIMEOUT", "60"))
accesslog = "-"
errorlog = "-"
loglevel = os.getenv("LOG_LEVEL", "info")
