"use client";

import { useEffect, useRef, useState } from "react";
import {
  api,
  Application,
  ApplicationStatus,
  InterviewPrep,
  Job,
  JobFacets,
  SavedSearch,
} from "@/lib/api";

const PAGE = 24;

const TABS: {
  key: string;
  label: string;
  params: Record<string, string>;
  facet?: "remote" | string;
}[] = [
  { key: "all", label: "All", params: {} },
  { key: "remote", label: "Remote", params: { remote: "true" }, facet: "remote" },
  { key: "full_time", label: "Full-time", params: { employment_type: "full_time" }, facet: "full_time" },
  { key: "contract", label: "Contract", params: { employment_type: "contract" }, facet: "contract" },
  { key: "freelance", label: "Freelance", params: { employment_type: "freelance" }, facet: "freelance" },
];

const RECENCY = [
  { label: "Any time", value: "" },
  { label: "Past 24h", value: "1" },
  { label: "Past 3 days", value: "3" },
  { label: "Past week", value: "7" },
  { label: "Past month", value: "30" },
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
  const [sort, setSort] = useState("recent");
  const [source, setSource] = useState("");
  const [recency, setRecency] = useState("");
  const [tag, setTag] = useState("");
  const [jobs, setJobs] = useState<Job[]>([]);
  const [total, setTotal] = useState(0);
  const [facets, setFacets] = useState<JobFacets | null>(null);
  const [saved, setSaved] = useState<SavedSearch[]>([]);
  const [busyId, setBusyId] = useState<number | null>(null);
  const [detail, setDetail] = useState<Job | null>(null);
  const [prep, setPrep] = useState<InterviewPrep | null>(null);
  const [prepBusy, setPrepBusy] = useState(false);

  function buildParams(key: string, off: number): Record<string, string> {
    const base = TABS.find((t) => t.key === key)?.params ?? {};
    const params: Record<string, string> = {
      ...base,
      sort,
      limit: String(PAGE),
      offset: String(off),
    };
    if (q.trim()) params.q = q.trim();
    if (source) params.source = source;
    if (recency) params.posted_within_days = recency;
    if (tag) params.tag = tag;
    return params;
  }

  // The active filters as a plain object (for saving a search).
  function currentParams(): Record<string, string> {
    const p = buildParams(tab, 0);
    delete p.limit;
    delete p.offset;
    return p;
  }

  async function load(key: string, off: number, append: boolean) {
    const res = await api.searchJobs(buildParams(key, off));
    setJobs(append ? (prev) => [...prev, ...res.items] : res.items);
    setTotal(res.total);
    setFacets(res.facets);
  }

  // Reload whenever any filter/sort/tab/source/recency/tag changes.
  useEffect(() => {
    load(tab, 0, false).catch((e) => onStatus((e as Error).message));
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [tab, sort, source, recency, tag]);

  // Debounced search-as-you-type on the keyword box.
  const firstRun = useRef(true);
  useEffect(() => {
    if (firstRun.current) {
      firstRun.current = false;
      return;
    }
    const id = setTimeout(() => {
      load(tab, 0, false).catch((e) => onStatus((e as Error).message));
    }, 400);
    return () => clearTimeout(id);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [q]);

  useEffect(() => {
    api.savedSearches().then(setSaved).catch(() => {});
  }, []);

  function runSearch() {
    load(tab, 0, false).catch((e) => onStatus((e as Error).message));
  }

  async function saveCurrent() {
    const name = window.prompt(
      "Name this search",
      q || (tab !== "all" ? tab : "My search")
    );
    if (!name) return;
    try {
      await api.createSavedSearch(name, currentParams());
      setSaved(await api.savedSearches());
      onStatus(`Saved search “${name}”. You'll be alerted when new jobs match.`);
    } catch (e) {
      onStatus((e as Error).message);
    }
  }

  function applySaved(s: SavedSearch) {
    const p = s.params || {};
    setQ((p.q as string) || "");
    setSort((p.sort as string) || "recent");
    setSource((p.source as string) || "");
    setRecency((p.posted_within_days as string)?.toString() || "");
    setTag((p.tag as string) || "");
    if (p.remote) setTab("remote");
    else if (p.employment_type) setTab(p.employment_type as string);
    else setTab("all");
  }

  async function toggleAlert(s: SavedSearch) {
    try {
      await api.updateSavedSearch(s.id, { alert_enabled: !s.alert_enabled });
      setSaved(await api.savedSearches());
    } catch (e) {
      onStatus((e as Error).message);
    }
  }

  async function removeSaved(s: SavedSearch) {
    try {
      await api.deleteSavedSearch(s.id);
      setSaved((prev) => prev.filter((x) => x.id !== s.id));
    } catch (e) {
      onStatus((e as Error).message);
    }
  }

  function pickTag(t: string) {
    setTag(t);
    setDetail(null);
  }

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

  const facetCount = (key: string | undefined): number | null => {
    if (!facets || !key) return null;
    if (key === "remote") return facets.remote;
    return facets.employment_types[key] ?? 0;
  };

  return (
    <>
      <div className="row" style={{ marginBottom: 12, gap: 8 }}>
        <input
          placeholder="Search title, company, skills, description..."
          value={q}
          onChange={(e) => setQ(e.target.value)}
          onKeyDown={(e) => e.key === "Enter" && runSearch()}
          style={{ flex: 1, minWidth: 220, marginTop: 0 }}
        />
        <select
          value={sort}
          onChange={(e) => setSort(e.target.value)}
          style={{ width: "auto", marginTop: 0 }}
          title="Sort"
        >
          <option value="recent">Newest</option>
          <option value="relevance">Most relevant</option>
        </select>
        <button className="btn" onClick={runSearch}>
          Search
        </button>
        <button className="btn secondary" onClick={saveCurrent} title="Save this search + get alerts">
          ★ Save
        </button>
      </div>

      {saved.length > 0 && (
        <div className="saved-row">
          {saved.map((s) => (
            <span className="saved-chip" key={s.id}>
              <button className="saved-name" onClick={() => applySaved(s)}>
                {s.name}
              </button>
              <button
                className="saved-alert"
                onClick={() => toggleAlert(s)}
                title={s.alert_enabled ? "Alerts on" : "Alerts off"}
              >
                {s.alert_enabled ? "🔔" : "🔕"}
              </button>
              <button
                className="saved-del"
                onClick={() => removeSaved(s)}
                title="Delete"
              >
                ✕
              </button>
            </span>
          ))}
        </div>
      )}

      <div className="row" style={{ marginBottom: 12, gap: 8 }}>
        <select
          value={source}
          onChange={(e) => setSource(e.target.value)}
          style={{ width: "auto", marginTop: 0 }}
          title="Source"
        >
          <option value="">All sources</option>
          {facets &&
            Object.keys(facets.sources).map((s) => (
              <option key={s} value={s}>
                {s} ({facets.sources[s]})
              </option>
            ))}
        </select>
        <select
          value={recency}
          onChange={(e) => setRecency(e.target.value)}
          style={{ width: "auto", marginTop: 0 }}
          title="Date posted"
        >
          {RECENCY.map((r) => (
            <option key={r.value} value={r.value}>
              {r.label}
            </option>
          ))}
        </select>
        {tag && (
          <span className="active-filter">
            tag: {tag}
            <button className="link-btn" onClick={() => setTag("")}>
              ✕
            </button>
          </span>
        )}
      </div>

      <div className="tabs">
        {TABS.map((t) => {
          const c = facetCount(t.facet);
          return (
            <button
              key={t.key}
              className={`tab ${tab === t.key ? "active" : ""}`}
              onClick={() => setTab(t.key)}
            >
              {t.label}
              {c !== null && <span className="tab-count">{c}</span>}
            </button>
          );
        })}
      </div>

      <div className="muted" style={{ margin: "0 0 10px" }}>
        {total} job{total === 1 ? "" : "s"}
        {q ? ` for “${q}”` : ""}
      </div>

      <div className="grid">
        {jobs.map((job) => {
          const tracked = trackedByJob[job.id];
          return (
            <div className="card" key={job.id}>
              <h3 onClick={() => openDetail(job)} style={{ cursor: "pointer" }}>
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
                  <span
                    className="tag clickable"
                    key={t}
                    onClick={() => pickTag(t)}
                    title={`Filter by ${t}`}
                  >
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
            No jobs match. Clear filters, or try “Refresh jobs” / “Load sample jobs”.
          </p>
        )}
      </div>

      {jobs.length < total && (
        <div style={{ textAlign: "center", marginTop: 16 }}>
          <button
            className="btn secondary"
            onClick={() =>
              load(tab, jobs.length, true).catch((e) => onStatus((e as Error).message))
            }
          >
            Load more ({total - jobs.length} more)
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
                <span className="tag clickable" key={t} onClick={() => pickTag(t)}>
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
                      {prep.likely_questions.map((qq, i) => (
                        <li key={i}>{qq}</li>
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
