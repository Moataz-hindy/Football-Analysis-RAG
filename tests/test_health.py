"""Unit tests for FastAPI health check and monitoring endpoints.

Fulfills Week 5 Section 38, 39, and 48 testing requirements.
"""

import pytest
from fastapi.testclient import TestClient

from src.api.main import app


@pytest.fixture(scope="module")
def client():
    """Create a test client with app lifespan context."""
    with TestClient(app) as test_client:
        yield test_client


def test_health_check_returns_200_ok(client: TestClient):
    """Verify /health endpoint satisfies Section 39 acceptance criteria."""
    response = client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ok"


def test_cors_middleware_configured():
    """Verify CORS middleware is properly mounted on FastAPI app."""
    middleware_classes = [m.cls.__name__ for m in app.user_middleware]
    assert "CORSMiddleware" in middleware_classes


def test_routes_registered():
    """Verify required routes exist in the API router."""
    routes = {r.path for r in app.routes if hasattr(r, "path")}
    assert "/health" in routes
    assert "/" in routes
    assert "/docs" in routes
    assert "/discussions" in routes
    assert "/topics" in routes
    assert "/app" in routes
