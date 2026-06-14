"""FastAPI application factory and wiring."""

from __future__ import annotations

import sys
from pathlib import Path

# Allow `python app/main.py` from the project folder (fixes import path).
if __name__ == "__main__":
    _root = Path(__file__).resolve().parent.parent
    if str(_root) not in sys.path:
        sys.path.insert(0, str(_root))

from fastapi import Depends, FastAPI, Request
from fastapi.responses import RedirectResponse, Response
from fastapi.staticfiles import StaticFiles

try:
    from starlette.middleware.sessions import SessionMiddleware
except ModuleNotFoundError as exc:
    if exc.name == "itsdangerous":
        print(
            "Missing dependencies.\n"
            "  source .venv/bin/activate\n"
            "  pip install -r requirements.txt\n"
            "  python run.py\n"
            "Do not use global pyenv Python unless you installed requirements there too.",
            file=sys.stderr,
        )
        sys.exit(1)
    raise

from starlette.middleware.trustedhost import TrustedHostMiddleware

from app import config
from app.auth import get_current_user
from app.database import init_db
from app.models import User
from app.routers import auth as auth_router
from app.routers import common as common_router
from app.routers import student as student_router
from app.routers import teacher as teacher_router
from app.templating import render

config.ensure_dirs()

app = FastAPI(title="Mind Mirror Platform")


@app.middleware("http")
async def security_headers(request: Request, call_next):
    if config.FORCE_HTTPS and request.url.scheme == "http" and request.headers.get(
        "x-forwarded-proto", "http"
    ) != "https":
        return RedirectResponse(request.url.replace(scheme="https"), status_code=307)
    response: Response = await call_next(request)
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
    if config.IS_PRODUCTION:
        response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"
    return response


if config.ALLOWED_HOSTS and config.ALLOWED_HOSTS != ["*"]:
    app.add_middleware(TrustedHostMiddleware, allowed_hosts=config.ALLOWED_HOSTS)

app.add_middleware(
    SessionMiddleware,
    secret_key=config.SECRET_KEY,
    https_only=config.SECURE_COOKIES,
    same_site="lax",
)

app.mount("/static", StaticFiles(directory=str(config.ROOT / "app" / "static")), name="static")


@app.on_event("startup")
def _startup() -> None:
    init_db()


app.include_router(common_router.router)
app.include_router(auth_router.router)
app.include_router(student_router.router)
app.include_router(teacher_router.router)


@app.get("/")
def home(request: Request, user: User | None = Depends(get_current_user)):
    if user is None:
        return render(request, "home.html", {"user": None})
    target = "/student" if user.role == "student" else "/teacher"
    return RedirectResponse(target, status_code=303)


if __name__ == "__main__":
    import uvicorn

    uvicorn.run("app.main:app", host="127.0.0.1", port=8000, reload=True)
