import csv
import io
import sqlite3
from datetime import date
from typing import Optional
from db import get_connection


def letter_grade(percentage: float) -> str:
    if percentage >= 70:
        return "A"
    if percentage >= 60:
        return "B"
    if percentage >= 50:
        return "C"
    if percentage >= 45:
        return "D"
    return "F"


def list_classes() -> list[str]:
    with get_connection() as conn:
        rows = conn.execute(
            "SELECT DISTINCT class_name FROM students ORDER BY class_name ASC"
        ).fetchall()
    return [row["class_name"] for row in rows]


def list_students(class_filter: Optional[str] = None) -> list[dict]:
    with get_connection() as conn:
        if class_filter and class_filter.strip():
            rows = conn.execute(
                """
                SELECT id, full_name, reg_no, class_name
                FROM students
                WHERE LOWER(class_name) = LOWER(?)
                ORDER BY full_name ASC
                """,
                (class_filter.strip(),),
            ).fetchall()
        else:
            rows = conn.execute(
                "SELECT id, full_name, reg_no, class_name FROM students ORDER BY full_name ASC"
            ).fetchall()
    return [dict(row) for row in rows]


def add_student(full_name: str, reg_no: str, class_name: str) -> dict:
    full_name = full_name.strip()
    reg_no = reg_no.strip().upper()
    class_name = class_name.strip()

    if not full_name or not reg_no or not class_name:
        raise ValueError("Full name, registration number, and class name are required.")

    try:
        with get_connection() as conn:
            cursor = conn.execute(
                "INSERT INTO students (full_name, reg_no, class_name) VALUES (?, ?, ?)",
                (full_name, reg_no, class_name),
            )
            student_id = cursor.lastrowid
        return {
            "id": student_id,
            "full_name": full_name,
            "reg_no": reg_no,
            "class_name": class_name,
        }
    except sqlite3.IntegrityError as exc:
        raise ValueError(f"Registration number '{reg_no}' already exists.") from exc


def delete_student(student_id: int) -> bool:
    with get_connection() as conn:
        cursor = conn.execute("DELETE FROM students WHERE id = ?", (student_id,))
    return cursor.rowcount > 0


def mark_attendance(
    reg_no: str, status: str, session_date: Optional[str] = None
) -> dict:
    status = status.strip().lower()
    if status not in {"present", "absent", "late"}:
        raise ValueError("Status must be 'present', 'absent', or 'late'.")

    target_date = (session_date or date.today().isoformat()).strip()
    reg_no = reg_no.strip().upper()

    with get_connection() as conn:
        student = conn.execute(
            "SELECT id, full_name, reg_no FROM students WHERE reg_no = ?", (reg_no,)
        ).fetchone()
        if not student:
            raise LookupError(f"Student '{reg_no}' not found.")

        conn.execute(
            """
            INSERT INTO attendance (student_id, session_date, status)
            VALUES (?, ?, ?)
            ON CONFLICT(student_id, session_date)
            DO UPDATE SET status = excluded.status
            """,
            (student["id"], target_date, status),
        )

    return {
        "reg_no": student["reg_no"],
        "full_name": student["full_name"],
        "session_date": target_date,
        "status": status,
    }


def record_score(
    reg_no: str, assessment_title: str, score: float, max_score: float
) -> dict:
    assessment_title = assessment_title.strip()
    reg_no = reg_no.strip().upper()

    if not assessment_title:
        raise ValueError("Assessment title is required.")
    if max_score <= 0:
        raise ValueError("Maximum score must be greater than zero.")
    if score < 0 or score > max_score:
        raise ValueError(f"Score must be between 0 and {max_score}.")

    with get_connection() as conn:
        student = conn.execute(
            "SELECT id, full_name, reg_no FROM students WHERE reg_no = ?", (reg_no,)
        ).fetchone()
        if not student:
            raise LookupError(f"Student '{reg_no}' not found.")

        cursor = conn.execute(
            """
            INSERT INTO scores (student_id, assessment_title, score, max_score)
            VALUES (?, ?, ?, ?)
            """,
            (student["id"], assessment_title, score, max_score),
        )
        score_id = cursor.lastrowid

    return {
        "id": score_id,
        "reg_no": student["reg_no"],
        "full_name": student["full_name"],
        "assessment_title": assessment_title,
        "score": score,
        "max_score": max_score,
    }


def list_scores(class_filter: Optional[str] = None) -> list[dict]:
    with get_connection() as conn:
        if class_filter and class_filter.strip():
            rows = conn.execute(
                """
                SELECT sc.id, st.reg_no, st.full_name, st.class_name,
                       sc.assessment_title, sc.score, sc.max_score, sc.recorded_at
                FROM scores sc
                JOIN students st ON st.id = sc.student_id
                WHERE LOWER(st.class_name) = LOWER(?)
                ORDER BY sc.id DESC
                """,
                (class_filter.strip(),),
            ).fetchall()
        else:
            rows = conn.execute(
                """
                SELECT sc.id, st.reg_no, st.full_name, st.class_name,
                       sc.assessment_title, sc.score, sc.max_score, sc.recorded_at
                FROM scores sc
                JOIN students st ON st.id = sc.student_id
                ORDER BY sc.id DESC
                """
            ).fetchall()
    return [dict(row) for row in rows]


def delete_score(score_id: int) -> bool:
    with get_connection() as conn:
        cursor = conn.execute("DELETE FROM scores WHERE id = ?", (score_id,))
    return cursor.rowcount > 0


def get_class_summary(class_filter: Optional[str] = None) -> list[dict]:
    students = list_students(class_filter)
    summary = []

    with get_connection() as conn:
        for s in students:
            att_rows = conn.execute(
                "SELECT status FROM attendance WHERE student_id = ?", (s["id"],)
            ).fetchall()
            total_sessions = len(att_rows)
            attended = sum(1 for r in att_rows if r["status"] in ("present", "late"))
            attendance_pct = (attended / total_sessions * 100) if total_sessions > 0 else 0.0

            score_rows = conn.execute(
                "SELECT score, max_score FROM scores WHERE student_id = ?", (s["id"],)
            ).fetchall()
            if score_rows:
                pcts = [(r["score"] / r["max_score"]) * 100 for r in score_rows]
                avg_pct = sum(pcts) / len(pcts)
                grade = letter_grade(avg_pct)
            else:
                avg_pct = 0.0
                grade = "N/A"

            summary.append(
                {
                    "id": s["id"],
                    "reg_no": s["reg_no"],
                    "full_name": s["full_name"],
                    "class_name": s["class_name"],
                    "assessments": len(score_rows),
                    "avg_percentage": round(avg_pct, 1),
                    "grade": grade,
                    "attendance_pct": round(attendance_pct, 1),
                    "sessions": total_sessions,
                }
            )

    summary.sort(key=lambda item: (item["grade"] == "N/A", -item["avg_percentage"]))
    return summary


def generate_csv_text(class_filter: Optional[str] = None) -> str:
    rows = get_class_summary(class_filter)
    output = io.StringIO()
    fieldnames = [
        "reg_no",
        "full_name",
        "class_name",
        "assessments",
        "avg_percentage",
        "grade",
        "attendance_pct",
        "sessions",
    ]
    writer = csv.DictWriter(output, fieldnames=fieldnames, extrasaction="ignore")
    writer.writeheader()
    writer.writerows(rows)
    return output.getvalue()