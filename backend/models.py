# backend/models.py
from sqlalchemy import Column, String, Integer, Boolean, Text, DateTime, JSON, ForeignKey
from sqlalchemy.dialects.postgresql import UUID
from database import Base
from datetime import datetime
import uuid

class ReferenceRoutine(Base):
    __tablename__ = "reference_routines"

    id             = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    reference_id   = Column(String(100), unique=True, nullable=False)
    routine_name   = Column(String(100), nullable=False)
    version        = Column(Integer, default=1)
    rungs          = Column(JSON, nullable=False)   # list of rung objects
    raw_xml        = Column(Text, nullable=False)
    description    = Column(Text)
    created_at     = Column(DateTime, default=datetime.utcnow)
    is_active      = Column(Boolean, default=True)


class Review(Base):
    __tablename__ = "reviews"

    id             = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    filename       = Column(String(255), nullable=False)
    status         = Column(String(50), default="pending")
    created_at     = Column(DateTime, default=datetime.utcnow)


class Finding(Base):
    __tablename__ = "findings"

    id             = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    review_id      = Column(UUID(as_uuid=True), nullable=False)
    rule_id        = Column(String(50), nullable=False)
    severity       = Column(String(20), nullable=False)
    program        = Column(String(255), nullable=False)
    location       = Column(String(500), nullable=False)
    message        = Column(Text, nullable=False)
    evidence       = Column(Text)
    fix            = Column(Text)
    created_at     = Column(DateTime, default=datetime.utcnow)

class Project(Base):
    __tablename__ = "projects"

    id             = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name           = Column(String(255), nullable=False)
    version_label  = Column(String(100), nullable=False, default="v1")
    zip_filename   = Column(String(255), nullable=False)
    program_count  = Column(Integer, default=0)
    uploaded_at    = Column(DateTime, default=datetime.utcnow)


class Program(Base):
    __tablename__ = "programs"

    id               = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    project_id       = Column(UUID(as_uuid=True), ForeignKey("projects.id"), nullable=False)
    program_name     = Column(String(255), nullable=False)
    unit             = Column(String(50))    # AI1, VC1, SB1, PD1, TP1
    program_type     = Column(String(10))    # PH, OP, UP
    number           = Column(String(20))    # 1010, 1020 etc
    description_name = Column(String(255))   # Purge, Prep etc
    has_prestate     = Column(Boolean, default=False)
    prestate_rungs   = Column(JSON)          # list of {number, text}
    tags             = Column(JSON)          # list of {name, value, data_type}
    created_at       = Column(DateTime, default=datetime.utcnow)

class Routine(Base):
    __tablename__ = "routines"

    id           = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    program_id   = Column(UUID(as_uuid=True), ForeignKey("programs.id"), nullable=False)
    routine_name = Column(String(255), nullable=False)
    routine_type = Column(String(10))   # RLL, ST, FBD
    rung_count   = Column(Integer, default=0)
    rungs        = Column(JSON, nullable=False)
    created_at   = Column(DateTime, default=datetime.utcnow)        