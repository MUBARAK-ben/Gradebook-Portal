from contextlib import asynccontextmanager
from pathlib import Path
import sys
from typing import Optional

BACKEND_DIR = str(Path(__file__).resolve().parent)
if BACKEND_DIR not in sys.path:
    sys.path.insert(0, BACKEND_DIR)

from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import PlainTextResponse
from pydantic import BaseModel
from db import init_db
from gradebook import (
    add_student,
    delete_score,
    delete_student,
    generate_csv_text,
    get_class_summary,
    list_classes,
    list_scores,
    list_students,
    mark_attendance,
    record_score,
)

@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()
    yield


app = FastAPI(title="Classroom Gradebook & Attendance API", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://127.0.0.1:5500",
        "http://localhost:5500",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


class StudentCreate(BaseModel):
    full_name: str
    reg_no: str
    class_name: str


class AttendanceCreate(BaseModel):
    reg_no: str
    status: str
    session_date: Optional[str] = None


class ScoreCreate(BaseModel):
    reg_no: str
    assessment_title: str
    score: float
    max_score: float


@app.get("/api/health")
def health():
    return {"status": "ok"}


@app.get("/api/classes")
def api_list_classes():
    return list_classes()


@app.get("/api/students")
def api_list_students(class_name: Optional[str] = Query(default=None)):
    return list_students(class_name)


@app.post("/api/students", status_code=201)
def api_add_student(payload: StudentCreate):
    try:
        return add_student(payload.full_name, payload.reg_no, payload.class_name)
    except ValueError as err:
        raise HTTPException(status_code=400, detail=str(err)) from err


@app.delete("/api/students/{student_id}")
def api_delete_student(student_id: int):
    if not delete_student(student_id):
        raise HTTPException(status_code=404, detail="Student not found.")
    return {"deleted": True}


@app.post("/api/attendance", status_code=201)
def api_mark_attendance(payload: AttendanceCreate):
    try:
        return mark_attendance(payload.reg_no, payload.status, payload.session_date)
    except ValueError as err:
        raise HTTPException(status_code=400, detail=str(err)) from err
    except LookupError as err:
        raise HTTPException(status_code=404, detail=str(err)) from err


@app.get("/api/scores")
def api_list_scores(class_name: Optional[str] = Query(default=None)):
    return list_scores(class_name)


@app.post("/api/scores", status_code=201)
def api_record_score(payload: ScoreCreate):
    try:
        return record_score(
            payload.reg_no, payload.assessment_title, payload.score, payload.max_score
        )
    except ValueError as err:
        raise HTTPException(status_code=400, detail=str(err)) from err
    except LookupError as err:
        raise HTTPException(status_code=404, detail=str(err)) from err


@app.delete("/api/scores/{score_id}")
def api_delete_score(score_id: int):
    if not delete_score(score_id):
        raise HTTPException(status_code=404, detail="Score record not found.")
    return {"deleted": True}


@app.get("/api/summary")
def api_summary(class_name: Optional[str] = Query(default=None)):
    return get_class_summary(class_name)


@app.get("/api/export.csv")
def api_export_csv(class_name: Optional[str] = Query(default=None)):
    csv_text = generate_csv_text(class_name)
    return PlainTextResponse(
        content=csv_text,
        media_type="text/csv",
        headers={"Content-Disposition": "attachment; filename=gradebook_report.csv"},
    )