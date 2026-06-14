"""User customization: personality + theme."""

from __future__ import annotations

from fastapi import APIRouter, Depends, Form, Request
from fastapi.responses import RedirectResponse
from sqlalchemy.orm import Session

from app import themes
from app.auth import require_user
from app.database import get_db
from app.models import User
from app.templating import render

router = APIRouter()


def _current_cartoon(user: User) -> str:
    """The user's theme is a cartoon theme only if it isn't a personality theme."""

    return user.theme if user.theme in themes.CARTOON_THEMES else ""


@router.get("/settings")
def settings_form(request: Request, user: User = Depends(require_user)):
    return render(
        request,
        "settings.html",
        {
            "user": user,
            "personalities": themes.PERSONALITIES,
            "cartoon_themes": themes.CARTOON_THEMES,
            "current_personality": themes.normalize_personality(user.personality),
            "current_cartoon": _current_cartoon(user),
            "saved": request.query_params.get("saved") == "1",
        },
    )


@router.post("/settings")
def update_settings(
    request: Request,
    personality: str = Form("logical"),
    cartoon: str = Form(""),
    user: User = Depends(require_user),
    db: Session = Depends(get_db),
):
    user.personality = themes.normalize_personality(personality)
    user.theme = themes.resolve_theme(user.personality, cartoon)
    db.commit()
    request.session["theme"] = user.theme
    return RedirectResponse("/settings?saved=1", status_code=303)
