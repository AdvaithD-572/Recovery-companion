"""Station-wide identity and audit records, separate from clinical permissions."""
from datetime import datetime, timezone
from uuid import uuid4

from sqlalchemy import Column, DateTime, ForeignKey, Index, String, text
from app.core.database import Base, GUID


def utcnow():
    return datetime.now(timezone.utc)


class Administrator(Base):
    __tablename__ = "care_administrators"
    id = Column(GUID(), primary_key=True, default=uuid4)
    email = Column(String(200), nullable=False, unique=True)
    hashed_password = Column(String(200), nullable=False)


class Clinic(Base):
    __tablename__ = "care_clinics"
    id = Column(GUID(), primary_key=True, default=uuid4)
    scope = Column(String, nullable=False, unique=True)
    name = Column(String, nullable=False)
    deleted_at = Column(DateTime(timezone=True))
    __table_args__ = (Index("uq_active_clinic_name", name, unique=True,
                            sqlite_where=text("deleted_at IS NULL"), postgresql_where=text("deleted_at IS NULL")),)


class ClosedProfile(Base):
    __tablename__ = "care_closed_profiles"
    patient = Column(GUID(), ForeignKey("patients.id"), primary_key=True)
    closed_at = Column(DateTime(timezone=True), nullable=False, default=utcnow)


class DirectoryAudit(Base):
    __tablename__ = "care_directory_audit"
    id = Column(GUID(), primary_key=True, default=uuid4)
    at = Column(DateTime(timezone=True), nullable=False, default=utcnow)
    actor = Column(GUID(), nullable=False)
    action = Column(String(50), nullable=False)
    target = Column(GUID())
