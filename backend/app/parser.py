from __future__ import annotations

import hashlib
import io
import re
import unicodedata
from collections import Counter, defaultdict
from typing import Any

import pdfplumber


STATUS_PATTERN = r"Aprovado|Dispensado|Em Curso|A Cursar|Reprovado por Nota|Reprovado por Frequência"
ROW_RE = re.compile(
    rf"^(?P<name>[A-ZÁÀÂÃÉÊÍÓÔÕÚÜÇ0-9][A-ZÁÀÂÃÉÊÍÓÔÕÚÜÇ0-9 :,.'()\-/]+?)\s+"
    rf"(?:(?P<period>\d{{4}}/[12])\s+(?P<grade>\d+[.,]\d+)\s+(?P<attendance>\d+)\s+(?P<hours>\d+)\s+)?"
    rf"(?:\*{{3}}\s+)?(?P<status>{STATUS_PATTERN})$"
)
SEMESTER_RE = re.compile(r"^\s*(\d{1,2})º\s+Semestre\s*$", re.IGNORECASE)


def normalize_name(value: str) -> str:
    value = unicodedata.normalize("NFKD", value)
    value = "".join(ch for ch in value if not unicodedata.combining(ch))
    value = re.sub(r"[^A-Z0-9]+", " ", value.upper()).strip()
    return re.sub(r"\s+", " ", value)


def normalize_status(value: str) -> str:
    normalized = normalize_name(value)
    mapping = {
        "APROVADO": "Aprovado",
        "DISPENSADO": "Dispensado",
        "EM CURSO": "Em Curso",
        "A CURSAR": "A Cursar",
        "REPROVADO POR NOTA": "Reprovado por Nota",
        "REPROVADO POR FREQUENCIA": "Reprovado por Frequência",
    }
    return mapping.get(normalized, value.strip())


def extract_text(pdf_bytes: bytes) -> str:
    with pdfplumber.open(io.BytesIO(pdf_bytes)) as pdf:
        return "\n\f\n".join(page.extract_text(layout=True) or "" for page in pdf.pages)


def _extract_identity(text: str) -> tuple[str | None, str | None, str | None]:
    name = registration = course = None
    lines = text.splitlines()
    for idx, line in enumerate(lines):
        header = re.sub(r"\s+", " ", line.strip())
        if header == "Nome Código" and idx + 1 < len(lines):
            candidate = lines[idx + 1].strip()
            match = re.match(r"(.+?)\s{3,}(\d{5,})$", candidate)
            if match:
                name, registration = match.group(1).strip(), match.group(2)
        if line.strip() == "Curso" and idx + 1 < len(lines):
            course = lines[idx + 1].strip()
    return name, registration, course


def parse_ulbra_history(pdf_bytes: bytes, reference_period: str | None = None) -> dict[str, Any]:
    text = extract_text(pdf_bytes)
    name, registration, course = _extract_identity(text)
    main_text = text.split("Outros Componentes Curriculares", 1)[0]
    semester = 0
    attempts: list[dict[str, Any]] = []
    for raw_line in main_text.splitlines():
        sem = SEMESTER_RE.match(raw_line)
        if sem:
            semester = int(sem.group(1))
            continue
        # Main discipline lines are flush-left; indented rows are teachers or elective choices.
        if len(raw_line) - len(raw_line.lstrip()) > 4:
            continue
        line = re.sub(r"\s+", " ", raw_line.strip())
        match = ROW_RE.match(line)
        if not match or not semester:
            continue
        item = match.groupdict()
        status = normalize_status(item["status"])
        attempts.append(
            {
                "semester": semester,
                "subject_name": item["name"].strip(),
                "normalized_name": normalize_name(item["name"]),
                "status": status,
                "grade": float(item["grade"].replace(",", ".")) if item["grade"] else None,
                "attendance": int(item["attendance"]) if item["attendance"] else None,
                "academic_period": item["period"] or (reference_period if status == "Em Curso" else None),
                "hours": int(item["hours"]) if item["hours"] else None,
                "hours_source": "Histórico" if item["hours"] else "Não disponível",
                "confidence": 1.0,
            }
        )

    grouped: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for item in attempts:
        grouped[item["normalized_name"]].append(item)

    rank = {
        "Aprovado": 6,
        "Dispensado": 5,
        "Em Curso": 4,
        "A Cursar": 3,
        "Reprovado por Frequência": 2,
        "Reprovado por Nota": 1,
    }
    consolidated: list[dict[str, Any]] = []
    duplicate_count = 0
    for records in grouped.values():
        duplicate_count += max(0, len(records) - 1)
        chosen = sorted(
            records,
            key=lambda x: (rank.get(x["status"], 0), x["academic_period"] or ""),
            reverse=True,
        )[0].copy()
        consolidated.append(chosen)
    consolidated.sort(key=lambda x: (x["semester"], x["subject_name"]))

    elective_choice = None
    optional_section = text.split("Disciplinas Optativas", 1)
    if len(optional_section) == 2:
        choice_match = re.search(
            rf"^\s+([A-ZÁÀÂÃÉÊÍÓÔÕÚÜÇ][A-ZÁÀÂÃÉÊÍÓÔÕÚÜÇ0-9 :,.'()\-/]+?)\s+\d+\s+\d{{4}}/[12]\s+\d+[.,]\d+\s+\d+\s+Aprovado\s*$",
            optional_section[1],
            re.MULTILINE,
        )
        if choice_match:
            elective_choice = choice_match.group(1).strip()
    if elective_choice:
        for item in consolidated:
            if item["normalized_name"] == "OPTATIVA I" and item["status"] in {"Aprovado", "Dispensado"}:
                item["elective_choice"] = elective_choice
                break

    required = re.search(r"Carga Horária Exigida:\s*(\d+)", text)
    completed = re.search(r"Carga Horária Cumprida:\s*(\d+)", text)
    ira = re.search(r"Índice de Rendimento Acadêmico \(IRA\):\s*([\d,]+)", text)
    complementary = re.search(r"ATIVIDADES COMPLEMENTARES\s+(\d+)\s+(\d+)", text)
    warnings: list[str] = []
    if not name:
        warnings.append("Nome não identificado")
    if not registration:
        warnings.append("Matrícula não identificada")
    if not consolidated:
        warnings.append("Nenhuma disciplina foi identificada")

    counts = Counter(item["status"] for item in consolidated)
    return {
        "file_hash": hashlib.sha256(pdf_bytes).hexdigest(),
        "student": {
            "name": name,
            "registration": registration,
            "course": course or "FARMÁCIA",
            "required_hours": int(required.group(1)) if required else 0,
            "completed_hours": int(completed.group(1)) if completed else 0,
            "complementary_required": int(complementary.group(1)) if complementary else 0,
            "complementary_completed": int(complementary.group(2)) if complementary else 0,
            "ira": float(ira.group(1).replace(",", ".")) if ira else None,
        },
        "records": consolidated,
        "attempts": attempts,
        "summary": {"total": len(consolidated), "statuses": dict(counts), "duplicates_consolidated": duplicate_count},
        "warnings": warnings,
    }
