from __future__ import annotations

import io
import json
import math
import sqlite3
import tempfile
from contextlib import asynccontextmanager, closing
from datetime import datetime
from pathlib import Path
from typing import Any

from fastapi import Depends, FastAPI, File, HTTPException, Query, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, StreamingResponse
from openpyxl import Workbook
from openpyxl.styles import Alignment, Font, PatternFill
from openpyxl.utils import get_column_letter
from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER
from reportlab.lib.pagesizes import A4, landscape
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle
from sqlalchemy import delete, select
from sqlalchemy.orm import Session, selectinload

from .database import Base, DATABASE_PATH, SessionLocal, engine, get_db
from .models import (
    CourseRecord,
    CurriculumMatrix,
    EnrollmentIntent,
    ImportLog,
    MatrixSubject,
    PlannedClass,
    Prerequisite,
    Setting,
    SimulationScenario,
    Student,
    SubjectEquivalence,
)
from .parser import normalize_name, parse_curriculum_matrix, parse_ulbra_history
from .seed import bootstrap, category_for
from .services import (
    conflicts,
    dashboard,
    demand_rows,
    enrich_review,
    load_student,
    save_import,
    settings_dict,
    simulate,
    student_detail,
    student_summary,
)


MAX_UPLOAD_BYTES = 12 * 1024 * 1024


@asynccontextmanager
async def lifespan(_app: FastAPI):
    Base.metadata.create_all(engine)
    with SessionLocal() as db:
        bootstrap(db)
    yield


app = FastAPI(title="FarmaHub Acadêmico", version="0.1.0", docs_url="/api/docs", redoc_url=None, lifespan=lifespan)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://127.0.0.1:3000", "http://localhost:5173", "http://127.0.0.1:5173"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)


def _read_pdf(file: UploadFile) -> bytes:
    if not file.filename or not file.filename.lower().endswith(".pdf"):
        raise HTTPException(415, "Envie um arquivo PDF válido")
    data = file.file.read(MAX_UPLOAD_BYTES + 1)
    if len(data) > MAX_UPLOAD_BYTES:
        raise HTTPException(413, "O PDF ultrapassa o limite de 12 MB")
    if not data.startswith(b"%PDF"):
        raise HTTPException(415, "O conteúdo enviado não é um PDF válido")
    return data


def _matrix_json(matrix: CurriculumMatrix) -> dict[str, Any]:
    return {
        "id": matrix.id,
        "name": matrix.name,
        "course": matrix.course,
        "campus": matrix.campus,
        "valid_from": matrix.valid_from,
        "valid_to": matrix.valid_to,
        "total_hours": matrix.total_hours,
        "active": matrix.active,
        "subject_count": len(matrix.subjects),
        "subjects": [
            {
                "id": s.id,
                "code": s.code,
                "name": s.name,
                "semester": s.semester,
                "hours": s.hours,
                "credits": s.credits,
                "sequence": s.sequence,
                "category": s.category,
                "active": s.active,
            }
            for s in sorted(matrix.subjects, key=lambda x: x.sequence)
        ],
    }


@app.get("/api/health")
def health() -> dict[str, str]:
    return {"status": "ok", "service": "FarmaHub Acadêmico"}


@app.get("/api/dashboard")
def get_dashboard(db: Session = Depends(get_db)):
    return dashboard(db)


@app.get("/api/settings")
def get_settings(db: Session = Depends(get_db)):
    return settings_dict(db)


@app.put("/api/settings")
def update_settings(payload: dict[str, Any], db: Session = Depends(get_db)):
    allowed = {"reference_period", "graduation_year", "default_capacity", "stage_capacity", "default_shift", "display_user", "retain_pdfs"}
    for key, value in payload.items():
        if key not in allowed:
            continue
        item = db.get(Setting, key)
        if item:
            item.value = str(value).lower() if isinstance(value, bool) else str(value)
        else:
            db.add(Setting(key=key, value=str(value)))
    db.commit()
    return settings_dict(db)


@app.get("/api/matrices")
def list_matrices(db: Session = Depends(get_db)):
    matrices = db.scalars(select(CurriculumMatrix).options(selectinload(CurriculumMatrix.subjects))).all()
    return [_matrix_json(item) for item in matrices]


@app.post("/api/matrices")
def create_matrix(payload: dict[str, Any], db: Session = Depends(get_db)):
    name = str(payload.get("name") or "").strip()
    if not name:
        raise HTTPException(422, "Informe o nome da matriz")
    if db.scalar(select(CurriculumMatrix).where(CurriculumMatrix.name == name)):
        raise HTTPException(409, "Já existe uma matriz com esse nome")
    matrix = CurriculumMatrix(
        name=name,
        course=payload.get("course") or "Farmácia",
        campus=payload.get("campus") or "ULBRA Canoas",
        valid_from=payload.get("valid_from"),
        valid_to=payload.get("valid_to"),
        total_hours=int(payload.get("total_hours") or 0),
        active=bool(payload.get("active", True)),
    )
    db.add(matrix)
    db.commit()
    db.refresh(matrix)
    return _matrix_json(matrix)


@app.post("/api/matrices/import/review")
def review_matrix_pdf(file: UploadFile = File(...)):
    try:
        return parse_curriculum_matrix(_read_pdf(file))
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(422, f"Não foi possível interpretar a matriz: {exc}") from exc


@app.post("/api/matrices/import/confirm")
def confirm_matrix_import(payload: dict[str, Any], db: Session = Depends(get_db)):
    name = str(payload.get("name") or "").strip()
    subjects = payload.get("subjects") or []
    if not name:
        raise HTTPException(422, "Informe o nome da matriz")
    if not isinstance(subjects, list) or not subjects:
        raise HTTPException(422, "Nenhum componente curricular foi informado")
    if len(subjects) > 500:
        raise HTTPException(422, "A matriz ultrapassa o limite de 500 componentes")
    if db.scalar(select(CurriculumMatrix).where(CurriculumMatrix.name == name)):
        raise HTTPException(409, "Já existe uma matriz com esse nome")
    codes: set[str] = set()
    matrix = CurriculumMatrix(
        name=name,
        course=str(payload.get("course") or "Farmácia").strip(),
        campus=str(payload.get("campus") or "ULBRA Canoas").strip(),
        valid_from=str(payload.get("valid_from") or "").strip() or None,
        total_hours=int(payload.get("total_hours") or 0),
        active=True,
    )
    db.add(matrix)
    db.flush()
    for index, item in enumerate(subjects, 1):
        code = str(item.get("code") or "").strip()
        subject_name = str(item.get("name") or "").strip()
        if not code or not subject_name:
            raise HTTPException(422, f"Componente {index}: código e nome são obrigatórios")
        if code in codes:
            raise HTTPException(422, f"Código duplicado na matriz: {code}")
        codes.add(code)
        db.add(
            MatrixSubject(
                matrix_id=matrix.id,
                code=code,
                name=subject_name,
                normalized_name=normalize_name(subject_name),
                semester=int(item.get("semester") or 0),
                hours=int(item.get("hours") or 0),
                credits=int(item.get("credits") or 0),
                sequence=int(item.get("sequence") or index),
                category=str(item.get("category") or category_for(subject_name.upper())),
            )
        )
    db.commit()
    db.refresh(matrix)
    return _matrix_json(matrix)


@app.delete("/api/matrices/{matrix_id}")
def delete_matrix(matrix_id: int, db: Session = Depends(get_db)):
    matrix = db.get(CurriculumMatrix, matrix_id)
    if not matrix:
        raise HTTPException(404, "Matriz não encontrada")
    name = matrix.name
    affected_students = len(matrix.students)
    db.delete(matrix)
    db.commit()
    return {"ok": True, "name": name, "affected_students": affected_students}


@app.post("/api/matrices/{matrix_id}/subjects")
def create_subject(matrix_id: int, payload: dict[str, Any], db: Session = Depends(get_db)):
    matrix = db.get(CurriculumMatrix, matrix_id)
    if not matrix:
        raise HTTPException(404, "Matriz não encontrada")
    code, name = str(payload.get("code") or "").strip(), str(payload.get("name") or "").strip()
    if not code or not name:
        raise HTTPException(422, "Código e nome são obrigatórios")
    subject = MatrixSubject(
        matrix_id=matrix_id,
        code=code,
        name=name,
        normalized_name=normalize_name(name),
        semester=int(payload.get("semester") or 0),
        hours=int(payload.get("hours") or 0),
        credits=int(payload.get("credits") or 0),
        sequence=int(payload.get("sequence") or 0),
        category=payload.get("category") or category_for(name.upper()),
        notes=payload.get("notes"),
    )
    db.add(subject)
    db.commit()
    db.refresh(subject)
    return {"id": subject.id, "name": subject.name, "code": subject.code}


@app.put("/api/subjects/{subject_id}")
def update_subject(subject_id: int, payload: dict[str, Any], db: Session = Depends(get_db)):
    subject = db.get(MatrixSubject, subject_id)
    if not subject:
        raise HTTPException(404, "Disciplina não encontrada")
    for field in ("code", "name", "category", "notes"):
        if field in payload:
            setattr(subject, field, payload[field])
    for field in ("semester", "hours", "credits", "sequence"):
        if field in payload:
            setattr(subject, field, int(payload[field]))
    if "active" in payload:
        subject.active = bool(payload["active"])
    subject.normalized_name = normalize_name(subject.name)
    db.commit()
    return {"ok": True}


@app.post("/api/subjects/{subject_id}/prerequisites")
def add_prerequisite(subject_id: int, payload: dict[str, Any], db: Session = Depends(get_db)):
    required_id = int(payload.get("required_subject_id") or 0)
    if subject_id == required_id:
        raise HTTPException(422, "Uma disciplina não pode ser pré-requisito de si mesma")
    if not db.get(MatrixSubject, subject_id) or not db.get(MatrixSubject, required_id):
        raise HTTPException(404, "Disciplina não encontrada")
    if db.scalar(select(Prerequisite).where(Prerequisite.subject_id == required_id, Prerequisite.required_subject_id == subject_id)):
        raise HTTPException(422, "Esta regra criaria uma dependência circular direta")
    existing = db.scalar(select(Prerequisite).where(Prerequisite.subject_id == subject_id, Prerequisite.required_subject_id == required_id))
    if not existing:
        db.add(Prerequisite(subject_id=subject_id, required_subject_id=required_id))
        db.commit()
    return {"ok": True}


@app.get("/api/subjects/{subject_id}/prerequisites")
def list_prerequisites(subject_id: int, db: Session = Depends(get_db)):
    ids = db.scalars(select(Prerequisite.required_subject_id).where(Prerequisite.subject_id == subject_id)).all()
    return [{"id": item.id, "code": item.code, "name": item.name} for item in db.scalars(select(MatrixSubject).where(MatrixSubject.id.in_(ids))).all()]


@app.delete("/api/subjects/{subject_id}/prerequisites/{required_subject_id}")
def delete_prerequisite(subject_id: int, required_subject_id: int, db: Session = Depends(get_db)):
    db.execute(delete(Prerequisite).where(Prerequisite.subject_id == subject_id, Prerequisite.required_subject_id == required_subject_id))
    db.commit()
    return {"ok": True}


@app.get("/api/equivalences")
def list_equivalences(db: Session = Depends(get_db)):
    subjects = {item.id: item for item in db.scalars(select(MatrixSubject)).all()}
    rows = db.scalars(select(SubjectEquivalence)).all()
    return [{"id": row.id, "subject_id": row.subject_id, "subject_name": subjects[row.subject_id].name, "equivalent_subject_id": row.equivalent_subject_id, "equivalent_subject_name": subjects[row.equivalent_subject_id].name, "confirmed": row.confirmed, "notes": row.notes} for row in rows if row.subject_id in subjects and row.equivalent_subject_id in subjects]


@app.post("/api/equivalences")
def create_equivalence(payload: dict[str, Any], db: Session = Depends(get_db)):
    subject_id = int(payload.get("subject_id") or 0)
    equivalent_id = int(payload.get("equivalent_subject_id") or 0)
    if not subject_id or not equivalent_id or subject_id == equivalent_id:
        raise HTTPException(422, "Selecione duas disciplinas diferentes")
    if not db.get(MatrixSubject, subject_id) or not db.get(MatrixSubject, equivalent_id):
        raise HTTPException(404, "Disciplina não encontrada")
    pair = sorted([subject_id, equivalent_id])
    existing = db.scalar(select(SubjectEquivalence).where(SubjectEquivalence.subject_id == pair[0], SubjectEquivalence.equivalent_subject_id == pair[1]))
    if not existing:
        db.add(SubjectEquivalence(subject_id=pair[0], equivalent_subject_id=pair[1], confirmed=bool(payload.get("confirmed", True)), notes=payload.get("notes")))
        db.commit()
    return {"ok": True}


@app.delete("/api/equivalences/{equivalence_id}")
def delete_equivalence(equivalence_id: int, db: Session = Depends(get_db)):
    row = db.get(SubjectEquivalence, equivalence_id)
    if not row:
        raise HTTPException(404, "Equivalência não encontrada")
    db.delete(row)
    db.commit()
    return {"ok": True}


@app.post("/api/imports/review")
def review_imports(
    files: list[UploadFile] = File(...),
    matrix_id: int | None = Query(default=None),
    reference_period: str | None = Query(default=None),
    db: Session = Depends(get_db),
):
    if len(files) > 300:
        raise HTTPException(413, "O lote pode conter no máximo 300 arquivos")
    settings = settings_dict(db)
    period = reference_period or settings.get("reference_period")
    results = []
    for file in files:
        try:
            data = _read_pdf(file)
            parsed = parse_ulbra_history(data, period)
            parsed = enrich_review(db, parsed, matrix_id)
            parsed["file_name"] = Path(file.filename or "historico.pdf").name
            parsed["duplicate_file"] = db.scalar(select(ImportLog.id).where(ImportLog.file_hash == parsed["file_hash"])) is not None
            results.append({"ok": True, "data": parsed})
        except HTTPException as exc:
            results.append({"ok": False, "file_name": Path(file.filename or "arquivo").name, "error": exc.detail})
        except Exception as exc:
            results.append({"ok": False, "file_name": Path(file.filename or "arquivo").name, "error": f"Não foi possível processar: {type(exc).__name__}"})
    return {"received": len(files), "results": results}


@app.post("/api/imports/confirm")
def confirm_import(payload: dict[str, Any], db: Session = Depends(get_db)):
    try:
        student, duplicate = save_import(db, payload, Path(payload.get("file_name") or "historico.pdf").name)
        refreshed = load_student(db, student.id)
        return {"ok": True, "duplicate": duplicate, "student": student_summary(refreshed)}
    except ValueError as exc:
        db.rollback()
        raise HTTPException(422, str(exc)) from exc
    except Exception:
        db.rollback()
        raise


@app.get("/api/students")
def list_students(
    search: str | None = None,
    status: str | None = None,
    db: Session = Depends(get_db),
):
    stmt = select(Student).options(selectinload(Student.records), selectinload(Student.matrix)).order_by(Student.name)
    if status:
        stmt = stmt.where(Student.academic_status == status)
    students = db.scalars(stmt).all()
    if search:
        needle = normalize_name(search)
        students = [s for s in students if needle in normalize_name(s.name) or search in s.registration]
    return [student_summary(item) for item in students]


@app.get("/api/students/{student_id}")
def get_student(student_id: int, db: Session = Depends(get_db)):
    data = student_detail(db, student_id)
    if not data:
        raise HTTPException(404, "Estudante não encontrado")
    return data


@app.put("/api/students/{student_id}")
def update_student(student_id: int, payload: dict[str, Any], db: Session = Depends(get_db)):
    student = db.get(Student, student_id)
    if not student:
        raise HTTPException(404, "Estudante não encontrado")
    allowed = {"name", "matrix_id", "current_semester", "academic_status", "expected_graduation", "preferred_shift", "complementary_completed"}
    for key, value in payload.items():
        if key in allowed:
            setattr(student, key, value)
    if "current_semester" in payload:
        student.semester_source = "Manual"
    if "expected_graduation" in payload:
        student.graduation_source = "Manual"
    db.commit()
    return student_detail(db, student_id)


@app.put("/api/records/{record_id}")
def update_course_record(record_id: int, payload: dict[str, Any], db: Session = Depends(get_db)):
    record = db.get(CourseRecord, record_id)
    if not record:
        raise HTTPException(404, "Registro acadêmico não encontrado")
    for field in ("subject_name", "status", "academic_period", "elective_choice"):
        if field in payload:
            setattr(record, field, str(payload[field]).strip() if payload[field] is not None else None)
    for field in ("semester", "attendance", "hours"):
        if field in payload:
            setattr(record, field, int(payload[field]) if payload[field] not in (None, "") else None)
    if "grade" in payload:
        record.grade = float(payload["grade"]) if payload["grade"] not in (None, "") else None
    record.normalized_name = normalize_name(record.subject_name)
    record.hours_source = "Manual" if "hours" in payload else record.hours_source
    student = db.get(Student, record.student_id)
    if student:
        records = db.scalars(select(CourseRecord).where(CourseRecord.student_id == student.id)).all()
        student.completed_hours = sum(
            int(item.hours or 0) for item in records if item.status in {"Aprovado", "Dispensado"}
        )
    db.commit()
    return {
        "id": record.id,
        "semester": record.semester,
        "subject_name": record.subject_name,
        "display_name": record.elective_choice or record.subject_name,
        "status": record.status,
        "grade": record.grade,
        "academic_period": record.academic_period,
        "hours": record.hours,
        "hours_source": record.hours_source,
        "subject_id": record.subject_id,
    }


@app.delete("/api/students/{student_id}")
def delete_student(student_id: int, db: Session = Depends(get_db)):
    student = db.get(Student, student_id)
    if not student:
        raise HTTPException(404, "Estudante não encontrado")
    # O log de importação não possui chave estrangeira para permitir auditoria
    # de arquivos rejeitados. Ao excluir um perfil confirmado, apague também
    # os logs ligados à matrícula para remover seus dados de toda a base.
    db.execute(delete(ImportLog).where(ImportLog.registration == student.registration))
    db.delete(student)
    db.commit()
    return {"ok": True}


@app.put("/api/students/{student_id}/intents/{subject_id}")
def set_intent(student_id: int, subject_id: int, payload: dict[str, Any], db: Session = Depends(get_db)):
    if not db.get(Student, student_id) or not db.get(MatrixSubject, subject_id):
        raise HTTPException(404, "Estudante ou disciplina não encontrado")
    intent = db.scalar(select(EnrollmentIntent).where(EnrollmentIntent.student_id == student_id, EnrollmentIntent.subject_id == subject_id))
    if intent:
        intent.intends = bool(payload.get("intends", True))
    else:
        db.add(EnrollmentIntent(student_id=student_id, subject_id=subject_id, intends=bool(payload.get("intends", True))))
    db.commit()
    return {"ok": True}


@app.get("/api/demand")
def get_demand(category: str | None = None, db: Session = Depends(get_db)):
    rows = demand_rows(db)
    return [row for row in rows if not category or row["category"] == category]


@app.get("/api/graduating")
def get_graduating(db: Session = Depends(get_db)):
    year = settings_dict(db).get("graduation_year", "")
    students = db.scalars(select(Student).options(selectinload(Student.records), selectinload(Student.matrix))).all()
    selected = [s for s in students if s.academic_status == "Formando" or (year and (s.expected_graduation or "").startswith(year))]
    return [student_summary(item) for item in selected]


@app.post("/api/simulations")
def run_simulation(payload: dict[str, Any], db: Session = Depends(get_db)):
    return simulate(db, [int(item) for item in payload.get("subject_ids", [])])


@app.get("/api/simulations/saved")
def list_saved_simulations(db: Session = Depends(get_db)):
    rows = db.scalars(select(SimulationScenario).order_by(SimulationScenario.created_at.desc())).all()
    return [{"id": row.id, "name": row.name, "subject_ids": json.loads(row.subject_ids_json), "result": json.loads(row.result_json), "created_at": row.created_at.isoformat()} for row in rows]


@app.post("/api/simulations/saved")
def save_simulation(payload: dict[str, Any], db: Session = Depends(get_db)):
    name = str(payload.get("name") or "").strip()
    ids = [int(item) for item in payload.get("subject_ids", [])]
    if not name or not ids:
        raise HTTPException(422, "Informe o nome e selecione disciplinas")
    result = simulate(db, ids)
    row = SimulationScenario(name=name, subject_ids_json=json.dumps(ids), result_json=json.dumps(result, ensure_ascii=False))
    db.add(row)
    db.commit()
    db.refresh(row)
    return {"id": row.id, "name": row.name, "subject_ids": ids, "result": result}


@app.delete("/api/simulations/saved/{scenario_id}")
def delete_simulation(scenario_id: int, db: Session = Depends(get_db)):
    row = db.get(SimulationScenario, scenario_id)
    if not row:
        raise HTTPException(404, "Cenário não encontrado")
    db.delete(row)
    db.commit()
    return {"ok": True}


@app.get("/api/recommendations")
def recommendations(limit: int = 8, db: Session = Depends(get_db)):
    rows = demand_rows(db)[: max(1, min(limit, 30))]
    result = simulate(db, [row["subject_id"] for row in rows])
    result["recommendation"] = rows
    return result


@app.get("/api/classes")
def list_classes(db: Session = Depends(get_db)):
    subjects = {s.id: s for s in db.scalars(select(MatrixSubject)).all()}
    rows = db.scalars(select(PlannedClass).order_by(PlannedClass.weekday, PlannedClass.start_time)).all()
    return [
        {
            "id": row.id,
            "subject_id": row.subject_id,
            "subject_name": subjects[row.subject_id].name if row.subject_id in subjects else "Disciplina removida",
            "planning_period": row.planning_period,
            "label": row.label,
            "capacity": row.capacity,
            "shift": row.shift,
            "weekday": row.weekday,
            "start_time": row.start_time,
            "end_time": row.end_time,
            "professor": row.professor,
            "room": row.room,
            "notes": row.notes,
        }
        for row in rows
    ]


@app.post("/api/classes")
def create_class(payload: dict[str, Any], db: Session = Depends(get_db)):
    subject_id = int(payload.get("subject_id") or 0)
    if not db.get(MatrixSubject, subject_id):
        raise HTTPException(404, "Disciplina não encontrada")
    settings = settings_dict(db)
    row = PlannedClass(
        subject_id=subject_id,
        planning_period=payload.get("planning_period") or settings.get("reference_period", "2026/2"),
        label=payload.get("label") or "Turma A",
        capacity=int(payload.get("capacity") or settings.get("default_capacity", "30")),
        shift=payload.get("shift") or "Noite",
        weekday=payload.get("weekday"),
        start_time=payload.get("start_time"),
        end_time=payload.get("end_time"),
        professor=payload.get("professor"),
        room=payload.get("room"),
        notes=payload.get("notes"),
    )
    db.add(row)
    db.commit()
    db.refresh(row)
    return {"id": row.id}


@app.delete("/api/classes/{class_id}")
def delete_class(class_id: int, db: Session = Depends(get_db)):
    row = db.get(PlannedClass, class_id)
    if not row:
        raise HTTPException(404, "Turma não encontrada")
    db.delete(row)
    db.commit()
    return {"ok": True}


@app.get("/api/conflicts")
def get_conflicts(db: Session = Depends(get_db)):
    return conflicts(db)


def _style_sheet(ws, widths: list[int]) -> None:
    fill = PatternFill("solid", fgColor="0B6B57")
    for cell in ws[1]:
        cell.fill = fill
        cell.font = Font(color="FFFFFF", bold=True)
        cell.alignment = Alignment(horizontal="center")
    ws.freeze_panes = "A2"
    ws.auto_filter.ref = ws.dimensions
    for index, width in enumerate(widths, 1):
        ws.column_dimensions[get_column_letter(index)].width = width


@app.get("/api/reports/students/{student_id}.xlsx")
def student_excel(student_id: int, db: Session = Depends(get_db)):
    data = student_detail(db, student_id)
    if not data:
        raise HTTPException(404, "Estudante não encontrado")
    workbook = Workbook()
    sheet = workbook.active
    sheet.title = "Controle Acadêmico"
    sheet.append(["Semestre", "Disciplina", "Status", "Nota", "Ano/Semestre", "CH", "Origem CH"])
    for row in data["records"]:
        sheet.append([f"{row['semester']}º", row["display_name"], row["status"], row["grade"], row["academic_period"], row["hours"], row["hours_source"]])
    _style_sheet(sheet, [12, 55, 20, 10, 18, 10, 22])
    summary = workbook.create_sheet("Resumo")
    summary.append(["Indicador", "Valor"])
    for label, value in [
        ("Nome", data["name"]), ("Matrícula", data["registration"]), ("Matriz", data["matrix_name"]),
        ("Carga horária exigida", data["required_hours"]), ("Carga horária concluída", data["completed_hours"]),
        ("Integralização", data["progress"] / 100), ("IRA", data["ira"]),
    ]:
        summary.append([label, value])
    summary["B7"].number_format = "0%"
    _style_sheet(summary, [32, 32])
    output = io.BytesIO()
    workbook.save(output)
    output.seek(0)
    return StreamingResponse(output, media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet", headers={"Content-Disposition": f'attachment; filename="historico_{data["registration"]}.xlsx"'})


@app.get("/api/reports/demand.xlsx")
def demand_excel(db: Session = Depends(get_db)):
    workbook = Workbook()
    sheet = workbook.active
    sheet.title = "Demanda"
    headers = ["Código", "Disciplina", "Semestre", "Categoria", "Necessitam", "Aptos", "Potenciais", "Indeterminados", "Interessados", "Formandos", "Turmas", "Prioridade"]
    sheet.append(headers)
    for row in demand_rows(db):
        sheet.append([row["code"], row["name"], row["semester"], row["category"], row["total"], row["eligible"], row["potential"], row["indeterminate"], row["interested"], row["graduating"], row["estimated_classes"], row["priority"]])
    _style_sheet(sheet, [13, 55, 12, 20, 13, 10, 13, 16, 14, 12, 10, 22])
    output = io.BytesIO()
    workbook.save(output)
    output.seek(0)
    return StreamingResponse(output, media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet", headers={"Content-Disposition": 'attachment; filename="demanda_farmahub.xlsx"'})


def _pdf_table(title: str, subtitle: str, headers: list[str], rows: list[list[Any]], column_widths: list[float]) -> io.BytesIO:
    output = io.BytesIO()
    document = SimpleDocTemplate(output, pagesize=landscape(A4), leftMargin=12 * mm, rightMargin=12 * mm, topMargin=12 * mm, bottomMargin=12 * mm)
    styles = getSampleStyleSheet()
    styles.add(ParagraphStyle(name="CenteredTitle", parent=styles["Title"], alignment=TA_CENTER, textColor=colors.HexColor("#0B6B57")))
    story = [Paragraph(title, styles["CenteredTitle"]), Paragraph(subtitle, styles["Normal"]), Spacer(1, 6 * mm)]
    table_data = [[Paragraph(str(value), styles["BodyText"]) for value in headers]]
    for row in rows:
        table_data.append([Paragraph("—" if value is None else str(value), styles["BodyText"]) for value in row])
    table = Table(table_data, colWidths=[value * mm for value in column_widths], repeatRows=1)
    table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#0B6B57")),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        ("GRID", (0, 0), (-1, -1), 0.25, colors.HexColor("#CBD5E1")),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#F4F7F6")]),
        ("FONTSIZE", (0, 0), (-1, -1), 7.5),
        ("LEFTPADDING", (0, 0), (-1, -1), 4),
        ("RIGHTPADDING", (0, 0), (-1, -1), 4),
    ]))
    story.append(table)
    document.build(story)
    output.seek(0)
    return output


@app.get("/api/reports/students/{student_id}.pdf")
def student_pdf(student_id: int, db: Session = Depends(get_db)):
    data = student_detail(db, student_id)
    if not data:
        raise HTTPException(404, "Estudante não encontrado")
    rows = [[f"{r['semester']}º", r["display_name"], r["status"], r["grade"], r["academic_period"], r["hours"]] for r in data["records"]]
    output = _pdf_table("FarmaHub Acadêmico — Histórico consolidado", f"{data['name']} · Matrícula {data['registration']} · Gerado em {datetime.now():%d/%m/%Y}", ["Sem.", "Disciplina", "Status", "Nota", "Período", "CH"], rows, [12, 115, 32, 15, 25, 15])
    return StreamingResponse(output, media_type="application/pdf", headers={"Content-Disposition": f'attachment; filename="historico_{data["registration"]}.pdf"'})


@app.get("/api/reports/demand.pdf")
def demand_pdf(db: Session = Depends(get_db)):
    rows = [[r["code"], r["name"], r["total"], r["eligible"], r["potential"], r["interested"], r["graduating"], r["priority"]] for r in demand_rows(db)]
    output = _pdf_table("FarmaHub Acadêmico — Demanda de disciplinas", f"Relatório gerado em {datetime.now():%d/%m/%Y %H:%M}", ["Código", "Disciplina", "Demanda", "Aptos", "Potenciais", "Interesse", "Formandos", "Prioridade"], rows, [20, 100, 20, 17, 22, 20, 20, 35])
    return StreamingResponse(output, media_type="application/pdf", headers={"Content-Disposition": 'attachment; filename="demanda_farmahub.pdf"'})


@app.get("/api/backup")
def download_backup():
    if not DATABASE_PATH.exists():
        raise HTTPException(404, "Banco de dados ainda não foi criado")
    backup_path = Path(tempfile.gettempdir()) / f"farmahub_backup_{datetime.now():%Y%m%d_%H%M%S}.db"
    with closing(sqlite3.connect(DATABASE_PATH)) as source, closing(sqlite3.connect(backup_path)) as destination:
        source.backup(destination)
    return FileResponse(backup_path, media_type="application/vnd.sqlite3", filename=backup_path.name)


@app.post("/api/backup/restore")
def restore_backup(file: UploadFile = File(...)):
    data = file.file.read(50 * 1024 * 1024 + 1)
    if len(data) > 50 * 1024 * 1024:
        raise HTTPException(413, "O backup ultrapassa 50 MB")
    if not data.startswith(b"SQLite format 3\x00"):
        raise HTTPException(415, "O arquivo não é um banco SQLite válido")
    temp_path = Path(tempfile.gettempdir()) / "farmahub_restore_candidate.db"
    temp_path.write_bytes(data)
    try:
        with closing(sqlite3.connect(temp_path)) as candidate:
            tables = {row[0] for row in candidate.execute("SELECT name FROM sqlite_master WHERE type='table'")}
            required = {"students", "curriculum_matrices", "matrix_subjects", "course_records"}
            if not required.issubset(tables):
                raise HTTPException(422, "O arquivo não contém a estrutura do FarmaHub")
        engine.dispose()
        with closing(sqlite3.connect(temp_path)) as source, closing(sqlite3.connect(DATABASE_PATH)) as destination:
            source.backup(destination)
        return {"ok": True, "message": "Backup restaurado. Recarregue a página."}
    finally:
        temp_path.unlink(missing_ok=True)
