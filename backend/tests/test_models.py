"""Tests for database models."""

from app.models import AggregationJob, JobStatus


def test_create_job_model(db):
    job = AggregationJob(
        id="test-123",
        status=JobStatus.PENDING,
        sources=["weather", "news"],
        parameters={"city": "London", "topic": "tech"},
    )
    db.add(job)
    db.commit()

    loaded = db.query(AggregationJob).filter_by(id="test-123").first()
    assert loaded.sources == ["weather", "news"]
    assert loaded.parameters["city"] == "London"
    assert loaded.status == JobStatus.PENDING


def test_update_job_status(db):
    job = AggregationJob(
        id="test-456",
        status=JobStatus.PENDING,
        sources=["weather"],
        parameters={},
    )
    db.add(job)
    db.commit()

    job.status = JobStatus.COMPLETED
    db.commit()

    loaded = db.query(AggregationJob).filter_by(id="test-456").first()
    assert loaded.status == JobStatus.COMPLETED
