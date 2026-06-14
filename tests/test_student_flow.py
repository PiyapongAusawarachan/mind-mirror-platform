"""End-to-end student flow using the mock AI path (no API key)."""

from tests.conftest import register


def _login_student(client):
    register(client, "Alice", "alice@example.com", role="student")
    client.post("/login", data={"email": "alice@example.com", "password": "password123"})


def test_full_student_journey(client):
    _login_student(client)

    # Create a lesson.
    r = client.post("/student/lessons", data={"title": "Functions"}, follow_redirects=False)
    assert r.status_code == 303
    lesson_url = r.headers["location"]
    assert "/student/lessons/" in lesson_url

    # Add an explanation (typed).
    r = client.post(
        lesson_url + "/explain",
        data={"modality": "typing", "text": "A function is a reusable block of code with parameters and scope."},
        follow_redirects=False,
    )
    assert r.status_code == 303

    # Analyze -> creates a knowledge map + snapshot.
    r = client.post(lesson_url + "/analyze", follow_redirects=False)
    assert r.status_code == 303

    # The wizard puts the knowledge map on its own step page.
    page = client.get(lesson_url + "/step/map")
    assert page.status_code == 200
    assert "cy" in page.text  # knowledge map container rendered

    # Generate a quiz.
    r = client.post(lesson_url + "/quiz", follow_redirects=False)
    assert r.status_code == 303
    quiz_url = r.headers["location"]
    assert "/student/quiz/" in quiz_url

    quiz_page = client.get(quiz_url)
    assert quiz_page.status_code == 200


def test_cannot_access_others_lesson(client):
    _login_student(client)
    client.post("/student/lessons", data={"title": "Mine"})

    # Second student should not see the first one's lesson #1.
    register(client, "Mallory", "mallory@example.com", role="student")
    client.post("/login", data={"email": "mallory@example.com", "password": "password123"})
    r = client.get("/student/lessons/1")
    assert r.status_code == 404


def test_requires_login(client):
    r = client.get("/student", follow_redirects=False)
    assert r.status_code in (401, 303, 307)
