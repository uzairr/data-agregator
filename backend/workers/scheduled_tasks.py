"""Scheduled tasks for automatic data refresh and cleanup."""

from datetime import datetime, timedelta, timezone
from celery import chain
from sqlalchemy import and_

from app.config import settings
from app.database import SessionLocal
from app.models import AggregationJob, JobStatus
from workers.celery_app import celery_app
from workers.tasks import run_aggregation_pipeline, FETCHER_MAP


@celery_app.task
def refresh_recent_jobs(minutes: int = 5):
    """
    Automatically refresh jobs created in the last N minutes.
    This demonstrates async recurring tasks - data updates automatically!
    """
    db = SessionLocal()
    try:
        # Find jobs from the last N minutes
        cutoff_time = datetime.now(timezone.utc) - timedelta(minutes=minutes)
        recent_jobs = db.query(AggregationJob).filter(
            AggregationJob.created_at >= cutoff_time
        ).all()
        
        print(f"🔄 Auto-refreshing {len(recent_jobs)} recent jobs...")
        
        refreshed_count = 0
        for job in recent_jobs:
            # Only refresh completed or failed jobs (not pending/processing)
            if job.status in [JobStatus.COMPLETED, JobStatus.FAILED]:
                print(f"  → Refreshing job {job.id[:8]}...")
                # Create a new job with same parameters (or re-run existing)
                run_aggregation_pipeline.delay(job.id, job.sources, job.parameters)
                refreshed_count += 1
        
        return {
            "task": "refresh_recent_jobs",
            "minutes": minutes,
            "jobs_found": len(recent_jobs),
            "jobs_refreshed": refreshed_count
        }
    finally:
        db.close()


@celery_app.task
def cleanup_old_jobs(hours: int = 24):
    """Delete old jobs to keep database clean (optional)."""
    db = SessionLocal()
    try:
        # Delete jobs older than N hours
        cutoff_time = datetime.now(timezone.utc) - timedelta(hours=hours)
        old_jobs = db.query(AggregationJob).filter(
            AggregationJob.created_at < cutoff_time
        ).delete(synchronize_session=False)
        db.commit()
        
        print(f"🧹 Cleaned up {old_jobs} old jobs (> {hours} hours old)")
        return {
            "task": "cleanup_old_jobs",
            "hours": hours,
            "deleted_count": old_jobs
        }
    finally:
        db.close()


@celery_app.task
def demonstrate_async_progress(job_id: str):
    """
    Demo task that shows async progress by updating status at intervals.
    This helps visualize the async nature to clients.
    """
    from time import sleep
    
    db = SessionLocal()
    try:
        job = db.query(AggregationJob).filter(AggregationJob.id == job_id).first()
        if not job:
            return
        
        # Update status to show progress
        for i in range(1, 4):
            sleep(2)  # Simulate work
            # You could add a custom field to show progress percentage
            print(f"⏳ Job {job_id[:8]}: Step {i}/3 completed...")
        
        return f"Job {job_id} processed asynchronously"
    finally:
        db.close()


@celery_app.task
def check_api_health():
    """Monitor API key health and report status."""
    import httpx
    
    status_report = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "apis": {}
    }
    
    # Check OpenWeatherMap
    if settings.OPENWEATHER_API_KEY:
        try:
            resp = httpx.get(
                "https://api.openweathermap.org/data/2.5/weather",
                params={"q": "London", "appid": settings.OPENWEATHER_API_KEY},
                timeout=5
            )
            status_report["apis"]["openweather"] = {
                "status": "ok" if resp.status_code == 200 else "error",
                "code": resp.status_code
            }
        except Exception as e:
            status_report["apis"]["openweather"] = {
                "status": "error",
                "error": str(e)
            }
    else:
        status_report["apis"]["openweather"] = {"status": "not_configured"}
    
    # Check NewsAPI
    if settings.NEWSAPI_API_KEY:
        try:
            resp = httpx.get(
                "https://newsapi.org/v2/everything",
                params={"q": "tech", "apiKey": settings.NEWSAPI_API_KEY},
                timeout=5
            )
            status_report["apis"]["newsapi"] = {
                "status": "ok" if resp.status_code == 200 else "error",
                "code": resp.status_code
            }
        except Exception as e:
            status_report["apis"]["newsapi"] = {
                "status": "error",
                "error": str(e)
            }
    else:
        status_report["apis"]["newsapi"] = {"status": "not_configured"}
    
    print(f"📊 API Health Check: {status_report}")
    return status_report