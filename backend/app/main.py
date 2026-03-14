"""FastAPI application entry point."""

import json
import uuid
import re

import boto3
from botocore.exceptions import ClientError
from fastapi import FastAPI, Depends, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session

from app.config import settings
from app.database import Base, engine, get_db
from app.models import AggregationJob, JobStatus
from app.schemas import JobCreate, JobResponse, JobStatusResponse, VALID_SOURCES
from workers.tasks import run_aggregation_pipeline

# Create database tables
Base.metadata.create_all(bind=engine)

app = FastAPI(title="Async Data Aggregator API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/health")
def health():
    """Health check endpoint."""
    return {"status": "ok"}


def _validate_sources(sources: list[str]) -> None:
    """Validate that all sources are allowed."""
    invalid = [s for s in sources if s not in VALID_SOURCES]
    if invalid:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid sources: {invalid}. Allowed: {list(VALID_SOURCES)}",
        )


@app.post("/api/jobs", response_model=JobResponse)
def create_job(job_in: JobCreate, db: Session = Depends(get_db)):
    """Create a new aggregation job and trigger the pipeline."""
    _validate_sources(job_in.sources)

    job_id = str(uuid.uuid4())
    job = AggregationJob(
        id=job_id,
        status=JobStatus.PENDING,
        sources=job_in.sources,
        parameters=job_in.parameters,
    )
    db.add(job)
    db.commit()
    db.refresh(job)

    run_aggregation_pipeline.delay(job_id, job_in.sources, job_in.parameters)

    return job


@app.get("/api/jobs/{job_id}", response_model=JobResponse)
def get_job(job_id: str, db: Session = Depends(get_db)):
    """Get a job by ID."""
    job = db.query(AggregationJob).filter(AggregationJob.id == job_id).first()
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    return job


@app.get("/api/jobs", response_model=list[JobResponse])
def list_jobs(db: Session = Depends(get_db), limit: int = 20):
    """List jobs ordered by created_at descending."""
    jobs = (
        db.query(AggregationJob)
        .order_by(AggregationJob.created_at.desc())
        .limit(limit)
        .all()
    )
    return jobs


def _fetch_json_from_s3(result_url: str) -> dict:
    """Fetch JSON content from S3 given an s3:// URL."""
    match = re.match(r"s3://([^/]+)/(.+)", result_url)
    if not match:
        raise HTTPException(status_code=500, detail="Invalid result URL format")

    bucket, key = match.group(1), match.group(2)
    s3 = boto3.client(
        "s3",
        aws_access_key_id=settings.AWS_ACCESS_KEY_ID or None,
        aws_secret_access_key=settings.AWS_SECRET_ACCESS_KEY or None,
        region_name=settings.AWS_REGION,
    )

    try:
        resp = s3.get_object(Bucket=bucket, Key=key)
        body = resp["Body"].read().decode("utf-8")
        return json.loads(body)
    except ClientError as e:
        raise HTTPException(status_code=404, detail=f"Result not found: {e}") from e


@app.get("/api/jobs/{job_id}/result")
def get_job_result(job_id: str, db: Session = Depends(get_db)):
    """Fetch the aggregation result JSON from S3."""
    job = db.query(AggregationJob).filter(AggregationJob.id == job_id).first()
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    if job.status != JobStatus.COMPLETED:
        raise HTTPException(
            status_code=400,
            detail=f"Job not completed (status: {job.status.value})",
        )
    if not job.result_url:
        raise HTTPException(status_code=404, detail="No result URL available")

    return _fetch_json_from_s3(job.result_url)
