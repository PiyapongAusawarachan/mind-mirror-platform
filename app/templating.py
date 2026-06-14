"""Shared Jinja2 templates with per-request i18n injection."""

from __future__ import annotations

from typing import Any

from fastapi import Request
from fastapi.templating import Jinja2Templates

from app import config, i18n, themes

templates = Jinja2Templates(directory=str(config.ROOT / "app" / "templates"))
templates.env.globals["LEVEL_COLORS"] = config.LEVEL_COLORS
templates.env.globals["LEVELS"] = config.LEVELS
templates.env.globals["AI_ENABLED"] = config.AI_ENABLED
templates.env.globals["AI_PROVIDER_NAME"] = config.AI_PROVIDER_NAME
templates.env.globals["LANGUAGES"] = i18n.LANGUAGES
templates.env.globals["QUESTION_OPEN"] = config.QUESTION_OPEN
templates.env.globals["QUESTION_MCQ"] = config.QUESTION_MCQ


def current_lang(request: Request) -> str:
    return i18n.normalize_lang(request.session.get("lang"))


def render(request: Request, template: str, context: dict[str, Any] | None = None):
    """Render a template with translation helpers available in the context."""

    lang = current_lang(request)
    theme = themes.normalize_theme(request.session.get("theme"))
    ctx: dict[str, Any] = {
        "request": request,
        "lang": lang,
        "t": lambda key: i18n.translate(lang, key),
        "LEVEL_LABELS": i18n.level_labels(lang),
        "theme": theme,
        "theme_emoji": themes.theme_emoji(theme),
    }
    if context:
        ctx.update(context)
    return templates.TemplateResponse(template, ctx)
