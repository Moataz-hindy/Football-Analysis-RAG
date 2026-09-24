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
    from src.api.routes import router
    router_routes = {r.path for r in router.routes}
    assert "/health" in router_routes
    assert "/" in router_routes
    assert "/discussions" in router_routes
    assert "/topics" in router_routes

    app_mounts = {r.path for r in app.routes if hasattr(r, "path")}
    assert "/app" in app_mounts

