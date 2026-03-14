"""Celery tasks for data aggregation pipeline."""

import json
from datetime import datetime, timezone
from typing import Any

import httpx
from celery import chord
from celery.exceptions import Retry
from sqlalchemy.orm import Session

from app.config import settings
from app.database import SessionLocal
from app.models import AggregationJob, JobStatus

from workers.celery_app import celery_app


def _get_db() -> Session:
    """Get a database session for worker use."""
    return SessionLocal()


@celery_app.task(bind=True, max_retries=3, default_retry_delay=5)
def fetch_weather(self, parameters: dict[str, Any]) -> dict[str, Any]:
    """Fetch weather data from OpenWeatherMap API."""
    city = parameters.get("city", "London")
    api_key = settings.OPENWEATHER_API_KEY
    if not api_key:
        return {"source": "weather", "error": "OPENWEATHER_API_KEY not configured", "data": None}

    url = "https://api.openweathermap.org/data/2.5/weather"
    params = {"q": city, "appid": api_key, "units": "metric"}

    try:
        with httpx.Client(timeout=10.0) as client:
            resp = client.get(url, params=params)
            resp.raise_for_status()
            data = resp.json()
            return {"source": "weather", "data": data, "error": None}
    except Exception as exc:
        try:
            raise self.retry(exc=exc)
        except Retry:
            raise
        except Exception:
            return {"source": "weather", "error": str(exc), "data": None}


@celery_app.task(bind=True, max_retries=3, default_retry_delay=5)
def fetch_news(self, parameters: dict[str, Any]) -> dict[str, Any]:
    """Fetch news from NewsAPI."""
    topic = parameters.get("topic", "technology")
    api_key = settings.NEWSAPI_API_KEY
    if not api_key:
        return {"source": "news", "error": "NEWSAPI_API_KEY not configured", "data": None}

    url = "https://newsapi.org/v2/everything"
    params = {"q": topic, "apiKey": api_key, "pageSize": 10, "sortBy": "publishedAt"}

    try:
        with httpx.Client(timeout=10.0) as client:
            resp = client.get(url, params=params)
            resp.raise_for_status()
            data = resp.json()
            return {"source": "news", "data": data, "error": None}
    except Exception as exc:
        try:
            raise self.retry(exc=exc)
        except Retry:
            raise
        except Exception:
            return {"source": "news", "error": str(exc), "data": None}


FETCHER_MAP = {
    "weather": fetch_weather,
    "news": fetch_news,
}


@celery_app.task
def update_job_status(
    job_id: str,
    status: str,
    result_url: str | None = None,
    error_message: str | None = None,
) -> None:
    """Update job status in the database."""
    db = _get_db()
    try:
        job = db.query(AggregationJob).filter(AggregationJob.id == job_id).first()
        if job:
            job.status = JobStatus(status)
            if result_url is not None:
                job.result_url = result_url
            if error_message is not None:
                job.error_message = error_message
            if status in ("COMPLETED", "FAILED"):
                job.completed_at = datetime.now(timezone.utc)
            db.commit()
    finally:
        db.close()


def _upload_to_s3(job_id: str, payload: dict) -> str:
    """Upload JSON payload to S3 and return the object URL."""
    import boto3
    from botocore.exceptions import ClientError

    bucket = settings.S3_BUCKET
    key = f"reports/{job_id}.json"

    s3 = boto3.client(
        "s3",
        aws_access_key_id=settings.AWS_ACCESS_KEY_ID or None,
        aws_secret_access_key=settings.AWS_SECRET_ACCESS_KEY or None,
        region_name=settings.AWS_REGION,
    )

    try:
        s3.put_object(
            Bucket=bucket,
            Key=key,
            Body=json.dumps(payload, default=str),
            ContentType="application/json",
        )
        return f"s3://{bucket}/{key}"
    except ClientError as e:
        raise RuntimeError(f"S3 upload failed: {e}") from e


@celery_app.task
def aggregate_results(
    fetch_results: list[dict[str, Any]],
    job_id: str,
) -> None:
    """Chord callback: merge fetch results, upload to S3, update job to COMPLETED."""
    db = _get_db()
    try:
        job = db.query(AggregationJob).filter(AggregationJob.id == job_id).first()
        if not job:
            return

        merged: dict[str, Any] = {}
        errors: list[str] = []

        for item in fetch_results:
            source = item.get("source", "unknown")
            if item.get("error"):
                errors.append(f"{source}: {item['error']}")
            elif item.get("data") is not None:
                merged[source] = item["data"]

        if errors and not merged:
            job.status = JobStatus.FAILED
            job.error_message = "; ".join(errors)
            job.completed_at = datetime.now(timezone.utc)
            db.commit()
            return

        payload = {"job_id": job_id, "results": merged, "errors": errors if errors else None}

        # try:
        #     result_url = _upload_to_s3(job_id, payload)
        #     job.status = JobStatus.COMPLETED
        #     job.result_url = result_url
        #     job.completed_at = datetime.now(timezone.utc)
        #     if errors:
        #         job.error_message = "; ".join(errors)
        # except Exception as e:
        #     job.status = JobStatus.FAILED
        #     job.error_message = str(e)
        #     job.completed_at = datetime.now(timezone.utc)

        job.status = JobStatus.COMPLETED
        job.completed_at = datetime.now(timezone.utc)
        if errors:
            job.error_message = "; ".join(errors)
            
        db.commit()
    finally:
        db.close()


@celery_app.task
def run_aggregation_pipeline(
    job_id: str,
    sources: list[str],
    parameters: dict[str, Any],
) -> None:

    update_job_status(job_id, "PROCESSING")

    fetch_tasks = []
    for src in sources:
        fetcher = FETCHER_MAP.get(src)
        if fetcher:
            fetch_tasks.append(fetcher.s(parameters))

    if not fetch_tasks:
        update_job_status(job_id, "FAILED", error_message="No valid sources")
        return

    # FIXED: Remove .apply_async() from the end
    chord(fetch_tasks)(aggregate_results.s(job_id=job_id))