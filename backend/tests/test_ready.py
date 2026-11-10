from unittest.mock import MagicMock

from sqlalchemy.exc import OperationalError

from stockwise.app.db.session import get_db
from stockwise.app.main import app


def test_ready_returns_200_when_db_connected(client):
    response = client.get("/api/ready")

    assert response.status_code == 200
    assert response.json() == {"status": "ready", "database": "connected"}


def test_ready_returns_503_when_db_unavailable(client):
    mock_session = MagicMock()
    mock_session.execute.side_effect = OperationalError(
        "connection failed", None, None
    )

    original_override = app.dependency_overrides[get_db]
    app.dependency_overrides[get_db] = lambda: mock_session

    try:
        response = client.get("/api/ready")
    finally:
        app.dependency_overrides[get_db] = original_override

    assert response.status_code == 503
    assert response.json()["detail"] == "Service unavailable"
