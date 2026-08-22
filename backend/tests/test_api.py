from __future__ import annotations

import os

from fastapi.testclient import TestClient

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


def test_reference_upload_review():
    path = os.getenv("HERA_REFERENCE_PDF") or os.getenv("FARMAHUB_REFERENCE_PDF")
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
