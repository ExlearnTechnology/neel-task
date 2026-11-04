import os

import psycopg
from fastapi import FastAPI, HTTPException

app = FastAPI(title="EC2 Compose Reference API")


@app.get("/api/health")
def health() -> dict[str, str]:
    database_url = os.environ.get("DATABASE_URL")
    if not database_url:
        raise HTTPException(status_code=503, detail="Database is not configured")

    try:
        with psycopg.connect(database_url) as connection:
            connection.execute("SELECT 1")
    except psycopg.Error as error:
        raise HTTPException(status_code=503, detail="Database is unavailable") from error

    return {"status": "ok", "database": "connected"}
