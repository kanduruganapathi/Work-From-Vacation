"use client";

import { useEffect, useState } from "react";
import {
  api,
  Application,
  ApplicationStatus,
  InterviewPrep,
  Job,
} from "@/lib/api";

const PAGE = 24;

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

const stripHtml = (s: string) => s.replace(/<[^>]*>/g, " ").replace(/\s+/g, " ").trim();

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
  const [q, setQ] = useState("");
  const [jobs, setJobs] = useState<Job[]>([]);
  const [offset, setOffset] = useState(0);
  const [hasMore, setHasMore] = useState(false);
  const [busyId, setBusyId] = useState<number | null>(null);
  const [detail, setDetail] = useState<Job | null>(null);
  const [prep, setPrep] = useState<InterviewPrep | null>(null);
  const [prepBusy, setPrepBusy] = useState(false);

  function openDetail(job: Job) {
    setPrep(null);
    setDetail(job);
  }

  async function getPrep(job: Job) {
    setPrepBusy(true);
    onStatus(`🎤 Preparing interview questions for “${job.title}”...`);
    try {
      setPrep(await api.interviewPrep(job.id));
      onStatus("Interview prep ready.");
    } catch (e) {
      onStatus((e as Error).message);
    } finally {
      setPrepBusy(false);
    }
  }

  async function load(key: string, search: string, reset: boolean) {
    const base = TABS.find((t) => t.key === key)?.params ?? {};
    const nextOffset = reset ? 0 : offset;
    const params: Record<string, string> = {
      ...base,
      limit: String(PAGE),
      offset: String(nextOffset),
    };
    if (search.trim()) params.q = search.trim();
    const batch = await api.listJobs(params);
    setJobs(reset ? batch : [...jobs, ...batch]);
    setOffset(nextOffset + batch.length);
    setHasMore(batch.length === PAGE);
  }

  useEffect(() => {
    load("all", "", true).catch((e) => onStatus((e as Error).message));
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  function selectTab(key: string) {
    setTab(key);
    load(key, q, true).catch((e) => onStatus((e as Error).message));
  }

  function search() {
    load(tab, q, true).catch((e) => onStatus((e as Error).message));
  }

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
      <div className="row" style={{ marginBottom: 12, gap: 8 }}>
        <input
          placeholder="Search titles, companies, skills..."
          value={q}
          onChange={(e) => setQ(e.target.value)}
          onKeyDown={(e) => e.key === "Enter" && search()}
          style={{ flex: 1, minWidth: 220, marginTop: 0 }}
        />
        <button className="btn" onClick={search}>
          Search
        </button>
      </div>

      <div className="tabs">
        {TABS.map((t) => (
          <button
            key={t.key}
            className={`tab ${tab === t.key ? "active" : ""}`}
            onClick={() => selectTab(t.key)}
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
              <h3
                onClick={() => openDetail(job)}
                style={{ cursor: "pointer" }}
                title="View details"
              >
                {job.title}
              </h3>
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
                <button className="link-btn" onClick={() => openDetail(job)}>
                  Details
                </button>
              </div>
            </div>
          );
        })}
        {jobs.length === 0 && (
          <p className="muted">
            No jobs here yet. Try “Refresh jobs” or “Load sample jobs”.
          </p>
        )}
      </div>

      {hasMore && (
        <div style={{ textAlign: "center", marginTop: 16 }}>
          <button
            className="btn secondary"
            onClick={() => load(tab, q, false).catch((e) => onStatus((e as Error).message))}
          >
            Load more
          </button>
        </div>
      )}

      {detail && (
        <div className="modal-overlay" onClick={() => setDetail(null)}>
          <div className="modal" onClick={(e) => e.stopPropagation()}>
            <div className="row" style={{ justifyContent: "space-between" }}>
              <h2 style={{ margin: 0 }}>{detail.title}</h2>
              <button className="btn secondary" onClick={() => setDetail(null)}>
                ✕
              </button>
            </div>
            <div className="muted" style={{ marginTop: 4 }}>
              {detail.company || "Unknown"} · {detail.location || "—"} ·{" "}
              {detail.employment_type.replace("_", " ")}
              {detail.salary_text ? ` · ${detail.salary_text}` : ""}
            </div>
            <div style={{ marginTop: 10 }}>
              {detail.tags.map((t) => (
                <span className="tag" key={t}>
                  {t}
                </span>
              ))}
            </div>
            <div className="modal-body">
              {detail.description
                ? stripHtml(detail.description)
                : "No description provided."}
            </div>
            <div className="row" style={{ marginTop: 14 }}>
              {!trackedByJob[detail.id] && (
                <button
                  className="btn"
                  onClick={() => autoApply(detail)}
                  disabled={!aiEnabled}
                >
                  🤖 Auto-apply
                </button>
              )}
              <button
                className="btn secondary"
                onClick={() => getPrep(detail)}
                disabled={prepBusy || !aiEnabled}
                title={aiEnabled ? "" : "Set ANTHROPIC_API_KEY on the server"}
              >
                🎤 Interview prep
              </button>
              {detail.url && (
                <a href={detail.url} target="_blank" rel="noreferrer">
                  Open original posting →
                </a>
              )}
            </div>

            {prep && (
              <div className="prep">
                {prep.summary && <p style={{ fontSize: 14 }}>{prep.summary}</p>}
                {prep.likely_questions.length > 0 && (
                  <>
                    <div className="prep-head">Likely questions</div>
                    <ul>
                      {prep.likely_questions.map((q, i) => (
                        <li key={i}>{q}</li>
                      ))}
                    </ul>
                  </>
                )}
                {prep.talking_points.length > 0 && (
                  <>
                    <div className="prep-head">Talking points</div>
                    <ul>
                      {prep.talking_points.map((p, i) => (
                        <li key={i}>{p}</li>
                      ))}
                    </ul>
                  </>
                )}
                {prep.focus_areas.length > 0 && (
                  <>
                    <div className="prep-head">Brush up on</div>
                    <ul>
                      {prep.focus_areas.map((f, i) => (
                        <li key={i}>{f}</li>
                      ))}
                    </ul>
                  </>
                )}
              </div>
            )}
          </div>
        </div>
      )}
    </>
  );
}
