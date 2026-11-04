from unittest.mock import patch

import psycopg
from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def test_health_returns_ok_when_database_is_available(monkeypatch):
    class Connection:
        def __enter__(self):
            return self

        def __exit__(self, *_):
            return False

        def execute(self, query):
            assert query == "SELECT 1"

    monkeypatch.setenv("DATABASE_URL", "postgresql://test")
    with patch("app.main.psycopg.connect", return_value=Connection()):
        response = client.get("/api/health")

    assert response.status_code == 200
    assert response.json() == {"status": "ok", "database": "connected"}


def test_health_returns_service_unavailable_when_database_is_down(monkeypatch):
    monkeypatch.setenv("DATABASE_URL", "postgresql://test")
    with patch("app.main.psycopg.connect", side_effect=psycopg.OperationalError):
        response = client.get("/api/health")

    assert response.status_code == 503
    assert response.json() == {"detail": "Database is unavailable"}
