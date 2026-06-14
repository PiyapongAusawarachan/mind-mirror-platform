"""Personality- and cartoon-driven UI themes.

A user answers a short personality question at sign-up (and can change it later
in Settings). That maps to a base color theme. They may optionally pick a
favorite cartoon style, which overrides the colors with a themed palette.

Themes are applied via ``<html data-theme="...">`` and matching CSS variable
overrides in ``styles.css``. Each theme also exposes a decorative accent emoji.
"""

from __future__ import annotations

DEFAULT_THEME = "indigo"
DEFAULT_PERSONALITY = "logical"

# personality id -> base color theme it selects
PERSONALITIES: dict[str, dict[str, str]] = {
    "logical": {"emoji": "🧠", "theme": "indigo"},
    "calm": {"emoji": "🌊", "theme": "ocean"},
    "energetic": {"emoji": "⚡", "theme": "sunset"},
    "creative": {"emoji": "🎨", "theme": "grape"},
    "friendly": {"emoji": "🌱", "theme": "forest"},
}

# cartoon style id -> decorative accent emoji
CARTOON_THEMES: dict[str, str] = {
    "ninja": "🍥",
    "pirate": "🏴‍☠️",
    "magical": "🌸",
    "hero": "🦸",
    "slayer": "⚔️",
    "sky": "☁️",
    "space": "🚀",
}

# accent emoji for the personality-driven base themes
_BASE_THEME_EMOJI: dict[str, str] = {
    "indigo": "🧠",
    "ocean": "🌊",
    "sunset": "⚡",
    "grape": "🎨",
    "forest": "🌱",
}

# Every valid theme id (base + cartoon).
ALL_THEMES: set[str] = (
    {DEFAULT_THEME}
    | {p["theme"] for p in PERSONALITIES.values()}
    | set(CARTOON_THEMES)
)


def normalize_personality(value: str | None) -> str:
    return value if value in PERSONALITIES else DEFAULT_PERSONALITY


def normalize_theme(value: str | None) -> str:
    return value if value in ALL_THEMES else DEFAULT_THEME


def normalize_cartoon(value: str | None) -> str:
    """Empty string means 'no cartoon theme, use personality colors'."""

    return value if value in CARTOON_THEMES else ""


def resolve_theme(personality: str | None, cartoon: str | None) -> str:
    """A chosen cartoon overrides personality colors; otherwise use personality."""

    cartoon = normalize_cartoon(cartoon)
    if cartoon:
        return cartoon
    return PERSONALITIES.get(normalize_personality(personality), {}).get("theme", DEFAULT_THEME)


def theme_emoji(theme: str | None) -> str:
    theme = normalize_theme(theme)
    if theme in CARTOON_THEMES:
        return CARTOON_THEMES[theme]
    return _BASE_THEME_EMOJI.get(theme, "🧠")
