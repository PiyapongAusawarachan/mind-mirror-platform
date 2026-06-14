"""Customization (personality + cartoon themes) and the lesson wizard."""

from __future__ import annotations


def _register(client, email, **extra):
    data = {"name": "T", "email": email, "password": "password123", "role": "student"}
    data.update(extra)
    return client.post("/register", data=data, follow_redirects=False)


def test_cartoon_theme_overrides_personality(client):
    _register(client, "ninja@example.com", personality="creative", cartoon="ninja")
    page = client.get("/student")
    assert page.status_code == 200
    assert 'data-theme="ninja"' in page.text


def test_personality_drives_theme_when_no_cartoon(client):
    _register(client, "calm@example.com", personality="calm")
    page = client.get("/student")
    assert 'data-theme="ocean"' in page.text


def test_invalid_choices_fall_back_to_defaults(client):
    _register(client, "bad@example.com", personality="nonsense", cartoon="nope")
    page = client.get("/student")
    assert 'data-theme="indigo"' in page.text


def test_settings_updates_theme(client):
    _register(client, "set@example.com", personality="logical")
    assert client.get("/student").text.count('data-theme="indigo"')

    r = client.post("/settings", data={"personality": "energetic", "cartoon": ""}, follow_redirects=False)
    assert r.status_code == 303
    page = client.get("/settings")
    assert page.status_code == 200
    assert 'data-theme="sunset"' in page.text


def test_lesson_wizard_steps(client):
    _register(client, "wiz@example.com")
    r = client.post("/student/lessons", data={"title": "Topic"}, follow_redirects=False)
    lesson_url = r.headers["location"]

    # Bare lesson URL redirects into the wizard at the first step.
    redirect = client.get(lesson_url, follow_redirects=False)
    assert redirect.status_code == 303
    assert redirect.headers["location"].endswith("/step/material")

    for step in ("material", "explain", "map", "quiz", "progress"):
        page = client.get(lesson_url + f"/step/{step}")
        assert page.status_code == 200
        assert "stepper" in page.text
