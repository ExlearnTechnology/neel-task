"use client";

import { useEffect, useState } from "react";

type Health = {
  status: string;
  database: string;
};

export default function Home() {
  const [health, setHealth] = useState<Health | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    fetch("/api/health")
      .then(async (response) => {
        if (!response.ok) {
          throw new Error(`API returned HTTP ${response.status}`);
        }
        return (await response.json()) as Health;
      })
      .then(setHealth)
      .catch((cause: unknown) => {
        setError(cause instanceof Error ? cause.message : "API is unavailable");
      });
  }, []);

  return (
    <main className="card">
      <p className="eyebrow">EC2 · Docker Compose</p>
      <h1>Deployment is running</h1>
      <p className="description">
        A Next.js frontend, FastAPI backend, and PostgreSQL database running on
        one EC2 virtual machine.
      </p>
      <section aria-live="polite" className="health">
        <strong>API and database</strong>
        {health ? (
          <span className="success">
            {health.status} · database {health.database}
          </span>
        ) : error ? (
          <span className="failure">{error}</span>
        ) : (
          <span>Checking connection…</span>
        )}
      </section>
    </main>
  );
}
