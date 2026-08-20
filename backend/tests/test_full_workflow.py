from __future__ import annotations

from fastapi.testclient import TestClient
from sqlalchemy import select

from app.database import SessionLocal
from app.main import app
from app.models import CourseAttempt, CourseRecord, ImportLog, MatrixSubject, Student


def test_complete_local_workflow():
    registration = "AUDIT-0001"
    file_hash = "a" * 64

    with TestClient(app) as client:
        matrix = client.get("/api/matrices").json()[0]
        subjects = [row for row in matrix["subjects"] if row["semester"] > 0][:2]
        assert len(subjects) == 2

        with SessionLocal() as db:
            student = Student(
                registration=registration,
                name="Estudante de Auditoria",
                matrix_id=matrix["id"],
                current_semester=2,
                academic_status="Ativo",
                preferred_shift="Noite",
                required_hours=matrix["total_hours"],
                completed_hours=60,
            )
            db.add(student)
            db.flush()
            student_id = student.id
            for subject in subjects:
                db.add(
                    CourseRecord(
                        student_id=student_id,
                        subject_id=subject["id"],
                        subject_name=subject["name"],
                        normalized_name=subject["name"].lower(),
                        semester=subject["semester"],
                        status="A Cursar",
                        hours=subject["hours"],
                        hours_source="Matriz",
                    )
                )
            db.add(
                CourseAttempt(
                    student_id=student_id,
                    subject_name=subjects[0]["name"],
                    status="Reprovado",
                    grade=4.0,
                    academic_period="2025/2",
                )
            )
            db.add(
                ImportLog(
                    file_name="auditoria.pdf",
                    file_hash=file_hash,
                    registration=registration,
                    status="Confirmado",
                )
            )
            db.commit()

        dashboard = client.get("/api/dashboard")
        assert dashboard.status_code == 200
        assert dashboard.json()["students"] == 1

        students = client.get("/api/students")
        assert students.status_code == 200
        assert students.json()[0]["registration"] == registration

        detail = client.get(f"/api/students/{student_id}")
        assert detail.status_code == 200
        assert len(detail.json()["records"]) == 2
        assert len(detail.json()["attempts"]) == 1

        update = client.put(
            f"/api/students/{student_id}",
            json={"academic_status": "Formando", "expected_graduation": "2027/1"},
        )
        assert update.status_code == 200
        assert update.json()["academic_status"] == "Formando"

        intent = client.put(
            f"/api/students/{student_id}/intents/{subjects[0]['id']}",
            json={"intends": True},
        )
        assert intent.status_code == 200

        demand = client.get("/api/demand")
        assert demand.status_code == 200
        assert sum(row["total"] for row in demand.json()) == 2
        assert any(row["interested"] == 1 for row in demand.json())

        graduating = client.get("/api/graduating")
        assert graduating.status_code == 200
        assert any(row["id"] == student_id for row in graduating.json())

        simulation = client.post(
            "/api/simulations", json={"subject_ids": [row["id"] for row in subjects]}
        )
        assert simulation.status_code == 200
        assert simulation.json()["unique_students"] == 1
        assert simulation.json()["curricular_needs"] == 2

        class_ids = []
        for subject in subjects:
            response = client.post(
                "/api/classes",
                json={
                    "subject_id": subject["id"],
                    "planning_period": "2027/1",
                    "weekday": "Segunda-feira",
                    "start_time": "19:00",
                    "end_time": "20:30",
                    "professor": "Docente Teste",
                    "room": "Sala Teste",
                },
            )
            assert response.status_code == 200
            class_ids.append(response.json()["id"])
        conflicts = client.get("/api/conflicts")
        assert conflicts.status_code == 200
        assert conflicts.json()

        student_xlsx = client.get(f"/api/reports/students/{student_id}.xlsx")
        assert student_xlsx.status_code == 200
        assert student_xlsx.content.startswith(b"PK")
        student_pdf = client.get(f"/api/reports/students/{student_id}.pdf")
        assert student_pdf.status_code == 200
        assert student_pdf.content.startswith(b"%PDF")
        demand_xlsx = client.get("/api/reports/demand.xlsx")
        assert demand_xlsx.status_code == 200
        assert demand_xlsx.content.startswith(b"PK")
        demand_pdf = client.get("/api/reports/demand.pdf")
        assert demand_pdf.status_code == 200
        assert demand_pdf.content.startswith(b"%PDF")

        backup = client.get("/api/backup")
        assert backup.status_code == 200
        assert backup.content.startswith(b"SQLite format 3\x00")
        restore = client.post(
            "/api/backup/restore",
            files={"file": ("auditoria.db", backup.content, "application/vnd.sqlite3")},
        )
        assert restore.status_code == 200
        assert restore.json()["ok"] is True
        assert client.get("/api/health").json()["status"] == "ok"

        for class_id in class_ids:
            assert client.delete(f"/api/classes/{class_id}").status_code == 200
        deletion = client.delete(f"/api/students/{student_id}")
        assert deletion.status_code == 200
        assert client.get(f"/api/students/{student_id}").status_code == 404

        with SessionLocal() as db:
            assert db.scalar(select(Student).where(Student.registration == registration)) is None
            assert db.scalar(select(ImportLog).where(ImportLog.file_hash == file_hash)) is None
