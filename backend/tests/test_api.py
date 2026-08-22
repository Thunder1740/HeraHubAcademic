from __future__ import annotations

import io
import os

from fastapi.testclient import TestClient
from reportlab.pdfgen import canvas

from app.main import app


client = TestClient(app)


def test_health():
    with client:
        response = client.get("/api/health")
        assert response.status_code == 200
        assert response.json()["status"] == "ok"


def test_bootstrap_matrix():
    with client:
        matrices = client.get("/api/matrices").json()
        assert matrices
        assert matrices[0]["total_hours"] == 4148
        assert matrices[0]["subject_count"] == 50


def test_create_and_delete_matrix():
    with client:
        created = client.post(
            "/api/matrices",
            json={"name": "Matriz temporária de teste", "total_hours": 100},
        )
        assert created.status_code == 200
        matrix_id = created.json()["id"]
        subject = client.post(
            f"/api/matrices/{matrix_id}/subjects",
            json={"code": "TMP001", "name": "Componente temporário", "hours": 100},
        )
        assert subject.status_code == 200

        deleted = client.delete(f"/api/matrices/{matrix_id}")
        assert deleted.status_code == 200
        assert deleted.json()["name"] == "Matriz temporária de teste"
        assert all(row["id"] != matrix_id for row in client.get("/api/matrices").json())
        assert client.delete(f"/api/matrices/{matrix_id}").status_code == 404


def test_matrix_pdf_review_confirm_edit_and_delete():
    output = io.BytesIO()
    pdf = canvas.Canvas(output)
    lines = [
        "MATRIZ CURRICULAR",
        "Unidade: 3 Universidade Luterana do Brasil - Campus Canoas",
        "Curso: 010835 FARMACIA",
        "Codigo Nome Sem CH Seq",
        "90001 FUNDAMENTOS DE FARMACIA 1 60 1",
        "90002 PRATICA FARMACEUTICA 2 80 2",
        "Carga Horaria Total: 140",
    ]
    y = 800
    for line in lines:
        pdf.drawString(40, y, line)
        y -= 20
    pdf.save()

    with client:
        review = client.post(
            "/api/matrices/import/review",
            files={"file": ("matriz-hera.pdf", output.getvalue(), "application/pdf")},
        )
        assert review.status_code == 200
        reviewed = review.json()
        assert reviewed["total_hours"] == 140
        assert len(reviewed["subjects"]) == 2

        # Simula a revisão editável feita pela pessoa antes da confirmação.
        reviewed["name"] = "Matriz Hera importada"
        reviewed["subjects"][0]["name"] = "Fundamentos de Farmácia Revisados"
        confirmed = client.post("/api/matrices/import/confirm", json=reviewed)
        assert confirmed.status_code == 200
        matrix = confirmed.json()
        assert matrix["subject_count"] == 2
        assert matrix["subjects"][0]["name"] == "Fundamentos de Farmácia Revisados"

        # Garante que a disciplina continua editável após entrar no banco.
        subject = matrix["subjects"][0]
        edited = client.put(
            f"/api/subjects/{subject['id']}",
            json={"name": "Fundamentos Hera", "hours": 70, "semester": 1},
        )
        assert edited.status_code == 200
        stored = next(row for row in client.get("/api/matrices").json() if row["id"] == matrix["id"])
        assert stored["subjects"][0]["name"] == "Fundamentos Hera"
        assert stored["subjects"][0]["hours"] == 70

        assert client.delete(f"/api/matrices/{matrix['id']}").status_code == 200
        assert all(row["id"] != matrix["id"] for row in client.get("/api/matrices").json())


def test_settings_round_trip():
    with client:
        original = client.get("/api/settings")
        assert original.status_code == 200
        updated = client.put(
            "/api/settings",
            json={"reference_period": "2030/1", "default_capacity": 42, "retain_pdfs": False},
        )
        assert updated.status_code == 200
        assert updated.json()["reference_period"] == "2030/1"
        assert updated.json()["default_capacity"] == "42"
        assert updated.json()["retain_pdfs"] == "false"


def test_reference_upload_review():
    path = os.getenv("HERA_REFERENCE_PDF")
    if not path:
        return
    with client, open(path, "rb") as stream:
        response = client.post("/api/imports/review", files=[("files", ("historico.pdf", stream, "application/pdf"))])
    assert response.status_code == 200
    parsed = response.json()["results"][0]["data"]
    assert parsed["summary"]["total"] == 49
    assert parsed["summary"]["unmatched"] == 0
    assert parsed["summary"]["hours_filled_from_matrix"] == 19


def test_prerequisite_equivalence_and_saved_scenario_routes():
    with client:
        subjects = client.get("/api/matrices").json()[0]["subjects"]
        regular = [item for item in subjects if item["semester"] > 0]
        first, second = regular[0], regular[1]
        response = client.post(f"/api/subjects/{second['id']}/prerequisites", json={"required_subject_id": first["id"]})
        assert response.status_code == 200
        assert any(item["id"] == first["id"] for item in client.get(f"/api/subjects/{second['id']}/prerequisites").json())
        assert client.delete(f"/api/subjects/{second['id']}/prerequisites/{first['id']}").status_code == 200

        assert client.post("/api/equivalences", json={"subject_id": first["id"], "equivalent_subject_id": second["id"], "confirmed": True}).status_code == 200
        equivalences = client.get("/api/equivalences").json()
        assert equivalences
        assert client.delete(f"/api/equivalences/{equivalences[0]['id']}").status_code == 200

        saved = client.post("/api/simulations/saved", json={"name": "Cenário de teste", "subject_ids": [first["id"]]})
        assert saved.status_code == 200
        scenario_id = saved.json()["id"]
        assert any(item["id"] == scenario_id for item in client.get("/api/simulations/saved").json())
        assert client.delete(f"/api/simulations/saved/{scenario_id}").status_code == 200
