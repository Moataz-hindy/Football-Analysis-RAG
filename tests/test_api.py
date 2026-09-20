"""Unit and integration tests for FastAPI backend routes (Week 5 P1)."""

import pytest
from fastapi.testclient import TestClient

from src.api.main import app


@pytest.fixture(scope="module")
def client():
    """Create a test client with app lifespan context."""
    with TestClient(app) as test_client:
        yield test_client


def test_health_check(client: TestClient):
    """GET /health should return 200 {"status": "ok"}."""
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_get_topics(client: TestClient):
    """GET /topics should return 200 with list of curated topics."""
    response = client.get("/topics")
    assert response.status_code == 200
    data = response.json()
    assert "topics" in data
    assert len(data["topics"]) > 0
    first_topic = data["topics"][0]
    assert "id" in first_topic
    assert "label" in first_topic
    assert "description" in first_topic


def test_list_discussions(client: TestClient):
    """GET /discussions should return 200 with list of saved discussions."""
    response = client.get("/discussions")
    assert response.status_code == 200
    data = response.json()
    assert "discussions" in data
    assert isinstance(data["discussions"], list)
    if data["discussions"]:
        item = data["discussions"][0]
        assert "discussion_id" in item
        assert "topic" in item
        assert "num_agents" in item
        assert "num_rounds" in item
        assert "num_messages" in item


def test_get_discussion_detail_success(client: TestClient):
    """GET /discussions/{id} should return 200 with full discussion structure."""
    response = client.get("/discussions/manual-demo-001")
    assert response.status_code == 200
    data = response.json()
    assert data["discussion_id"] == "manual-demo-001"
    assert "topic" in data
    assert "agents" in data
    assert "messages" in data
    assert len(data["messages"]) == 2
    assert "graph" in data


def test_get_discussion_detail_not_found(client: TestClient):
    """GET /discussions/{nonexistent} should return 404."""
    response = client.get("/discussions/nonexistent-id-999999")
    assert response.status_code == 404
    data = response.json()
    assert "error" in data or "detail" in data


def test_start_discussion(client: TestClient):
    """POST /discussions should return 202 Accepted with status 'queued'."""
    payload = {
        "topic": "Tactical analysis of high-press schemes",
        "num_rounds": 3,
    }
    response = client.post("/discussions", json=payload)
    assert response.status_code == 202
    data = response.json()
    assert "discussion_id" in data
    assert data["status"] == "queued"
    assert "message" in data


def test_start_discussion_validation_error(client: TestClient):
    """POST /discussions with invalid num_rounds should return 422."""
    payload = {
        "topic": "Invalid rounds test",
        "num_rounds": 99,  # max is 10
    }
    response = client.post("/discussions", json=payload)
    assert response.status_code == 422


def test_get_discussion_status_completed(client: TestClient):
    """GET /discussions/{id}/status for existing discussion should return 'completed'."""
    response = client.get("/discussions/manual-demo-001/status")
    assert response.status_code == 200
    data = response.json()
    assert data["discussion_id"] == "manual-demo-001"
    assert data["status"] == "completed"


def test_get_discussion_status_not_found(client: TestClient):
    """GET /discussions/{id}/status for missing discussion should return 'not_found'."""
    response = client.get("/discussions/nonexistent-id-999999/status")
    assert response.status_code == 200
    data = response.json()
    assert data["discussion_id"] == "nonexistent-id-999999"
    assert data["status"] == "not_found"


def test_get_discussion_analytics(client: TestClient):
    """GET /discussions/{id}/analytics should compute or retrieve analytics."""
    response = client.get("/discussions/manual-demo-001/analytics")
    assert response.status_code == 200
    data = response.json()
    assert data["discussion_id"] == "manual-demo-001"
    assert "opinion_trajectories" in data
    assert "agreement" in data
    assert "influence" in data
    assert "sentiment" in data
    assert "interaction_graph" in data
    assert "cached" in data


def test_openapi_schema_contains_all_endpoints(client: TestClient):
    """OpenAPI schema should document all 7 endpoints."""
    response = client.get("/openapi.json")
    assert response.status_code == 200
    paths = response.json().get("paths", {})

    expected_endpoints = [
        "/health",
        "/topics",
        "/discussions",
        "/discussions/{discussion_id}",
        "/discussions/{discussion_id}/status",
        "/discussions/{discussion_id}/analytics",
    ]
    for endpoint in expected_endpoints:
        assert endpoint in paths, f"Missing endpoint in OpenAPI docs: {endpoint}"


def test_cors_headers(client: TestClient):
    """CORS headers should be present for allowed origin."""
    headers = {
        "Origin": "http://localhost:3000",
        "Access-Control-Request-Method": "GET",
    }
    response = client.options("/health", headers=headers)
    assert response.status_code == 200
    assert response.headers.get("access-control-allow-origin") == "http://localhost:3000"
