import pytest
from fastapi.testclient import TestClient
from stockwise.app.main import app

client = TestClient(app)


@pytest.fixture
def test_client():
    return client
