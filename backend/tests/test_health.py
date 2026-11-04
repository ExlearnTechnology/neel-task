from datetime import datetime, timezone
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


class SubmissionConnection:
    def __init__(self, rows):
        self.rows = rows
        self.inserted_values = None

    def __enter__(self):
        return self

    def __exit__(self, *_):
        return False

    def execute(self, query, parameters=None):
        if "INSERT INTO submissions" in query:
            self.inserted_values = parameters
            return self
        return self

    def fetchone(self):
        return self.rows[0]

    def fetchall(self):
        return self.rows


def test_create_submission_stores_name_and_favorite_pet(monkeypatch):
    created_at = datetime(2026, 11, 4, tzinfo=timezone.utc)
    connection = SubmissionConnection([(1, "Ada", "Cat", created_at)])
    monkeypatch.setenv("DATABASE_URL", "postgresql://test")

    with patch("app.main.psycopg.connect", return_value=connection):
        response = client.post(
            "/api/submissions",
            json={"name": " Ada ", "favorite_pet": " Cat "},
        )

    assert response.status_code == 201
    assert response.json() == {
        "id": 1,
        "name": "Ada",
        "favorite_pet": "Cat",
        "created_at": "2026-11-04T00:00:00Z",
    }
    assert connection.inserted_values == ("Ada", "Cat")


def test_create_submission_rejects_blank_fields():
    response = client.post(
        "/api/submissions",
        json={"name": "   ", "favorite_pet": "Dog"},
    )

    assert response.status_code == 422


def test_list_submissions_returns_saved_entries(monkeypatch):
    created_at = datetime(2026, 11, 4, tzinfo=timezone.utc)
    connection = SubmissionConnection([(1, "Ada", "Cat", created_at)])
    monkeypatch.setenv("DATABASE_URL", "postgresql://test")

    with patch("app.main.psycopg.connect", return_value=connection):
        response = client.get("/api/submissions")

    assert response.status_code == 200
    assert response.json() == [
        {
            "id": 1,
            "name": "Ada",
            "favorite_pet": "Cat",
            "created_at": "2026-11-04T00:00:00Z",
        }
    ]
