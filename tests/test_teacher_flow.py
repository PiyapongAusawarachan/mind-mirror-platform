from tests.conftest import register


def test_teacher_dashboard_and_course(client):
    register(client, "Dr. Smith", "teacher@example.com", role="teacher")
    client.post("/login", data={"email": "teacher@example.com", "password": "password123"})

    r = client.post("/teacher/courses", data={"name": "Programming II"}, follow_redirects=False)
    assert r.status_code == 303

    dash = client.get("/teacher")
    assert dash.status_code == 200
    assert "Programming II" in dash.text


def test_student_cannot_access_teacher(client):
    register(client, "Alice", "alice@example.com", role="student")
    client.post("/login", data={"email": "alice@example.com", "password": "password123"})
    r = client.get("/teacher")
    assert r.status_code == 403


def test_teacher_sees_student_progress(client):
    # Teacher creates a course.
    register(client, "Teacher", "t@example.com", role="teacher")
    client.post("/login", data={"email": "t@example.com", "password": "password123"})
    client.post("/teacher/courses", data={"name": "Course A"})
    client.get("/logout")

    # Student joins course #1 and completes the flow.
    register(client, "Stu", "stu@example.com", role="student", course_id="1")
    client.post("/login", data={"email": "stu@example.com", "password": "password123"})
    r = client.post("/student/lessons", data={"title": "Loops"}, follow_redirects=False)
    lesson_url = r.headers["location"]
    client.post(lesson_url + "/explain", data={"modality": "typing", "text": "Loops repeat code."})
    client.post(lesson_url + "/analyze")
    client.get("/logout")

    # Teacher should now see the student row.
    client.post("/login", data={"email": "t@example.com", "password": "password123"})
    dash = client.get("/teacher")
    assert "Stu" in dash.text
    assert "Loops" in dash.text
