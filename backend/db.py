import sqlite3
from pathlib import Path

DB_PATH = Path(__file__).resolve().parent / "gradebook.db"


def get_connection() -> sqlite3.Connection:
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON;")
    return conn


def init_db() -> None:
    with get_connection() as conn:
        conn.executescript(
            """
            CREATE TABLE IF NOT EXISTS students (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                full_name TEXT NOT NULL,
                reg_no TEXT NOT NULL UNIQUE,
                class_name TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS attendance (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                student_id INTEGER NOT NULL,
                session_date TEXT NOT NULL,
                status TEXT NOT NULL CHECK (status IN ('present', 'absent', 'late')),
                FOREIGN KEY (student_id) REFERENCES students (id) ON DELETE CASCADE,
                UNIQUE (student_id, session_date)
            );

            CREATE TABLE IF NOT EXISTS scores (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                student_id INTEGER NOT NULL,
                assessment_title TEXT NOT NULL,
                score REAL NOT NULL CHECK (score >= 0),
                max_score REAL NOT NULL CHECK (max_score > 0),
                recorded_at TEXT DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (student_id) REFERENCES students (id) ON DELETE CASCADE
            );
            """
        )

        count = conn.execute("SELECT COUNT(*) AS count FROM students").fetchone()["count"]
        if count == 0:
            conn.executemany(
                "INSERT INTO students (full_name, reg_no, class_name) VALUES (?, ?, ?)",
                [
                    ("Amina Yusuf", "STU-001", "JSS 1A"),
                    ("Zainab Musa", "STU-002", "JSS 1A"),
                    ("Ibrahim Sani", "STU-003", "JSS 1B"),
                ],
            )