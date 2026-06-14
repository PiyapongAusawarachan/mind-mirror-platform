"""Cross-cutting routes: language switching, health check."""

from __future__ import annotations

from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse, RedirectResponse

from app import i18n

router = APIRouter()


@router.get("/lang/{code}")
def set_language(code: str, request: Request):
    request.session["lang"] = i18n.normalize_lang(code)
    referer = request.headers.get("referer", "/")
    return RedirectResponse(referer, status_code=303)


@router.get("/healthz")
def health() -> JSONResponse:
    return JSONResponse({"status": "ok"})
