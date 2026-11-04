"use client";

import { useEffect, useState } from "react";
import type { FormEvent } from "react";

type Health = {
  status: string;
  database: string;
};

type Submission = {
  id: number;
  name: string;
  favorite_pet: string;
  created_at: string;
};

export default function Home() {
  const [health, setHealth] = useState<Health | null>(null);
  const [healthError, setHealthError] = useState<string | null>(null);
  const [submissions, setSubmissions] = useState<Submission[]>([]);
  const [name, setName] = useState("");
  const [favoritePet, setFavoritePet] = useState("");
  const [isLoadingSubmissions, setIsLoadingSubmissions] = useState(true);
  const [isSaving, setIsSaving] = useState(false);
  const [formError, setFormError] = useState<string | null>(null);
  const [savedMessage, setSavedMessage] = useState<string | null>(null);

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
        setHealthError(
          cause instanceof Error ? cause.message : "API is unavailable",
        );
      });

    fetch("/api/submissions")
      .then(async (response) => {
        if (!response.ok) {
          throw new Error(`Could not load entries (HTTP ${response.status})`);
        }
        return (await response.json()) as Submission[];
      })
      .then(setSubmissions)
      .catch((cause: unknown) => {
        setFormError(
          cause instanceof Error ? cause.message : "Could not load entries",
        );
      })
      .finally(() => setIsLoadingSubmissions(false));
  }, []);

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setIsSaving(true);
    setFormError(null);
    setSavedMessage(null);

    try {
      const response = await fetch("/api/submissions", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ name, favorite_pet: favoritePet }),
      });
      if (!response.ok) {
        const body = (await response.json()) as {
          detail?: string | Array<{ msg?: string }>;
        };
        const detail =
          typeof body.detail === "string"
            ? body.detail
            : body.detail
                ?.map((error) => error.msg)
                .filter((message): message is string => Boolean(message))
                .join("; ");
        throw new Error(detail || `Could not save entry (HTTP ${response.status})`);
      }

      const submission = (await response.json()) as Submission;
      setSubmissions((current) => [submission, ...current]);
      setName("");
      setFavoritePet("");
      setSavedMessage("Your entry was saved.");
    } catch (cause: unknown) {
      setFormError(cause instanceof Error ? cause.message : "Could not save entry");
    } finally {
      setIsSaving(false);
    }
  }

  return (
    <main className="card">
      <p className="eyebrow">EC2 · Docker Compose</p>
      <h1>Tell us about your favorite pet</h1>
      <p className="description">
        Share your name and favorite pet. Each entry is saved in the database.
      </p>

      <form className="submission-form" onSubmit={handleSubmit}>
        <label htmlFor="name">Your name</label>
        <input
          autoComplete="name"
          id="name"
          maxLength={100}
          onChange={(event) => setName(event.target.value)}
          required
          value={name}
        />

        <label htmlFor="favorite-pet">Favorite pet</label>
        <input
          id="favorite-pet"
          maxLength={100}
          onChange={(event) => setFavoritePet(event.target.value)}
          placeholder="For example, cat or dog"
          required
          value={favoritePet}
        />

        <button disabled={isSaving} type="submit">
          {isSaving ? "Saving…" : "Save entry"}
        </button>
      </form>

      <p aria-live="polite" className={formError ? "failure message" : "success message"}>
        {formError ?? savedMessage}
      </p>

      <section aria-labelledby="entries-heading" className="entries">
        <h2 id="entries-heading">Saved entries</h2>
        {isLoadingSubmissions ? (
          <p>Loading entries…</p>
        ) : submissions.length === 0 ? (
          <p>No entries yet. Be the first to share!</p>
        ) : (
          <ul>
            {submissions.map((submission) => (
              <li key={submission.id}>
                <strong>{submission.name}</strong>
                <span>Favorite pet: {submission.favorite_pet}</span>
                <time dateTime={submission.created_at}>
                  {new Date(submission.created_at).toLocaleString()}
                </time>
              </li>
            ))}
          </ul>
        )}
      </section>

      <section aria-live="polite" className="health">
        <strong>API and database</strong>
        {health ? (
          <span className="success">
            {health.status} · database {health.database}
          </span>
        ) : healthError ? (
          <span className="failure">{healthError}</span>
        ) : (
          <span>Checking connection…</span>
        )}
      </section>
    </main>
  );
}
