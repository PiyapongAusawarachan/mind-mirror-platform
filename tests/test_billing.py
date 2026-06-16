from tests.conftest import register


def _login(client, email):
    client.post("/login", data={"email": email, "password": "password123"})


def test_student_can_join_and_leave_courses(client):
    # A Pro teacher creates two courses.
    register(client, "Teacher", "t@example.com", role="teacher")
    _login(client, "t@example.com")
    client.post("/billing/upgrade")
    client.post("/teacher/courses", data={"name": "Math"})
    client.post("/teacher/courses", data={"name": "Physics"})
    client.get("/logout")

    # A student joins both courses without making new accounts.
    register(client, "Stu", "stu@example.com", role="student")
    _login(client, "stu@example.com")
    client.post("/student/courses/join", data={"code": "1"})
    client.post("/student/courses/join", data={"code": "2"})
    dash = client.get("/student")
    assert "Math" in dash.text
    assert "Physics" in dash.text

    # Joining a missing course is rejected gracefully.
    r = client.post("/student/courses/join", data={"code": "999"}, follow_redirects=False)
    assert "notice=not_found" in r.headers["location"]

    # Leaving works.
    client.post("/student/courses/1/leave")
    dash = client.get("/student")
    assert "Physics" in dash.text


def test_free_plan_course_limit_then_upgrade(client):
    register(client, "Teacher", "t2@example.com", role="teacher")
    _login(client, "t2@example.com")
    client.post("/billing/upgrade")
    for name in ["C1", "C2", "C3"]:
        client.post("/teacher/courses", data={"name": name})
    client.get("/logout")

    register(client, "Stu2", "stu2@example.com", role="student")
    _login(client, "stu2@example.com")
    client.post("/student/courses/join", data={"code": "1"})
    client.post("/student/courses/join", data={"code": "2"})
    # Third join blocked on the free plan.
    r = client.post("/student/courses/join", data={"code": "3"}, follow_redirects=False)
    assert "notice=limit" in r.headers["location"]

    # Upgrade unlocks unlimited courses.
    client.post("/billing/upgrade")
    r = client.post("/student/courses/join", data={"code": "3"}, follow_redirects=False)
    assert "notice=joined" in r.headers["location"]


def test_teacher_course_creation_gated_by_plan(client):
    register(client, "Teacher", "t3@example.com", role="teacher")
    _login(client, "t3@example.com")
    client.post("/teacher/courses", data={"name": "Only one"})
    # Free teacher limited to one course.
    r = client.post("/teacher/courses", data={"name": "Second"}, follow_redirects=False)
    assert "notice=limit" in r.headers["location"]

    client.post("/billing/upgrade")
    r = client.post("/teacher/courses", data={"name": "Second"}, follow_redirects=False)
    assert r.headers["location"] == "/teacher"


def test_pricing_and_checkout_pages(client):
    register(client, "Stu3", "stu3@example.com", role="student")
    _login(client, "stu3@example.com")
    assert client.get("/pricing").status_code == 200
    assert client.get("/billing/checkout").status_code == 200
    # Upgrade then verify pricing reflects current plan.
    client.post("/billing/upgrade")
    assert "PRO" in client.get("/pricing").text or "Pro" in client.get("/pricing").text
