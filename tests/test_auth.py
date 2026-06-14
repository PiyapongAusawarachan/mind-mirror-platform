from tests.conftest import register


def test_health(client):
    assert client.get("/healthz").json() == {"status": "ok"}


def test_register_and_login(client):
    r = register(client, "Alice", "alice@example.com")
    assert r.status_code == 303

    r = client.post(
        "/login",
        data={"email": "alice@example.com", "password": "password123"},
        follow_redirects=False,
    )
    assert r.status_code == 303


def test_short_password_rejected(client):
    r = client.post(
        "/register",
        data={"name": "Bob", "email": "bob@example.com", "password": "short", "role": "student"},
        follow_redirects=True,
    )
    assert r.status_code == 200
    # Stays on the register page rather than logging in.
    assert "register" in r.url.path or "form" in r.text.lower()


def test_duplicate_email_rejected(client):
    register(client, "Alice", "dup@example.com")
    r = client.post(
        "/register",
        data={"name": "Alice2", "email": "dup@example.com", "password": "password123", "role": "student"},
        follow_redirects=True,
    )
    assert r.status_code == 200


def test_bad_login(client):
    r = client.post(
        "/login",
        data={"email": "nobody@example.com", "password": "x"},
        follow_redirects=True,
    )
    assert r.status_code == 200


def test_language_switch(client):
    r = client.get("/lang/en", headers={"referer": "/"}, follow_redirects=False)
    assert r.status_code == 303
    home = client.get("/")
    assert "Mind Mirror" in home.text
