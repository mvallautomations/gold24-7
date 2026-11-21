import os
import sqlite3

DB_PATH = os.getenv("BUDDY_DB", "/data/buddy.sqlite3")

def connect():
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
    return sqlite3.connect(DB_PATH)

def init_db():
    with connect() as db:
        db.execute("CREATE TABLE IF NOT EXISTS completed_lessons (lesson_id INTEGER PRIMARY KEY)")
        db.execute("CREATE TABLE IF NOT EXISTS quiz_points (id INTEGER PRIMARY KEY AUTOINCREMENT, points INTEGER NOT NULL)")

def get_progress():
    with connect() as db:
        completed = [row[0] for row in db.execute("SELECT lesson_id FROM completed_lessons")]
        points = db.execute("SELECT COALESCE(SUM(points), 0) FROM quiz_points").fetchone()[0]
    return {"completed": completed, "points": points}

def save_lesson(lesson_id):
    with connect() as db:
        db.execute("INSERT OR IGNORE INTO completed_lessons (lesson_id) VALUES (?)", (lesson_id,))

def save_quiz(points):
    with connect() as db:
        db.execute("INSERT INTO quiz_points (points) VALUES (?)", (points,))
