"""Subscription plans and feature gating.

This is a demo/presentation billing model: there is no real payment. The
"Pro" upgrade is granted instantly so every feature can be shown, while the
plan tiers still demonstrate what would be locked/unlocked behind a paywall.

A value of ``None`` in a limit means "unlimited".
"""

from __future__ import annotations

FREE = "free"
PRO = "pro"

PLAN_IDS = (FREE, PRO)

# Display info for the pricing page (price is cosmetic — nothing is charged).
PLAN_INFO: dict[str, dict] = {
    FREE: {"price": "0", "emoji": "🎈"},
    PRO: {"price": "199", "emoji": "🚀"},
}

# Feature limits per plan. None = unlimited / fully unlocked.
LIMITS: dict[str, dict] = {
    FREE: {
        "max_courses_student": 2,
        "max_courses_teacher": 1,
        "timeline_points": 4,
        "advanced_analytics": False,
        "export": False,
    },
    PRO: {
        "max_courses_student": None,
        "max_courses_teacher": None,
        "timeline_points": None,
        "advanced_analytics": True,
        "export": True,
    },
}

# Feature keys shown (in order) on the pricing comparison.
FEATURE_KEYS = (
    "max_courses_student",
    "max_courses_teacher",
    "timeline_points",
    "advanced_analytics",
    "export",
)


def normalize_plan(value: str | None) -> str:
    return value if value in PLAN_IDS else FREE


def is_pro(plan: str | None) -> bool:
    return normalize_plan(plan) == PRO


def limit(plan: str | None, key: str):
    return LIMITS[normalize_plan(plan)].get(key)


def can_add(plan: str | None, key: str, current_count: int) -> bool:
    """Whether another item is allowed under this plan's limit for ``key``."""

    cap = limit(plan, key)
    if cap is None:
        return True
    return current_count < cap


def remaining(plan: str | None, key: str, current_count: int) -> int | None:
    cap = limit(plan, key)
    if cap is None:
        return None
    return max(0, cap - current_count)
