import copy
import tempfile
import unittest
from pathlib import Path

from fastapi.testclient import TestClient

from src import auth
from src.app import activities, app


class AdminModeTests(unittest.TestCase):
    def setUp(self):
        self.original_activities = copy.deepcopy(activities)
        self.original_credentials_file = auth.CREDENTIALS_FILE
        self.temporary_directory = tempfile.TemporaryDirectory()
        auth.CREDENTIALS_FILE = Path(self.temporary_directory.name) / "teachers.json"
        auth.add_teacher("coach", "correct horse battery staple")
        with auth._sessions_lock:
            auth._sessions.clear()
        self.client = TestClient(app)

    def tearDown(self):
        self.client.close()
        activities.clear()
        activities.update(self.original_activities)
        auth.CREDENTIALS_FILE = self.original_credentials_file
        with auth._sessions_lock:
            auth._sessions.clear()
        self.temporary_directory.cleanup()

    def test_activity_list_remains_public(self):
        response = self.client.get("/activities")

        self.assertEqual(response.status_code, 200)
        self.assertIn("Chess Club", response.json())

    def test_signup_and_unregister_require_teacher_session(self):
        signup = self.client.post(
            "/activities/Chess%20Club/signup", params={"email": "student@mergington.edu"}
        )
        unregister = self.client.delete(
            "/activities/Chess%20Club/unregister",
            params={"email": "michael@mergington.edu"},
        )

        self.assertEqual(signup.status_code, 401)
        self.assertEqual(unregister.status_code, 401)

    def test_teacher_can_log_in_register_unregister_and_log_out(self):
        login = self.client.post(
            "/auth/login",
            json={"username": "coach", "password": "correct horse battery staple"},
        )

        self.assertEqual(login.status_code, 200)
        self.assertEqual(login.json(), {"username": "coach"})
        self.assertIn("httponly", login.headers["set-cookie"].lower())

        current_teacher = self.client.get("/auth/me")
        signup = self.client.post(
            "/activities/Chess%20Club/signup", params={"email": "student@mergington.edu"}
        )
        unregister = self.client.delete(
            "/activities/Chess%20Club/unregister",
            params={"email": "student@mergington.edu"},
        )
        logout = self.client.post("/auth/logout")

        self.assertEqual(current_teacher.json(), {"username": "coach"})
        self.assertEqual(signup.status_code, 200)
        self.assertEqual(unregister.status_code, 200)
        self.assertEqual(logout.status_code, 200)
        self.assertEqual(self.client.get("/auth/me").status_code, 401)

    def test_invalid_password_is_rejected(self):
        response = self.client.post(
            "/auth/login", json={"username": "coach", "password": "wrong password"}
        )

        self.assertEqual(response.status_code, 401)

    def test_missing_credential_file_fails_closed(self):
        auth.CREDENTIALS_FILE = Path(self.temporary_directory.name) / "missing.json"

        response = self.client.post(
            "/auth/login", json={"username": "coach", "password": "anything"}
        )

        self.assertEqual(response.status_code, 503)


if __name__ == "__main__":
    unittest.main()