"""Tests for API endpoints."""

from unittest.mock import patch


def test_health(client):
    resp = client.get("/health")
    assert resp.status_code == 200
    assert resp.json() == {"status": "ok"}


@patch("app.main.run_aggregation_pipeline")
def test_create_job(mock_task, client):
    mock_task.delay.return_value = None
    resp = client.post("/api/jobs", json={
        "sources": ["weather"],
        "parameters": {"city": "London"}
    })
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "PENDING"
    assert data["sources"] == ["weather"]
    assert data["parameters"]["city"] == "London"
    mock_task.delay.assert_called_once()


@patch("app.main.run_aggregation_pipeline")
def test_create_job_invalid_source(mock_task, client):
    resp = client.post("/api/jobs", json={
        "sources": ["invalid_source"],
        "parameters": {}
    })
    assert resp.status_code == 400


@patch("app.main.run_aggregation_pipeline")
def test_create_job_empty_sources(mock_task, client):
    resp = client.post("/api/jobs", json={
        "sources": [],
        "parameters": {}
    })
    assert resp.status_code == 422  # pydantic min_length=1


@patch("app.main.run_aggregation_pipeline")
def test_get_job(mock_task, client):
    mock_task.delay.return_value = None
    create_resp = client.post("/api/jobs", json={
        "sources": ["news"],
        "parameters": {"topic": "tech"}
    })
    job_id = create_resp.json()["id"]

    resp = client.get(f"/api/jobs/{job_id}")
    assert resp.status_code == 200
    assert resp.json()["id"] == job_id


def test_get_job_not_found(client):
    resp = client.get("/api/jobs/nonexistent-id")
    assert resp.status_code == 404


@patch("app.main.run_aggregation_pipeline")
def test_list_jobs(mock_task, client):
    mock_task.delay.return_value = None
    for src in ["weather", "news"]:
        client.post("/api/jobs", json={"sources": [src], "parameters": {}})

    resp = client.get("/api/jobs")
    assert resp.status_code == 200
    assert len(resp.json()) == 2


@patch("app.main.run_aggregation_pipeline")
def test_get_result_not_completed(mock_task, client):
    mock_task.delay.return_value = None
    create_resp = client.post("/api/jobs", json={
        "sources": ["weather"],
        "parameters": {}
    })
    job_id = create_resp.json()["id"]

    resp = client.get(f"/api/jobs/{job_id}/result")
    assert resp.status_code == 400
