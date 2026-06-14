"use client";

import { useState } from "react";
import { api, Application, ApplicationStatus } from "@/lib/api";

const STATUSES: ApplicationStatus[] = [
  "saved",
  "applied",
  "interviewing",
  "offer",
  "rejected",
  "withdrawn",
];

const LABEL: Record<ApplicationStatus, string> = {
  saved: "Saved",
  applied: "Applied",
  interviewing: "Interviewing",
  offer: "Offer",
  rejected: "Rejected",
  withdrawn: "Withdrawn",
};

export default function Applications({
  applications,
  onChanged,
  onStatus,
}: {
  applications: Application[];
  onChanged: () => void;
  onStatus: (msg: string) => void;
}) {
  const [open, setOpen] = useState<number | null>(null);

  async function setStatus(app: Application, status: ApplicationStatus) {
    try {
      await api.updateApplication(app.id, { status });
      onChanged();
    } catch (e) {
      onStatus((e as Error).message);
    }
  }

  async function remove(app: Application) {
    try {
      await api.deleteApplication(app.id);
      onChanged();
    } catch (e) {
      onStatus((e as Error).message);
    }
  }

  if (applications.length === 0) {
    return (
      <p className="muted">
        No applications yet. Save a job or hit 🤖 Auto-apply to start tracking.
      </p>
    );
  }

  const grouped = STATUSES.map((s) => ({
    status: s,
    items: applications.filter((a) => a.status === s),
  }));

  return (
    <div className="board">
      {grouped.map((col) => (
        <div className="board-col" key={col.status}>
          <div className="board-col-head">
            <span className={`badge status-${col.status}`}>{LABEL[col.status]}</span>
            <span className="muted">{col.items.length}</span>
          </div>
          {col.items.map((app) => (
            <div className="app-card" key={app.id}>
              <strong>{app.job.title}</strong>
              <div className="muted">{app.job.company || "—"}</div>
              <div className="row" style={{ marginTop: 8, gap: 6 }}>
                <select
                  value={app.status}
                  onChange={(e) =>
                    setStatus(app, e.target.value as ApplicationStatus)
                  }
                  style={{ width: "auto", marginTop: 0, flex: 1 }}
                >
                  {STATUSES.map((s) => (
                    <option key={s} value={s}>
                      {LABEL[s]}
                    </option>
                  ))}
                </select>
                <button
                  className="btn secondary"
                  onClick={() => remove(app)}
                  title="Stop tracking"
                  style={{ padding: "6px 9px" }}
                >
                  ✕
                </button>
              </div>
              {(app.tailored_resume || app.cover_letter) && (
                <button
                  className="link-btn"
                  onClick={() => setOpen(open === app.id ? null : app.id)}
                >
                  {open === app.id ? "Hide" : "View"} AI materials
                </button>
              )}
              {open === app.id && (
                <div style={{ marginTop: 6 }}>
                  {app.cover_letter && (
                    <>
                      <div className="muted">Cover letter</div>
                      <pre>{app.cover_letter}</pre>
                    </>
                  )}
                  {app.tailored_resume && (
                    <>
                      <div className="muted">Tailored resume</div>
                      <pre>{app.tailored_resume}</pre>
                    </>
                  )}
                </div>
              )}
            </div>
          ))}
        </div>
      ))}
    </div>
  );
}
