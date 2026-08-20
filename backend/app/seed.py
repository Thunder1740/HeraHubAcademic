from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session

from .models import CurriculumMatrix, MatrixSubject, Setting
from .parser import normalize_name


SUBJECTS = [
    ("134104", "ATIVIDADES COMPLEMENTARES", 0, 82, 0, 1),
    ("134105", "INTRODUÇÃO E LEGISLAÇÃO FARMACÊUTICA", 1, 76, 4, 2),
    ("128100", "ANATOMOFISIOLOGIA", 1, 76, 4, 3),
    ("112150", "BIOLOGIA CELULAR, EMBRIOLOGIA E HISTOLOGIA", 1, 76, 4, 4),
    ("134106", "QUÍMICA INORGÂNICA E FÍSICO-QUÍMICA", 1, 76, 4, 5),
    ("112151", "BIOÉTICA E BIOSSEGURANÇA", 1, 76, 4, 6),
    ("112090", "COMUNICAÇÃO PARA O PLANEJAMENTO PROFISSIONAL", 1, 76, 4, 7),
    ("134109", "FARMACOTÉCNICA E TECNOLOGIA FARMACÊUTICA I", 2, 76, 4, 8),
    ("134108", "FUNDAMENTOS DE QUÍMICA ORGÂNICA I", 2, 76, 4, 9),
    ("134101", "BIOQUÍMICA ESTRUTURAL E METABÓLICA", 2, 76, 4, 10),
    ("112152", "EPIDEMIOLOGIA E BIOESTATÍSTICA", 2, 76, 4, 11),
    ("134100", "MICROBIOLOGIA E IMUNOLOGIA", 2, 76, 4, 12),
    ("134113", "FARMACOTÉCNICA E TECNOLOGIA FARMACÊUTICA II", 3, 76, 4, 13),
    ("134110", "FUNDAMENTOS DE QUÍMICA ORGÂNICA II", 3, 76, 4, 14),
    ("134102", "FISIOPATOLOGIA", 3, 76, 4, 15),
    ("134111", "ESTÁGIO: RELAÇÕES INTERPESSOAIS E COMUNICAÇÃO EM SAÚDE", 3, 38, 2, 16),
    ("112080", "SOCIEDADE E CONTEMPORANEIDADE", 3, 76, 4, 17),
    ("128101", "POLÍTICAS PÚBLICAS E GESTÃO EM SAÚDE", 3, 76, 4, 18),
    ("134112", "FARMACOTÉCNICA E TECNOLOGIA FARMACÊUTICA III", 4, 76, 4, 19),
    ("134107", "BIOLOGIA MOLECULAR E GENÉTICA", 4, 76, 4, 20),
    ("134114", "FARMACOLOGIA E FARMACODINÂMICA I", 4, 114, 6, 21),
    ("134115", "ANÁLISE FARMACÊUTICA", 4, 76, 4, 22),
    ("128102", "PRÁTICAS INTERPROFISSIONAIS DE EDUCAÇÃO EM SAÚDE", 4, 76, 4, 23),
    ("129109", "BIOQUÍMICA CLÍNICA", 5, 114, 6, 24),
    ("134116", "FARMACOLOGIA E FARMACODINÂMICA II", 5, 76, 4, 25),
    ("134117", "ASSISTÊNCIA FARMACÊUTICA", 5, 76, 4, 26),
    ("134118", "BROMATOLOGIA", 5, 76, 4, 27),
    ("134124", "ESTÁGIO: DROGARIA E MANIPULAÇÃO", 5, 114, 6, 28),
    ("112060", "CULTURA RELIGIOSA", 6, 76, 4, 29),
    ("134121", "CONTROLE DE QUALIDADE DE INSUMOS E PRODUTOS FARMACÊUTICOS", 6, 38, 2, 30),
    ("134122", "HOMEOPATIA", 6, 76, 4, 31),
    ("134123", "QUÍMICA FARMACÊUTICA E MEDICINAL", 6, 76, 4, 32),
    ("134119", "ESTÁGIO: ALIMENTOS", 6, 38, 2, 33),
    ("134131", "PRÁTICAS INTEGRATIVAS E COMPLEMENTARES APLICADAS À FARMÁCIA", 6, 76, 4, 34),
    ("134126", "FARMACOGNOSIA E FITOTERÁPICOS", 7, 76, 4, 35),
    ("112070", "CIÊNCIA, INOVAÇÃO E EMPREENDEDORISMO", 7, 76, 4, 36),
    ("134120", "ANÁLISES CITOLÓGICAS E PARASITOLÓGICAS", 7, 76, 4, 37),
    ("134128", "ESTÁGIO: ASSISTÊNCIA FARMACÊUTICA E SAÚDE PÚBLICA", 7, 76, 4, 38),
    ("134125", "FARMÁCIA CLÍNICA E HOSPITALAR", 7, 76, 4, 39),
    ("129108", "MICROBIOLOGIA CLÍNICA", 8, 76, 4, 40),
    ("134130", "HEMATOLOGIA", 8, 76, 4, 41),
    ("129112", "IMUNOLOGIA CLÍNICA", 8, 76, 4, 42),
    ("134127", "ESTÁGIO: FARMÁCIA HOSPITALAR", 8, 76, 4, 43),
    ("134129", "SEMIOLOGIA E CUIDADOS FARMACÊUTICOS", 8, 76, 4, 44),
    ("129117", "TOXICOLOGIA", 9, 76, 4, 45),
    ("111101", "OPTATIVA I", 9, 76, 4, 46),
    ("134132", "ESTÁGIO: ANÁLISES CLÍNICAS", 9, 228, 12, 47),
    ("129103", "BIOTECNOLOGIA", 10, 76, 4, 48),
    ("111102", "OPTATIVA II", 10, 76, 4, 49),
    ("134133", "ESTÁGIO: CIÊNCIAS FARMACÊUTICAS", 10, 266, 14, 50),
]


def category_for(name: str) -> str:
    if name == "ATIVIDADES COMPLEMENTARES":
        return "Atividade complementar"
    if name.startswith("ESTÁGIO:"):
        return "Estágio"
    if name.startswith("OPTATIVA"):
        return "Optativa"
    return "Regular"


def bootstrap(db: Session) -> CurriculumMatrix:
    matrix = db.scalar(select(CurriculumMatrix).where(CurriculumMatrix.name == "Farmácia — Matriz 2021"))
    if matrix is None:
        matrix = CurriculumMatrix(
            name="Farmácia — Matriz 2021",
            course="Farmácia",
            campus="ULBRA Canoas",
            valid_from="2021",
            total_hours=4148,
        )
        db.add(matrix)
        db.flush()
        for code, name, semester, hours, credits, sequence in SUBJECTS:
            db.add(
                MatrixSubject(
                    matrix_id=matrix.id,
                    code=code,
                    name=name,
                    normalized_name=normalize_name(name),
                    semester=semester,
                    hours=hours,
                    credits=credits,
                    sequence=sequence,
                    category=category_for(name),
                )
            )
    defaults = {
        "reference_period": "2026/2",
        "graduation_year": "2027",
        "default_capacity": "30",
        "stage_capacity": "20",
        "default_shift": "Noite",
        "display_user": "Farma",
        "retain_pdfs": "false",
    }
    existing = {row.key for row in db.scalars(select(Setting)).all()}
    for key, value in defaults.items():
        if key not in existing:
            db.add(Setting(key=key, value=value))
    db.commit()
    db.refresh(matrix)
    return matrix
