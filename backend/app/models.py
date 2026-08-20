from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy import Boolean, DateTime, Float, ForeignKey, Integer, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .database import Base


def utc_now() -> datetime:
    return datetime.now(timezone.utc).replace(tzinfo=None)


class CurriculumMatrix(Base):
    __tablename__ = "curriculum_matrices"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(120), unique=True, index=True)
    course: Mapped[str] = mapped_column(String(80), default="Farmácia")
    campus: Mapped[str] = mapped_column(String(120), default="ULBRA Canoas")
    valid_from: Mapped[str | None] = mapped_column(String(20))
    valid_to: Mapped[str | None] = mapped_column(String(20))
    total_hours: Mapped[int] = mapped_column(Integer, default=4148)
    active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utc_now)

    subjects: Mapped[list[MatrixSubject]] = relationship(back_populates="matrix", cascade="all, delete-orphan")
    students: Mapped[list[Student]] = relationship(back_populates="matrix")


class MatrixSubject(Base):
    __tablename__ = "matrix_subjects"
    __table_args__ = (UniqueConstraint("matrix_id", "code", name="uq_matrix_subject_code"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    matrix_id: Mapped[int] = mapped_column(ForeignKey("curriculum_matrices.id", ondelete="CASCADE"), index=True)
    code: Mapped[str] = mapped_column(String(30))
    name: Mapped[str] = mapped_column(String(220), index=True)
    normalized_name: Mapped[str] = mapped_column(String(220), index=True)
    semester: Mapped[int] = mapped_column(Integer, default=0)
    hours: Mapped[int] = mapped_column(Integer, default=0)
    credits: Mapped[int] = mapped_column(Integer, default=0)
    sequence: Mapped[int] = mapped_column(Integer, default=0)
    category: Mapped[str] = mapped_column(String(40), default="Regular")
    active: Mapped[bool] = mapped_column(Boolean, default=True)
    notes: Mapped[str | None] = mapped_column(Text)

    matrix: Mapped[CurriculumMatrix] = relationship(back_populates="subjects")
    records: Mapped[list[CourseRecord]] = relationship(back_populates="subject")


class Prerequisite(Base):
    __tablename__ = "prerequisites"
    __table_args__ = (UniqueConstraint("subject_id", "required_subject_id", name="uq_prerequisite"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    subject_id: Mapped[int] = mapped_column(ForeignKey("matrix_subjects.id", ondelete="CASCADE"), index=True)
    required_subject_id: Mapped[int] = mapped_column(ForeignKey("matrix_subjects.id", ondelete="CASCADE"))
    rule_type: Mapped[str] = mapped_column(String(30), default="Obrigatório")


class SubjectEquivalence(Base):
    __tablename__ = "subject_equivalences"
    __table_args__ = (UniqueConstraint("subject_id", "equivalent_subject_id", name="uq_subject_equivalence"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    subject_id: Mapped[int] = mapped_column(ForeignKey("matrix_subjects.id", ondelete="CASCADE"), index=True)
    equivalent_subject_id: Mapped[int] = mapped_column(ForeignKey("matrix_subjects.id", ondelete="CASCADE"), index=True)
    confirmed: Mapped[bool] = mapped_column(Boolean, default=True)
    notes: Mapped[str | None] = mapped_column(Text)


class Student(Base):
    __tablename__ = "students"

    id: Mapped[int] = mapped_column(primary_key=True)
    registration: Mapped[str] = mapped_column(String(40), unique=True, index=True)
    name: Mapped[str] = mapped_column(String(160), index=True)
    course: Mapped[str] = mapped_column(String(80), default="Farmácia")
    matrix_id: Mapped[int | None] = mapped_column(ForeignKey("curriculum_matrices.id", ondelete="SET NULL"), index=True)
    current_semester: Mapped[int | None] = mapped_column(Integer)
    semester_source: Mapped[str] = mapped_column(String(30), default="Inferido")
    academic_status: Mapped[str] = mapped_column(String(30), default="Ativo", index=True)
    expected_graduation: Mapped[str | None] = mapped_column(String(20), index=True)
    graduation_source: Mapped[str] = mapped_column(String(30), default="Não disponível")
    preferred_shift: Mapped[str] = mapped_column(String(20), default="Noite")
    required_hours: Mapped[int] = mapped_column(Integer, default=0)
    completed_hours: Mapped[int] = mapped_column(Integer, default=0)
    complementary_required: Mapped[int] = mapped_column(Integer, default=0)
    complementary_completed: Mapped[int] = mapped_column(Integer, default=0)
    ira: Mapped[float | None] = mapped_column(Float)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=utc_now, onupdate=utc_now)

    matrix: Mapped[CurriculumMatrix | None] = relationship(back_populates="students")
    records: Mapped[list[CourseRecord]] = relationship(back_populates="student", cascade="all, delete-orphan")
    attempts: Mapped[list[CourseAttempt]] = relationship(back_populates="student", cascade="all, delete-orphan")
    intents: Mapped[list[EnrollmentIntent]] = relationship(back_populates="student", cascade="all, delete-orphan")


class CourseRecord(Base):
    __tablename__ = "course_records"
    __table_args__ = (UniqueConstraint("student_id", "subject_id", name="uq_student_subject"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    student_id: Mapped[int] = mapped_column(ForeignKey("students.id", ondelete="CASCADE"), index=True)
    subject_id: Mapped[int | None] = mapped_column(ForeignKey("matrix_subjects.id", ondelete="SET NULL"), index=True)
    subject_name: Mapped[str] = mapped_column(String(220), index=True)
    normalized_name: Mapped[str] = mapped_column(String(220), index=True)
    semester: Mapped[int] = mapped_column(Integer)
    status: Mapped[str] = mapped_column(String(40), index=True)
    grade: Mapped[float | None] = mapped_column(Float)
    attendance: Mapped[int | None] = mapped_column(Integer)
    academic_period: Mapped[str | None] = mapped_column(String(20))
    hours: Mapped[int | None] = mapped_column(Integer)
    hours_source: Mapped[str] = mapped_column(String(30), default="Histórico")
    elective_choice: Mapped[str | None] = mapped_column(String(160))
    is_stage: Mapped[bool] = mapped_column(Boolean, default=False)
    confidence: Mapped[float] = mapped_column(Float, default=1.0)

    student: Mapped[Student] = relationship(back_populates="records")
    subject: Mapped[MatrixSubject | None] = relationship(back_populates="records")


class CourseAttempt(Base):
    __tablename__ = "course_attempts"

    id: Mapped[int] = mapped_column(primary_key=True)
    student_id: Mapped[int] = mapped_column(ForeignKey("students.id", ondelete="CASCADE"), index=True)
    subject_name: Mapped[str] = mapped_column(String(220), index=True)
    status: Mapped[str] = mapped_column(String(40))
    grade: Mapped[float | None] = mapped_column(Float)
    academic_period: Mapped[str | None] = mapped_column(String(20))
    attendance: Mapped[int | None] = mapped_column(Integer)
    hours: Mapped[int | None] = mapped_column(Integer)

    student: Mapped[Student] = relationship(back_populates="attempts")


class EnrollmentIntent(Base):
    __tablename__ = "enrollment_intents"
    __table_args__ = (UniqueConstraint("student_id", "subject_id", name="uq_intent"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    student_id: Mapped[int] = mapped_column(ForeignKey("students.id", ondelete="CASCADE"), index=True)
    subject_id: Mapped[int] = mapped_column(ForeignKey("matrix_subjects.id", ondelete="CASCADE"), index=True)
    intends: Mapped[bool] = mapped_column(Boolean, default=True)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=utc_now, onupdate=utc_now)

    student: Mapped[Student] = relationship(back_populates="intents")


class ImportLog(Base):
    __tablename__ = "import_logs"

    id: Mapped[int] = mapped_column(primary_key=True)
    file_name: Mapped[str] = mapped_column(String(240))
    file_hash: Mapped[str] = mapped_column(String(64), unique=True, index=True)
    registration: Mapped[str | None] = mapped_column(String(40), index=True)
    status: Mapped[str] = mapped_column(String(30))
    warnings_json: Mapped[str] = mapped_column(Text, default="[]")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utc_now)


class PlannedClass(Base):
    __tablename__ = "planned_classes"

    id: Mapped[int] = mapped_column(primary_key=True)
    subject_id: Mapped[int] = mapped_column(ForeignKey("matrix_subjects.id", ondelete="CASCADE"), index=True)
    planning_period: Mapped[str] = mapped_column(String(20), index=True)
    label: Mapped[str] = mapped_column(String(40), default="Turma A")
    capacity: Mapped[int] = mapped_column(Integer, default=30)
    shift: Mapped[str] = mapped_column(String(20), default="Noite")
    weekday: Mapped[str | None] = mapped_column(String(20))
    start_time: Mapped[str | None] = mapped_column(String(10))
    end_time: Mapped[str | None] = mapped_column(String(10))
    professor: Mapped[str | None] = mapped_column(String(160))
    room: Mapped[str | None] = mapped_column(String(80))
    notes: Mapped[str | None] = mapped_column(Text)


class SimulationScenario(Base):
    __tablename__ = "simulation_scenarios"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(100))
    subject_ids_json: Mapped[str] = mapped_column(Text)
    result_json: Mapped[str] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utc_now)


class Setting(Base):
    __tablename__ = "settings"

    key: Mapped[str] = mapped_column(String(80), primary_key=True)
    value: Mapped[str] = mapped_column(Text)
