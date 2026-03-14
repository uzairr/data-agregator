"""SQLAlchemy models."""

import enum

import json

from sqlalchemy import Column, DateTime, Enum, String, Text, TypeDecorator
from sqlalchemy.sql import func

from app.database import Base


class JSONType(TypeDecorator):
    """Store JSON as text for SQLite compatibility."""
    impl = Text
    cache_ok = True

    def process_bind_param(self, value, dialect):
        if value is not None:
            return json.dumps(value)
        return None

    def process_result_value(self, value, dialect):
        if value is not None:
            return json.loads(value)
        return None


class StringList(TypeDecorator):
    """Store a list of strings as JSON text for SQLite compatibility."""
    impl = Text
    cache_ok = True

    def process_bind_param(self, value, dialect):
        if value is not None:
            return json.dumps(value)
        return None

    def process_result_value(self, value, dialect):
        if value is not None:
            return json.loads(value)
        return None


class JobStatus(str, enum.Enum):
    """Status of an aggregation job."""

    PENDING = "PENDING"
    PROCESSING = "PROCESSING"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"


class AggregationJob(Base):
    """Model for aggregation jobs."""

    __tablename__ = "aggregation_jobs"

    id = Column(String(36), primary_key=True)
    status = Column(Enum(JobStatus), default=JobStatus.PENDING, nullable=False)
    sources = Column(StringList, nullable=False)
    parameters = Column(JSONType, nullable=False, default=dict)
    result_url = Column(String(512), nullable=True)
    error_message = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    completed_at = Column(DateTime(timezone=True), nullable=True)
