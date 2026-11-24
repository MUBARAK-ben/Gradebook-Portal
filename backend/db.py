import os
import sqlite3
from contextlib import contextmanager
from pathlib import Path
import psycopg
from psycopg.rows import dict_row

DB_PATH = Path(__file__).resolve().parent / "gradebook.db"
DATABASE_URL = os.getenv("DATABASE_URL", "").strip()

if DATABASE_URL.startswith("postgres://"):
    DATABASE_URL = DATABASE_URL.replace("postgres://", "postgresql://", 1)

USE_POSTGRES = DATABASE_URL.startswith("postgresql://")


@contextmanager
def get_connection():
    if USE_POSTGRES:
        conn = psycopg.connect(DATABASE_URL, row_factory=dict_row)
        try:
            yield conn
            conn.commit()
        except Exception:
            conn.rollback()
            raise
        finally:
            conn.close()
    else:
        conn = sqlite3.connect(DB_PATH)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA foreign_keys = ON;")
        try:
            yield conn
            conn.commit()
        except Exception:
            conn.rollback()
            raise
        finally:
            conn.close()


def init_db() -> None:
    if USE_POSTGRES:
        statements = [
            """
            CREATE TABLE IF NOT EXISTS students (
                id SERIAL PRIMARY KEY,
                full_name TEXT NOT NULL,
                reg_no TEXT NOT NULL UNIQUE,
                class_name TEXT NOT NULL
            );
            """,
            """
            CREATE TABLE IF NOT EXISTS attendance (
                id SERIAL PRIMARY KEY,
                student_id INTEGER NOT NULL,
                session_date TEXT NOT NULL,
                status TEXT NOT NULL CHECK (status IN ('present', 'absent', 'late')),
                FOREIGN KEY (student_id) REFERENCES students (id) ON DELETE CASCADE,
                UNIQUE (student_id, session_date)
            );
            """,
            """
            CREATE TABLE IF NOT EXISTS scores (
                id SERIAL PRIMARY KEY,
                student_id INTEGER NOT NULL,
                assessment_title TEXT NOT NULL,
                score_value DOUBLE PRECISION NOT NULL,
                max_score DOUBLE PRECISION NOT NULL DEFAULT 100,
                FOREIGN KEY (student_id) REFERENCES students (id) ON DELETE CASCADE
            );
            """,
        ]
        with get_connection() as conn:
            with conn.cursor() as cur:
                for stmt in statements:
                    cur.execute(stmt)
    else:
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
                    score_value REAL NOT NULL,
                    max_score REAL NOT NULL DEFAULT 100,
                    FOREIGN KEY (student_id) REFERENCES students (id) ON DELETE CASCADE
                );
                """
            )