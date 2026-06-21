"use client";

import { Play, ShieldCheck } from "lucide-react";
import { useState } from "react";
import type { PaperSessionRun } from "../lib/backend";
import { formatDateTime } from "./format";

const PAPER_CATEGORY = "tennis";
const PAPER_MAX_RESULTS = 100;

export function PaperSessionPanel({ readOnly = false }: { readOnly?: boolean }) {
  const [run, setRun] = useState<PaperSessionRun | null>(null);
  const [pending, setPending] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function startPaperSession() {
    if (readOnly) return;
    setPending(true);
    setError(null);
    try {
      const response = await fetch("/api/backend/api/paper-session/run", {
        method: "POST",
        cache: "no-store",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify({
          category: PAPER_CATEGORY,
          max_results: PAPER_MAX_RESULTS,
        }),
      });
      const payload = (await response.json()) as PaperSessionRun | { error?: string };
      if (!response.ok) {
        throw new Error("error" in payload && payload.error ? payload.error : "Paper session request failed.");
      }
      setRun(payload as PaperSessionRun);
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : "Paper session request failed.");
    } finally {
      setPending(false);
    }
  }

  const fillCount = run?.summary.paper_fills_created ?? 0;
  const ok = run?.status === "completed" && fillCount > 0;
  const statusLabel = run
    ? `${run.status}${run.summary.paper_fills_created !== undefined ? ` / ${fillCount} fills` : ""}`
    : "Ready";

  return (
    <section className="panel">
      <div className="panel-heading">
        <div>
          <h2>Paper Session</h2>
          <p>
            {run
              ? `${run.category} / ${run.max_results} finished ${formatDateTime(run.finished_at, true)}`
              : readOnly
                ? "Public proof view. Paper-session controls are hidden."
                : `Run one bounded ${PAPER_CATEGORY} paper session on the backend. No live order endpoint exists.`}
          </p>
        </div>
        {readOnly ? (
          <span className="pill good">Read-only</span>
        ) : (
          <button className="icon-button" type="button" onClick={startPaperSession} disabled={pending}>
            <Play size={16} />
            <span>{pending ? "Running" : `Run ${PAPER_CATEGORY} ${PAPER_MAX_RESULTS}`}</span>
          </button>
        )}
      </div>

      <div className="live-odds-strip">
        <div>
          <ShieldCheck size={18} />
          <span>
            {run?.summary.strategy ??
              "Token-protected paper-only run. The backend script refuses live-enabled environments."}
          </span>
        </div>
        <span className={ok ? "decision-badge accepted" : "decision-badge rejected"}>{statusLabel}</span>
        {run?.summary.top_rejections ? (
          <span className="secondary-cell">{run.summary.top_rejections}</span>
        ) : null}
      </div>

      {error ? <div className="empty-state">{error}</div> : null}
      {run?.stderr ? <div className="empty-state">{run.stderr}</div> : null}
      {run && !run.stderr ? (
        <div className="empty-state">
          Snapshots {run.summary.snapshots_collected ?? 0}, proposals {run.summary.proposals_created ?? 0}, fills{" "}
          {fillCount}. Journal: {run.summary.journal_path ?? "n/a"}
        </div>
      ) : null}
    </section>
  );
}
