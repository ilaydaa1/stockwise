import pytest
from unittest.mock import patch, MagicMock
from fastapi.testclient import TestClient
from sqlalchemy.exc import OperationalError
from stockwise.app.main import app

client = TestClient(app)


def test_ready_returns_200_when_db_connected():
    mock_session = MagicMock()
    mock_session.execute.return_value = None
    mock_session.commit.return_value = None
    mock_session.close.return_value = None
    with patch('stockwise.app.api.ready.SessionLocal', return_value=mock_session):
        response = client.get("/api/ready")
    assert response.status_code == 200
    assert response.json()["status"] == "ready"


def test_ready_returns_503_when_db_unavailable():
    mock_session = MagicMock()
    mock_session.execute.side_effect = OperationalError("connection failed", None, None)
    with patch('stockwise.app.api.ready.SessionLocal', return_value=mock_session):
        response = client.get("/api/ready")
    assert response.status_code == 503
    assert "Service unavailable" in response.json()["detail"]
