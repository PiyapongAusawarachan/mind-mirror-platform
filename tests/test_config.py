"""Configuration safety checks."""

from __future__ import annotations

import importlib
import sys

import pytest


def test_production_requires_persistent_database(monkeypatch):
    """Production must not silently use ephemeral SQLite."""

    monkeypatch.setenv("ENV", "production")
    monkeypatch.delenv("DATABASE_URL", raising=False)
    monkeypatch.delenv("REQUIRE_PERSISTENT_DB", raising=False)
    sys.modules.pop("app.config", None)

    with pytest.raises(RuntimeError, match="DATABASE_URL"):
        importlib.import_module("app.config")

    sys.modules.pop("app.config", None)

