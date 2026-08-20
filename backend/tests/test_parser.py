from __future__ import annotations

import os
from collections import Counter
from pathlib import Path

import pytest

from app.parser import normalize_name, normalize_status, parse_ulbra_history


def test_normalization():
    assert normalize_name("  Farmácia Clínica e Hospitalar ") == "FARMACIA CLINICA E HOSPITALAR"
    assert normalize_status(" Em Curso ") == "Em Curso"
    assert normalize_status("Reprovado por Frequência") == "Reprovado por Frequência"


def test_reference_history_regression():
    configured = os.getenv("FARMAHUB_REFERENCE_PDF")
    if not configured:
        pytest.skip("Defina FARMAHUB_REFERENCE_PDF para executar a regressão documental")
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
    configured = os.getenv("FARMAHUB_REFERENCE_PDF")
    if not configured:
        pytest.skip("Defina FARMAHUB_REFERENCE_PDF para executar a regressão documental")
    parsed = parse_ulbra_history(Path(configured).read_bytes(), "2026/2")
    serialized = str(parsed).lower()
    assert "cpf" not in serialized
    assert "nascimento" not in serialized
    assert "identidade" not in serialized
