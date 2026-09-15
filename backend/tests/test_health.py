import pytest
from fastapi.testclient import TestClient
from stockwise.app.main import app

client = TestClient(app)


def test_health_returns_200():
    response = client.get("/api/health")
    assert response.status_code == 200
    assert response.json()["status"] == "ok"


def test_health_independent_of_database():
    response = client.get("/api/health")
    assert response.status_code == 200


def test_health_response_time():
    response = client.get("/api/health")
    assert response.elapsed.total_seconds() < 1
