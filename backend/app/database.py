from __future__ import annotations

import os
import sqlite3
from pathlib import Path

from sqlalchemy import create_engine, event
from sqlalchemy.orm import DeclarativeBase, sessionmaker


BASE_DIR = Path(__file__).resolve().parents[2]
DATA_DIR = Path(os.getenv("HERA_DATA_DIR") or os.getenv("FARMAHUB_DATA_DIR") or BASE_DIR / "data")
DATA_DIR.mkdir(parents=True, exist_ok=True)
DATABASE_PATH = DATA_DIR / "hera.db"
LEGACY_DATABASE_PATH = Path(os.getenv("HERA_LEGACY_DATABASE", DATA_DIR / "farmahub.db"))
MIGRATION_MARKER = DATA_DIR / ".hera-migration-complete"
MIGRATION_VERSION = "FarmaHub Academico -> Hera v2\n"


def _migrate_legacy_database() -> None:
    """Migra a base antiga com a API SQLite para incorporar também o WAL."""
    if (
        MIGRATION_MARKER.exists()
        and MIGRATION_MARKER.read_text(encoding="utf-8") == MIGRATION_VERSION
    ) or not LEGACY_DATABASE_PATH.exists():
        return

    temporary_path = DATA_DIR / "hera.migration.tmp"
    temporary_path.unlink(missing_ok=True)
    source = sqlite3.connect(LEGACY_DATABASE_PATH)
    destination = sqlite3.connect(temporary_path)
    try:
        source.backup(destination)
    finally:
        destination.close()
        source.close()
    os.replace(temporary_path, DATABASE_PATH)
    MIGRATION_MARKER.write_text(MIGRATION_VERSION, encoding="utf-8")


_migrate_legacy_database()
DATABASE_URL = os.getenv("HERA_DATABASE_URL") or os.getenv("FARMAHUB_DATABASE_URL") or f"sqlite:///{DATABASE_PATH}"

engine = create_engine(
    DATABASE_URL,
    connect_args={"check_same_thread": False} if DATABASE_URL.startswith("sqlite") else {},
)


@event.listens_for(engine, "connect")
def _sqlite_foreign_keys(dbapi_connection, _connection_record):
    if DATABASE_URL.startswith("sqlite"):
        cursor = dbapi_connection.cursor()
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.execute("PRAGMA journal_mode=WAL")
        cursor.close()


SessionLocal = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)


class Base(DeclarativeBase):
    pass


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
