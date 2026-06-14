"""Turn uploaded materials and inputs into text.

- PDF  -> pypdf local extraction
- Image -> OpenAI vision OCR (handwriting + printed), mock fallback otherwise
- Audio -> OpenAI Whisper transcription, mock fallback otherwise
"""

from __future__ import annotations

import base64
import mimetypes
from pathlib import Path

from app import config
from app.ai import client


def extract_pdf_text(path: str) -> str:
    from pypdf import PdfReader

    try:
        reader = PdfReader(path)
    except Exception as exc:  # corrupt/unreadable file
        return f"[Could not read PDF: {exc}]"
    parts = [(page.extract_text() or "") for page in reader.pages]
    text = "\n".join(parts).strip()
    return text or "[No selectable text found in PDF]"


def extract_image_text(path: str) -> str:
    if not config.AI_ENABLED:
        return f"[Mock OCR] Text extracted from image '{Path(path).name}'."

    mime = mimetypes.guess_type(path)[0] or "image/png"
    data = base64.b64encode(Path(path).read_bytes()).decode()
    content = [
        {"type": "text", "text": "Transcribe all text in this image. Return JSON {\"text\": ...}."},
        {"type": "image_url", "image_url": {"url": f"data:{mime};base64,{data}"}},
    ]
    try:
        result = client.chat_json(
            "You are an OCR engine. Transcribe printed and handwritten text faithfully.",
            content,
            model=client.vision_model(),
        )
        return str(result.get("text", "")).strip() or "[No text detected in image]"
    except Exception as exc:  # pragma: no cover
        return f"[Image OCR failed: {exc}]"


def transcribe_audio(path: str) -> str:
    if not config.AI_ENABLED:
        return f"[Mock transcript] Spoken explanation from '{Path(path).name}'."
    try:
        return client.transcribe(path).strip()
    except Exception as exc:  # pragma: no cover
        return f"[Audio transcription failed: {exc}]"
