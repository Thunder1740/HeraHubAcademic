from __future__ import annotations

import json
import math
from collections import Counter, defaultdict
from datetime import datetime, timezone
from typing import Any

from sqlalchemy import delete, func, select
from sqlalchemy.orm import Session, selectinload

from .models import (
    CourseAttempt,
    CourseRecord,
    CurriculumMatrix,
    EnrollmentIntent,
    ImportLog,
    MatrixSubject,
    PlannedClass,
    Prerequisite,
    Setting,
    Student,
)
from .parser import normalize_name


PLANNING_STATUSES = {"Ativo", "Formando"}


def settings_dict(db: Session) -> dict[str, str]:
    return {item.key: item.value for item in db.scalars(select(Setting)).all()}


def matrix_subject_map(db: Session, matrix_id: int) -> dict[str, MatrixSubject]:
    subjects = db.scalars(select(MatrixSubject).where(MatrixSubject.matrix_id == matrix_id)).all()
    return {item.normalized_name: item for item in subjects}


def enrich_review(db: Session, parsed: dict[str, Any], matrix_id: int | None) -> dict[str, Any]:
    matrix = db.get(CurriculumMatrix, matrix_id) if matrix_id else db.scalar(select(CurriculumMatrix).where(CurriculumMatrix.active.is_(True)))
    subject_map = matrix_subject_map(db, matrix.id) if matrix else {}
    unmatched = 0
    filled = 0
    for item in parsed["records"]:
        subject = subject_map.get(item["normalized_name"])
        item["subject_id"] = subject.id if subject else None
        item["matrix_code"] = subject.code if subject else None
        item["category"] = subject.category if subject else ("Estágio" if item["subject_name"].startswith("ESTÁGIO:") else "Regular")
        if subject and item["hours"] is None:
            item["hours"] = subject.hours
            item["hours_source"] = "Matriz curricular"
            filled += 1
        if not subject:
            unmatched += 1
    parsed["matrix_id"] = matrix.id if matrix else None
    parsed["matrix_name"] = matrix.name if matrix else None
    parsed["summary"]["unmatched"] = unmatched
    parsed["summary"]["hours_filled_from_matrix"] = filled
    parsed["warnings"].extend([f"{unmatched} disciplina(s) sem correspondência com a matriz"] if unmatched else [])
    return parsed


def save_import(db: Session, payload: dict[str, Any], filename: str) -> tuple[Student, bool]:
    parsed_student = payload["student"]
    registration = str(parsed_student.get("registration") or "").strip()
    if not registration:
        raise ValueError("A matrícula é obrigatória antes da confirmação")
    matrix_id = payload.get("matrix_id")
    subject_map = matrix_subject_map(db, matrix_id) if matrix_id else {}
    existing_log = db.scalar(select(ImportLog).where(ImportLog.file_hash == payload["file_hash"]))
    if existing_log:
        student = db.scalar(select(Student).where(Student.registration == registration))
        if student:
            return student, True

    student = db.scalar(select(Student).where(Student.registration == registration))
    if student is None:
        student = Student(registration=registration, name=parsed_student.get("name") or "Nome não informado")
        db.add(student)
        db.flush()
    student.name = parsed_student.get("name") or student.name
    student.course = parsed_student.get("course") or "Farmácia"
    student.matrix_id = matrix_id
    student.required_hours = int(parsed_student.get("required_hours") or 0)
    student.completed_hours = int(parsed_student.get("completed_hours") or 0)
    student.complementary_required = int(parsed_student.get("complementary_required") or 0)
    student.complementary_completed = int(parsed_student.get("complementary_completed") or 0)
    student.ira = parsed_student.get("ira")
    student.current_semester = parsed_student.get("current_semester") or max(
        (int(r.get("semester") or 0) for r in payload.get("records", []) if r.get("status") == "Em Curso"),
        default=None,
    )
    student.semester_source = parsed_student.get("semester_source") or "Inferido"
    student.academic_status = parsed_student.get("academic_status") or student.academic_status
    student.expected_graduation = parsed_student.get("expected_graduation")
    student.graduation_source = parsed_student.get("graduation_source") or "Não disponível"
    student.preferred_shift = parsed_student.get("preferred_shift") or student.preferred_shift
    student.updated_at = datetime.now(timezone.utc).replace(tzinfo=None)
    db.flush()

    db.execute(delete(CourseRecord).where(CourseRecord.student_id == student.id))
    db.execute(delete(CourseAttempt).where(CourseAttempt.student_id == student.id))
    for item in payload.get("attempts", []):
        db.add(
            CourseAttempt(
                student_id=student.id,
                subject_name=item["subject_name"],
                status=item["status"],
                grade=item.get("grade"),
                academic_period=item.get("academic_period"),
                attendance=item.get("attendance"),
                hours=item.get("hours"),
            )
        )
    for item in payload.get("records", []):
        subject = subject_map.get(item.get("normalized_name") or normalize_name(item["subject_name"]))
        hours = item.get("hours")
        hours_source = item.get("hours_source") or "Não disponível"
        if subject and hours is None:
            hours, hours_source = subject.hours, "Matriz curricular"
        db.add(
            CourseRecord(
                student_id=student.id,
                subject_id=subject.id if subject else item.get("subject_id"),
                subject_name=item["subject_name"],
                normalized_name=item.get("normalized_name") or normalize_name(item["subject_name"]),
                semester=int(item.get("semester") or 0),
                status=item["status"],
                grade=item.get("grade"),
                attendance=item.get("attendance"),
                academic_period=item.get("academic_period"),
                hours=hours,
                hours_source=hours_source,
                elective_choice=item.get("elective_choice"),
                is_stage=(subject.category == "Estágio") if subject else item["subject_name"].startswith("ESTÁGIO:"),
                confidence=float(item.get("confidence") or 1.0),
            )
        )
    if existing_log:
        existing_log.file_name = filename
        existing_log.registration = registration
        existing_log.status = "Confirmado"
        existing_log.warnings_json = json.dumps(payload.get("warnings", []), ensure_ascii=False)
    else:
        db.add(
            ImportLog(
                file_name=filename,
                file_hash=payload["file_hash"],
                registration=registration,
                status="Confirmado",
                warnings_json=json.dumps(payload.get("warnings", []), ensure_ascii=False),
            )
        )
    db.commit()
    db.refresh(student)
    return student, False


def student_summary(student: Student) -> dict[str, Any]:
    counts = Counter(item.status for item in student.records)
    stage_pending = sum(1 for item in student.records if item.is_stage and item.status == "A Cursar")
    progress = round((student.completed_hours / student.required_hours * 100), 1) if student.required_hours else 0
    return {
        "id": student.id,
        "registration": student.registration,
        "name": student.name,
        "course": student.course,
        "matrix_id": student.matrix_id,
        "matrix_name": student.matrix.name if student.matrix else None,
        "current_semester": student.current_semester,
        "semester_source": student.semester_source,
        "academic_status": student.academic_status,
        "expected_graduation": student.expected_graduation,
        "graduation_source": student.graduation_source,
        "preferred_shift": student.preferred_shift,
        "required_hours": student.required_hours,
        "completed_hours": student.completed_hours,
        "pending_hours": max(0, student.required_hours - student.completed_hours),
        "progress": progress,
        "complementary_required": student.complementary_required,
        "complementary_completed": student.complementary_completed,
        "ira": student.ira,
        "counts": dict(counts),
        "stage_pending": stage_pending,
        "updated_at": student.updated_at.isoformat() if student.updated_at else None,
    }


def load_student(db: Session, student_id: int) -> Student | None:
    return db.scalar(
        select(Student)
        .options(selectinload(Student.matrix), selectinload(Student.records), selectinload(Student.attempts), selectinload(Student.intents))
        .where(Student.id == student_id)
    )


def student_detail(db: Session, student_id: int) -> dict[str, Any] | None:
    student = load_student(db, student_id)
    if not student:
        return None
    data = student_summary(student)
    intent_subjects = {item.subject_id for item in student.intents if item.intends}
    data["records"] = [
        {
            "id": item.id,
            "subject_id": item.subject_id,
            "code": item.subject.code if item.subject else None,
            "semester": item.semester,
            "subject_name": item.subject_name,
            "display_name": f"{item.subject_name} — {item.elective_choice}" if item.elective_choice else item.subject_name,
            "status": item.status,
            "grade": item.grade,
            "attendance": item.attendance,
            "academic_period": item.academic_period,
            "hours": item.hours,
            "hours_source": item.hours_source,
            "category": item.subject.category if item.subject else ("Estágio" if item.is_stage else "Regular"),
            "intent": item.subject_id in intent_subjects,
        }
        for item in sorted(student.records, key=lambda x: (x.semester, x.subject_name))
    ]
    data["attempts"] = [
        {
            "subject_name": item.subject_name,
            "status": item.status,
            "grade": item.grade,
            "academic_period": item.academic_period,
        }
        for item in student.attempts
        if item.status.startswith("Reprovado")
    ]
    return data


def eligibility(db: Session, student_id: int, subject_id: int, completed: set[int], in_course: set[int]) -> tuple[str, list[int]]:
    required = list(db.scalars(select(Prerequisite.required_subject_id).where(Prerequisite.subject_id == subject_id)).all())
    if not required:
        return "Indeterminada", []
    missing = [item for item in required if item not in completed and item not in in_course]
    if missing:
        return "Não apto", missing
    if any(item in in_course for item in required):
        return "Potencialmente apto", []
    return "Apto", []


def demand_rows(db: Session) -> list[dict[str, Any]]:
    students = db.scalars(
        select(Student)
        .options(selectinload(Student.records), selectinload(Student.intents))
        .where(Student.academic_status.in_(PLANNING_STATUSES))
    ).all()
    subjects = {item.id: item for item in db.scalars(select(MatrixSubject).where(MatrixSubject.active.is_(True))).all()}
    settings = settings_dict(db)
    default_capacity = int(settings.get("default_capacity", "30"))
    stage_capacity = int(settings.get("stage_capacity", "20"))
    buckets: dict[int, dict[str, Any]] = {}
    for student in students:
        completed = {r.subject_id for r in student.records if r.subject_id and r.status in {"Aprovado", "Dispensado"}}
        in_course = {r.subject_id for r in student.records if r.subject_id and r.status == "Em Curso"}
        intended = {i.subject_id for i in student.intents if i.intends}
        for record in student.records:
            if record.status != "A Cursar" or not record.subject_id or record.subject_id not in subjects:
                continue
            subject = subjects[record.subject_id]
            if subject.category == "Atividade complementar":
                continue
            row = buckets.setdefault(
                subject.id,
                {
                    "subject_id": subject.id,
                    "code": subject.code,
                    "name": subject.name,
                    "matrix_id": subject.matrix_id,
                    "semester": subject.semester,
                    "hours": subject.hours,
                    "category": subject.category,
                    "total": 0,
                    "eligible": 0,
                    "potential": 0,
                    "not_eligible": 0,
                    "indeterminate": 0,
                    "interested": 0,
                    "graduating": 0,
                    "students": [],
                },
            )
            status, missing = eligibility(db, student.id, subject.id, completed, in_course)
            row["total"] += 1
            if status == "Apto":
                row["eligible"] += 1
            elif status == "Potencialmente apto":
                row["potential"] += 1
            elif status == "Não apto":
                row["not_eligible"] += 1
            else:
                row["indeterminate"] += 1
            if subject.id in intended:
                row["interested"] += 1
            if student.academic_status == "Formando":
                row["graduating"] += 1
            row["students"].append(
                {
                    "id": student.id,
                    "name": student.name,
                    "registration": student.registration,
                    "academic_status": student.academic_status,
                    "current_semester": student.current_semester,
                    "expected_graduation": student.expected_graduation,
                    "preferred_shift": student.preferred_shift,
                    "eligibility": status,
                    "missing_prerequisite_ids": missing,
                    "interested": subject.id in intended,
                }
            )
    for row in buckets.values():
        capacity = stage_capacity if row["category"] == "Estágio" else default_capacity
        row["capacity"] = capacity
        row["estimated_classes"] = math.ceil(row["total"] / capacity) if row["total"] else 0
        row["priority"] = "Crítica — formandos" if row["graduating"] else ("Alta demanda" if row["total"] >= capacity else "Demanda regular")
    return sorted(buckets.values(), key=lambda x: (x["graduating"], x["total"], x["interested"]), reverse=True)


def dashboard(db: Session) -> dict[str, Any]:
    students = db.scalars(select(Student).options(selectinload(Student.records), selectinload(Student.matrix))).all()
    demand = demand_rows(db)
    active = [s for s in students if s.academic_status in PLANNING_STATUSES]
    last_import = db.scalar(select(func.max(ImportLog.created_at)))
    semesters = Counter(str(s.current_semester or "Não informado") for s in active)
    matrices = Counter(s.matrix.name if s.matrix else "Não vinculada" for s in active)
    total_pending = sum(1 for s in active for r in s.records if r.status == "A Cursar")
    stage_pending = sum(1 for s in active for r in s.records if r.status == "A Cursar" and r.is_stage)
    return {
        "students": len(students),
        "active": len(active),
        "graduating": sum(s.academic_status == "Formando" for s in active),
        "matrices": db.scalar(select(func.count(CurriculumMatrix.id))) or 0,
        "pending": total_pending,
        "stage_pending": stage_pending,
        "awaiting_review": db.scalar(select(func.count(ImportLog.id)).where(ImportLog.status == "Revisão")) or 0,
        "unconfigured_prerequisites": sum(1 for d in demand if d["indeterminate"] > 0),
        "last_import": last_import.isoformat() if last_import else None,
        "integralization_average": round(sum((s.completed_hours / s.required_hours * 100) if s.required_hours else 0 for s in active) / len(active), 1) if active else 0,
        "semester_distribution": dict(semesters),
        "matrix_distribution": dict(matrices),
        "demand": demand[:8],
    }


def simulate(db: Session, subject_ids: list[int]) -> dict[str, Any]:
    rows = [row for row in demand_rows(db) if row["subject_id"] in set(subject_ids)]
    unique_students = {student["id"] for row in rows for student in row["students"]}
    graduating_students = {student["id"] for row in rows for student in row["students"] if student["academic_status"] == "Formando"}
    all_demands = sum(row["total"] for row in demand_rows(db))
    met = sum(row["total"] for row in rows)
    return {
        "selected_subjects": len(rows),
        "unique_students": len(unique_students),
        "curricular_needs": met,
        "graduating_students": len(graduating_students),
        "eligible": sum(row["eligible"] for row in rows),
        "potential": sum(row["potential"] for row in rows),
        "stages": sum(row["category"] == "Estágio" for row in rows),
        "classes": sum(row["estimated_classes"] for row in rows),
        "unmet_needs": max(0, all_demands - met),
        "occupancy": round(met / sum(row["estimated_classes"] * row["capacity"] for row in rows) * 100, 1) if rows else 0,
        "rows": rows,
        "method": "Prioridade lexicográfica: formandos, estudantes únicos, necessidades e ocupação. Elegibilidade sem pré-requisitos cadastrados permanece indeterminada.",
    }


def conflicts(db: Session) -> list[dict[str, Any]]:
    classes = db.scalars(select(PlannedClass)).all()
    demand = {row["subject_id"]: {s["id"] for s in row["students"]} for row in demand_rows(db)}
    issues: list[dict[str, Any]] = []
    for index, first in enumerate(classes):
        for second in classes[index + 1 :]:
            if first.planning_period != second.planning_period or first.weekday != second.weekday:
                continue
            if not first.start_time or not first.end_time or not second.start_time or not second.end_time:
                continue
            overlaps = first.start_time < second.end_time and second.start_time < first.end_time
            if not overlaps:
                continue
            shared = len(demand.get(first.subject_id, set()) & demand.get(second.subject_id, set()))
            reasons = []
            if shared:
                reasons.append(f"{shared} estudante(s) em comum")
            if first.professor and first.professor == second.professor:
                reasons.append("mesmo professor")
            if first.room and first.room == second.room:
                reasons.append("mesma sala")
            if reasons:
                issues.append({"class_a": first.id, "class_b": second.id, "reasons": reasons, "shared_students": shared})
    return issues
