import os
from datetime import datetime

import psycopg
from fastapi import FastAPI, HTTPException, status
from pydantic import BaseModel, Field, field_validator

app = FastAPI(title="EC2 Compose Reference API")


class SubmissionCreate(BaseModel):
    name: str = Field(min_length=1, max_length=100)
    favorite_pet: str = Field(min_length=1, max_length=100)

    @field_validator("name", "favorite_pet")
    @classmethod
    def strip_and_validate(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("This field cannot be blank")
        return value


class Submission(BaseModel):
    id: int
    name: str
    favorite_pet: str
    created_at: datetime


def get_database_url() -> str:
    database_url = os.environ.get("DATABASE_URL")
    if not database_url:
        raise HTTPException(status_code=503, detail="Database is not configured")
    return database_url


def ensure_submissions_table(connection: psycopg.Connection) -> None:
    connection.execute(
        """
        CREATE TABLE IF NOT EXISTS submissions (
            id BIGSERIAL PRIMARY KEY,
            name VARCHAR(100) NOT NULL,
            favorite_pet VARCHAR(100) NOT NULL,
            created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
        )
        """
    )


@app.get("/api/health")
def health() -> dict[str, str]:
    try:
        with psycopg.connect(get_database_url()) as connection:
            connection.execute("SELECT 1")
    except HTTPException:
        raise
    except psycopg.Error as error:
        raise HTTPException(status_code=503, detail="Database is unavailable") from error

    return {"status": "ok", "database": "connected"}


@app.post(
    "/api/submissions",
    response_model=Submission,
    status_code=status.HTTP_201_CREATED,
)
def create_submission(submission: SubmissionCreate) -> Submission:
    try:
        with psycopg.connect(get_database_url()) as connection:
            ensure_submissions_table(connection)
            row = connection.execute(
                """
                INSERT INTO submissions (name, favorite_pet)
                VALUES (%s, %s)
                RETURNING id, name, favorite_pet, created_at
                """,
                (submission.name, submission.favorite_pet),
            ).fetchone()
    except HTTPException:
        raise
    except psycopg.Error as error:
        raise HTTPException(status_code=503, detail="Database is unavailable") from error

    return Submission(
        id=row[0],
        name=row[1],
        favorite_pet=row[2],
        created_at=row[3],
    )


@app.get("/api/submissions", response_model=list[Submission])
def list_submissions() -> list[Submission]:
    try:
        with psycopg.connect(get_database_url()) as connection:
            ensure_submissions_table(connection)
            rows = connection.execute(
                """
                SELECT id, name, favorite_pet, created_at
                FROM submissions
                ORDER BY created_at DESC, id DESC
                """
            ).fetchall()
    except HTTPException:
        raise
    except psycopg.Error as error:
        raise HTTPException(status_code=503, detail="Database is unavailable") from error

    return [
        Submission(id=row[0], name=row[1], favorite_pet=row[2], created_at=row[3])
        for row in rows
    ]
