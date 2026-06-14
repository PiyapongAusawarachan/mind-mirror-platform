"""Registration, login, logout."""

from __future__ import annotations

from fastapi import APIRouter, Depends, Form, Request
from fastapi.responses import RedirectResponse
from sqlalchemy import select
from sqlalchemy.orm import Session

from app import auth, i18n, themes
from app.database import get_db
from app.models import Course, User
from app.templating import current_lang, render

router = APIRouter()

MIN_PASSWORD = 8


@router.get("/login")
def login_form(request: Request):
    return render(request, "login.html", {"error": None})


@router.post("/login")
def login(
    request: Request,
    email: str = Form(...),
    password: str = Form(...),
    db: Session = Depends(get_db),
):
    user = db.scalar(select(User).where(User.email == email.strip().lower()))
    if user is None or not auth.verify_password(password, user.password_hash):
        msg = i18n.translate(current_lang(request), "auth.invalid")
        return render(request, "login.html", {"error": msg})
    auth.login_user(request, user)
    return RedirectResponse("/", status_code=303)


def _register_context(db: Session, **extra) -> dict:
    ctx = {
        "error": None,
        "courses": db.scalars(select(Course)).all(),
        "personalities": themes.PERSONALITIES,
        "cartoon_themes": themes.CARTOON_THEMES,
    }
    ctx.update(extra)
    return ctx


@router.get("/register")
def register_form(request: Request, db: Session = Depends(get_db)):
    return render(request, "register.html", _register_context(db))


@router.post("/register")
def register(
    request: Request,
    name: str = Form(...),
    email: str = Form(...),
    password: str = Form(...),
    role: str = Form(...),
    course_id: str = Form(""),
    personality: str = Form("logical"),
    cartoon: str = Form(""),
    db: Session = Depends(get_db),
):
    email = email.strip().lower()
    if role not in {"student", "teacher"}:
        role = "student"

    lang = current_lang(request)

    if len(password) < MIN_PASSWORD:
        return render(request, "register.html",
                      _register_context(db, error=i18n.translate(lang, "auth.password_short")))
    if db.scalar(select(User).where(User.email == email)):
        return render(request, "register.html",
                      _register_context(db, error=i18n.translate(lang, "auth.email_taken")))

    personality = themes.normalize_personality(personality)
    theme = themes.resolve_theme(personality, cartoon)

    user = User(
        name=name.strip(),
        email=email,
        password_hash=auth.hash_password(password),
        role=role,
        course_id=int(course_id) if (role == "student" and course_id) else None,
        personality=personality,
        theme=theme,
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    auth.login_user(request, user)
    return RedirectResponse("/", status_code=303)


@router.get("/logout")
def logout(request: Request):
    auth.logout_user(request)
    return RedirectResponse("/", status_code=303)
