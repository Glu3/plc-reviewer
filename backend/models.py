# backend/models.py
from sqlalchemy import Column, String, Integer, Boolean, Text, DateTime, JSON
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