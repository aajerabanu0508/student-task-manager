import os
import tempfile
import unittest
from pathlib import Path

# Set DATA_DIR before importing app so tests use a temporary database.
_tmpdir = tempfile.TemporaryDirectory()
os.environ["DATA_DIR"] = _tmpdir.name
os.environ["SECRET_KEY"] = "test-secret"
from app import app  # noqa: E402

class TaskManagerTests(unittest.TestCase):
    def setUp(self):
        app.config["TESTING"] = True
        self.client = app.test_client()
        db_path = Path(_tmpdir.name) / "tasks.db"
        if db_path.exists():
            db_path.unlink()
        from app import initialize_db
        initialize_db()

    def test_homepage_loads(self):
        response = self.client.get("/")
        self.assertEqual(response.status_code, 200)
        self.assertIn(b"Student Task Manager", response.data)

    def test_add_task(self):
        response = self.client.post("/tasks", data={"title": "Learn Docker"}, follow_redirects=True)
        self.assertEqual(response.status_code, 200)
        self.assertIn(b"Learn Docker", response.data)

    def test_blank_task_is_rejected(self):
        response = self.client.post("/tasks", data={"title": "   "}, follow_redirects=True)
        self.assertEqual(response.status_code, 200)
        self.assertIn(b"Please enter a task", response.data)

    def test_health_endpoint(self):
        response = self.client.get("/health")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json, {"status": "ok"})

if __name__ == "__main__":
    unittest.main()
