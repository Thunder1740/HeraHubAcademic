from __future__ import annotations

import os
import io
from collections import Counter
from pathlib import Path

import pytest
from reportlab.pdfgen import canvas

from app.parser import normalize_name, normalize_status, parse_curriculum_matrix, parse_ulbra_history


def test_normalization():
    assert normalize_name("  Farmácia Clínica e Hospitalar ") == "FARMACIA CLINICA E HOSPITALAR"
    assert normalize_status(" Em Curso ") == "Em Curso"
    assert normalize_status("Reprovado por Frequência") == "Reprovado por Frequência"


def test_curriculum_matrix_parser():
    output = io.BytesIO()
    pdf = canvas.Canvas(output)
    lines = [
        "MATRIZ CURRICULAR",
        "Unidade: 3 Universidade Luterana do Brasil - Campus Canoas",
        "Curso: 010835 FARMACIA",
        "Codigo Nome Sem CH Seq",
        "10001 INTRODUCAO A FARMACIA 1 60 1",
        "10002 ESTAGIO SUPERVISIONADO EM ANALISES CLINICAS E 9 200 2",
        "TOXICOLOGICAS",
        "Carga Horaria Total: 260",
    ]
    y = 800
    for line in lines:
        pdf.drawString(40, y, line)
        y -= 20
    pdf.save()
    parsed = parse_curriculum_matrix(output.getvalue())
    assert parsed["total_hours"] == 260
    assert parsed["calculated_hours"] == 260
    assert len(parsed["subjects"]) == 2
    assert parsed["subjects"][1]["name"].endswith("TOXICOLOGICAS")
    assert parsed["subjects"][1]["category"] == "Estágio"


def test_reference_history_regression():
    configured = os.getenv("HERA_REFERENCE_PDF") or os.getenv("FARMAHUB_REFERENCE_PDF")
    if not configured:
        pytest.skip("Defina HERA_REFERENCE_PDF para executar a regressão documental")
    path = Path(configured)
    parsed = parse_ulbra_history(path.read_bytes(), "2026/2")
    assert parsed["student"]["name"]
    assert parsed["student"]["registration"]
    assert parsed["summary"]["total"] == 49
    assert parsed["summary"]["statuses"] == {
        "Aprovado": 26,
        "Dispensado": 4,
        "Em Curso": 8,
        "A Cursar": 11,
    }
    assert parsed["student"]["required_hours"] == 4148
    assert parsed["student"]["completed_hours"] == 2432
    assert parsed["student"]["complementary_required"] == 82
    assert parsed["student"]["complementary_completed"] == 0
    assert parsed["student"]["ira"] == 7.125
    assert parsed["summary"]["duplicates_consolidated"] == 4
    approved_names = {item["normalized_name"] for item in parsed["records"] if item["status"] == "Aprovado"}
    assert "ANALISE FARMACEUTICA" in approved_names
    assert "MICROBIOLOGIA E IMUNOLOGIA" in approved_names
    optativa = next(item for item in parsed["records"] if item["normalized_name"] == "OPTATIVA I")
    assert optativa.get("elective_choice") == "LIBRAS"


def test_no_sensitive_identity_fields_are_returned():
    configured = os.getenv("HERA_REFERENCE_PDF") or os.getenv("FARMAHUB_REFERENCE_PDF")
    if not configured:
        pytest.skip("Defina HERA_REFERENCE_PDF para executar a regressão documental")
    parsed = parse_ulbra_history(Path(configured).read_bytes(), "2026/2")
    serialized = str(parsed).lower()
    assert "cpf" not in serialized
    assert "nascimento" not in serialized
    assert "identidade" not in serialized
