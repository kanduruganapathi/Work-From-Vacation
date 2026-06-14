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

function download(filename: string, text: string) {
  const blob = new Blob([text], { type: "text/plain" });
  const url = URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = url;
  a.download = filename;
  a.click();
  URL.revokeObjectURL(url);
}

const slug = (s: string) =>
  s.toLowerCase().replace(/[^a-z0-9]+/g, "-").replace(/^-|-$/g, "").slice(0, 40);

export default function Applications({
  applications,
  aiEnabled,
  onChanged,
  onStatus,
}: {
  applications: Application[];
  aiEnabled: boolean;
  onChanged: () => void;
  onStatus: (msg: string) => void;
}) {
  const [open, setOpen] = useState<number | null>(null);
  const [editing, setEditing] = useState<number | null>(null);
  const [draftResume, setDraftResume] = useState("");
  const [draftLetter, setDraftLetter] = useState("");
  const [busyId, setBusyId] = useState<number | null>(null);

  async function setStatus(app: Application, status: ApplicationStatus) {
    try {
      await api.updateApplication(app.id, { status });
      onChanged();
    } catch (e) {
      onStatus((e as Error).message);
    }
  }

  function startEdit(app: Application) {
    setEditing(app.id);
    setDraftResume(app.tailored_resume || "");
    setDraftLetter(app.cover_letter || "");
  }

  async function saveEdit(app: Application) {
    try {
      await api.updateApplication(app.id, {
        tailored_resume: draftResume,
        cover_letter: draftLetter,
      });
      setEditing(null);
      onChanged();
      onStatus("Materials saved.");
    } catch (e) {
      onStatus((e as Error).message);
    }
  }

  async function copy(text: string) {
    try {
      await navigator.clipboard.writeText(text);
      onStatus("Copied to clipboard.");
    } catch {
      onStatus("Copy failed — your browser blocked clipboard access.");
    }
  }

  async function regenerate(app: Application) {
    setBusyId(app.id);
    onStatus(`Regenerating materials for “${app.job.title}”...`);
    try {
      await api.autoApply(app.job_id);
      onChanged();
      onStatus("Materials regenerated.");
    } catch (e) {
      onStatus((e as Error).message);
    } finally {
      setBusyId(null);
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
              <div className="row" style={{ gap: 8, marginTop: 6 }}>
                {(app.tailored_resume || app.cover_letter) && (
                  <button
                    className="link-btn"
                    onClick={() => setOpen(open === app.id ? null : app.id)}
                  >
                    {open === app.id ? "Hide" : "View"} AI materials
                  </button>
                )}
                {aiEnabled && (
                  <button
                    className="link-btn"
                    onClick={() => regenerate(app)}
                    disabled={busyId === app.id}
                  >
                    ↻ Regenerate
                  </button>
                )}
              </div>

              {open === app.id && (
                <div style={{ marginTop: 8 }}>
                  {editing === app.id ? (
                    <>
                      <div className="muted">Cover letter</div>
                      <textarea
                        rows={5}
                        value={draftLetter}
                        onChange={(e) => setDraftLetter(e.target.value)}
                      />
                      <div className="muted" style={{ marginTop: 6 }}>
                        Tailored resume
                      </div>
                      <textarea
                        rows={6}
                        value={draftResume}
                        onChange={(e) => setDraftResume(e.target.value)}
                      />
                      <div className="row" style={{ marginTop: 8 }}>
                        <button className="btn" onClick={() => saveEdit(app)}>
                          Save
                        </button>
                        <button
                          className="btn secondary"
                          onClick={() => setEditing(null)}
                        >
                          Cancel
                        </button>
                      </div>
                    </>
                  ) : (
                    <>
                      {app.cover_letter && (
                        <>
                          <div className="row" style={{ justifyContent: "space-between" }}>
                            <div className="muted">Cover letter</div>
                            <div className="row" style={{ gap: 8 }}>
                              <button
                                className="link-btn"
                                onClick={() => copy(app.cover_letter!)}
                              >
                                Copy
                              </button>
                              <button
                                className="link-btn"
                                onClick={() =>
                                  download(
                                    `cover-letter-${slug(app.job.title)}.txt`,
                                    app.cover_letter!
                                  )
                                }
                              >
                                Download
                              </button>
                            </div>
                          </div>
                          <pre>{app.cover_letter}</pre>
                        </>
                      )}
                      {app.tailored_resume && (
                        <>
                          <div className="row" style={{ justifyContent: "space-between" }}>
                            <div className="muted">Tailored resume</div>
                            <div className="row" style={{ gap: 8 }}>
                              <button
                                className="link-btn"
                                onClick={() => copy(app.tailored_resume!)}
                              >
                                Copy
                              </button>
                              <button
                                className="link-btn"
                                onClick={() =>
                                  download(
                                    `resume-${slug(app.job.title)}.txt`,
                                    app.tailored_resume!
                                  )
                                }
                              >
                                Download
                              </button>
                            </div>
                          </div>
                          <pre>{app.tailored_resume}</pre>
                        </>
                      )}
                      {(app.tailored_resume || app.cover_letter) && (
                        <button className="link-btn" onClick={() => startEdit(app)}>
                          ✎ Edit materials
                        </button>
                      )}
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
