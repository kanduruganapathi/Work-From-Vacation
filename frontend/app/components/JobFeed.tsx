"use client";

import { useEffect, useState } from "react";
import { api, Application, ApplicationStatus, Job } from "@/lib/api";

const TABS: { key: string; label: string; params: Record<string, string> }[] = [
  { key: "all", label: "All", params: {} },
  { key: "remote", label: "Remote", params: { remote: "true" } },
  { key: "full_time", label: "Full-time", params: { employment_type: "full_time" } },
  { key: "contract", label: "Contract", params: { employment_type: "contract" } },
  { key: "freelance", label: "Freelance", params: { employment_type: "freelance" } },
];

const STATUS_LABEL: Record<ApplicationStatus, string> = {
  saved: "Saved",
  applied: "Applied",
  interviewing: "Interviewing",
  offer: "Offer",
  rejected: "Rejected",
  withdrawn: "Withdrawn",
};

export default function JobFeed({
  aiEnabled,
  trackedByJob,
  onChanged,
  onStatus,
}: {
  aiEnabled: boolean;
  trackedByJob: Record<number, Application>;
  onChanged: () => void;
  onStatus: (msg: string) => void;
}) {
  const [tab, setTab] = useState("all");
  const [jobs, setJobs] = useState<Job[]>([]);
  const [busyId, setBusyId] = useState<number | null>(null);

  async function load(key: string) {
    setTab(key);
    const params = TABS.find((t) => t.key === key)?.params ?? {};
    setJobs(await api.listJobs({ ...params, limit: "30" }));
  }

  useEffect(() => {
    load("all").catch((e) => onStatus((e as Error).message));
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  async function save(job: Job) {
    setBusyId(job.id);
    try {
      await api.createApplication(job.id, "saved");
      onStatus(`Saved “${job.title}”.`);
      onChanged();
    } catch (e) {
      onStatus((e as Error).message);
    } finally {
      setBusyId(null);
    }
  }

  async function autoApply(job: Job) {
    setBusyId(job.id);
    onStatus(`🤖 Auto-applying to “${job.title}” — tailoring resume + cover letter...`);
    try {
      await api.autoApply(job.id);
      onStatus(`Auto-applied to “${job.title}”. Materials prepared and tracked.`);
      onChanged();
    } catch (e) {
      onStatus((e as Error).message);
    } finally {
      setBusyId(null);
    }
  }

  return (
    <>
      <div className="tabs">
        {TABS.map((t) => (
          <button
            key={t.key}
            className={`tab ${tab === t.key ? "active" : ""}`}
            onClick={() => load(t.key).catch((e) => onStatus((e as Error).message))}
          >
            {t.label}
          </button>
        ))}
      </div>

      <div className="grid">
        {jobs.map((job) => {
          const tracked = trackedByJob[job.id];
          return (
            <div className="card" key={job.id}>
              <h3>{job.title}</h3>
              <div className="muted">
                {job.company || "Unknown"} · {job.location || "—"}
              </div>
              <div style={{ marginTop: 6 }}>
                <span className={`badge type-${job.employment_type}`}>
                  {job.employment_type.replace("_", " ")}
                </span>
                {job.remote && <span className="badge remote">remote</span>}
              </div>
              <div style={{ marginTop: 8 }}>
                {job.tags.slice(0, 5).map((t) => (
                  <span className="tag" key={t}>
                    {t}
                  </span>
                ))}
              </div>
              <div className="row muted" style={{ marginTop: 8 }}>
                <span>{job.source}</span>
                {job.salary_text && <span>· {job.salary_text}</span>}
              </div>

              <div className="row" style={{ marginTop: 12 }}>
                {tracked ? (
                  <span className={`badge status-${tracked.status}`}>
                    {STATUS_LABEL[tracked.status]}
                  </span>
                ) : (
                  <>
                    <button
                      className="btn secondary"
                      onClick={() => save(job)}
                      disabled={busyId === job.id}
                    >
                      Save
                    </button>
                    <button
                      className="btn"
                      onClick={() => autoApply(job)}
                      disabled={busyId === job.id || !aiEnabled}
                      title={aiEnabled ? "" : "Set ANTHROPIC_API_KEY on the server"}
                    >
                      🤖 Auto-apply
                    </button>
                  </>
                )}
                {job.url && (
                  <a href={job.url} target="_blank" rel="noreferrer">
                    View →
                  </a>
                )}
              </div>
            </div>
          );
        })}
        {jobs.length === 0 && (
          <p className="muted">
            No jobs in this category yet. Try “Refresh jobs” or “Load sample jobs”.
          </p>
        )}
      </div>
    </>
  );
}
