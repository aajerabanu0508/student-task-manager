import os
import sqlite3
from contextlib import contextmanager
from pathlib import Path
from flask import Flask, redirect, render_template, request, url_for, flash

app = Flask(__name__)
app.secret_key = os.environ.get("SECRET_KEY", "change-this-development-secret")
BASE_DIR = Path(__file__).resolve().parent
DATA_DIR = Path(os.environ.get("DATA_DIR", BASE_DIR / "data"))
DB_PATH = DATA_DIR / "tasks.db"

@contextmanager
def get_db():
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    connection = sqlite3.connect(DB_PATH)
    connection.row_factory = sqlite3.Row
    try:
        yield connection
        connection.commit()
    except Exception:
        connection.rollback()
        raise
    finally:
        connection.close()

def initialize_db():
    with get_db() as db:
        db.execute("""
            CREATE TABLE IF NOT EXISTS tasks (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                title TEXT NOT NULL,
                completed INTEGER NOT NULL DEFAULT 0,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)

@app.route("/")
def index():
    with get_db() as db:
        tasks = db.execute(
            "SELECT id, title, completed, created_at FROM tasks ORDER BY id DESC"
        ).fetchall()
    return render_template("index.html", tasks=tasks)

@app.post("/tasks")
def add_task():
    title = request.form.get("title", "").strip()
    if not title:
        flash("Please enter a task.", "error")
    elif len(title) > 200:
        flash("Task titles must be 200 characters or fewer.", "error")
    else:
        with get_db() as db:
            db.execute("INSERT INTO tasks (title) VALUES (?)", (title,))
        flash("Task added.", "success")
    return redirect(url_for("index"))

@app.post("/tasks/<int:task_id>/toggle")
def toggle_task(task_id):
    with get_db() as db:
        db.execute(
            "UPDATE tasks SET completed = CASE completed WHEN 0 THEN 1 ELSE 0 END WHERE id = ?",
            (task_id,),
        )
    return redirect(url_for("index"))

@app.post("/tasks/<int:task_id>/delete")
def delete_task(task_id):
    with get_db() as db:
        db.execute("DELETE FROM tasks WHERE id = ?", (task_id,))
    flash("Task deleted.", "success")
    return redirect(url_for("index"))

@app.get("/health")
def health():
    # Also verifies that the database can be opened.
    with get_db() as db:
        db.execute("SELECT 1").fetchone()
    return {"status": "ok"}, 200

initialize_db()

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
