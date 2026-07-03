"use client";

import { useEffect, useState } from "react";
import {
  api,
  Application,
  clearToken,
  getToken,
  JobMatch,
  Notification,
  pollTask,
  Profile,
  Task,
} from "@/lib/api";
import JobFeed from "./components/JobFeed";
import ApplicationsBoard from "./components/Applications";
import NotificationBell from "./components/NotificationBell";

const EMPTY_PROFILE: Profile = {
  skills: [],
  desired_titles: [],
  desired_employment_types: [],
  locations: [],
  remote_only: true,
  headline: "",
  summary: "",
  resume_text: "",
  full_name: "",
  phone: "",
  linkedin_url: "",
  github_url: "",
  portfolio_url: "",
  current_location: "",
  autopilot_enabled: false,
  autopilot_min_score: 85,
  autopilot_daily_limit: 5,
  autopilot_auto_submit: false,
};

export default function Home() {
  const [authed, setAuthed] = useState(false);

  useEffect(() => {
    setAuthed(!!getToken());
  }, []);

  if (!authed) return <Landing onAuthed={() => setAuthed(true)} />;
  return <Dashboard onLogout={() => setAuthed(false)} />;
}

// ── Landing + auth ────────────────────────────────────────────────────────
function Landing({ onAuthed }: { onAuthed: () => void }) {
  const [mode, setMode] = useState<"login" | "register">("register");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);

  async function submit() {
    if (mode === "register" && password.length < 8) {
      setError("Password must be at least 8 characters.");
      return;
    }
    setBusy(true);
    setError("");
    try {
      if (mode === "register") {
        await api.register(email, password);
      }
      await api.login(email, password);
      onAuthed();
    } catch (e) {
      setError((e as Error).message);
    } finally {
      setBusy(false);
    }
  }

  const scrollToAuth = () => {
    document.getElementById("auth")?.scrollIntoView({ behavior: "smooth" });
  };

  const FEATURES = [
    {
      icon: "🌐",
      title: "Aggregate everything",
      body: "Full-time, contract, freelance, and remote roles from many sources, deduped into one feed.",
    },
    {
      icon: "🎯",
      title: "AI match scoring",
      body: "A multi-agent pipeline scores every job against your profile — with reasons and red flags.",
    },
    {
      icon: "🤖",
      title: "Auto-apply",
      body: "The AI tailors your resume and drafts a cover letter per role, then tracks the application.",
    },
    {
      icon: "🔔",
      title: "Alerts on autopilot",
      body: "Get notified the moment a new high-fit role appears — even while you're away.",
    },
  ];

  const STEPS = [
    { n: 1, t: "Build your profile", d: "Upload your resume (PDF) and set your skills, titles, and preferences." },
    { n: 2, t: "Let the agents run", d: "Aggregate jobs, then run the AI hunt to score and rank the best matches." },
    { n: 3, t: "Apply & track", d: "Auto-apply to top roles and watch them move across your pipeline." },
  ];

  return (
    <div className="container">
      <section className="hero">
        <div className="hero-badges">
          {["Full-time", "Contract", "Freelance", "Remote"].map((c) => (
            <span className="chip" key={c}>
              {c}
            </span>
          ))}
        </div>
        <h1>
          Find your next role <span className="grad">while you&apos;re on vacation.</span>
        </h1>
        <p>
          Work From Vacation aggregates jobs across every employment type, then runs
          a multi-agent AI pipeline to match, tailor, and track every opportunity —
          so your job hunt runs itself.
        </p>
        <div className="hero-cta">
          <button className="btn btn-lg" onClick={scrollToAuth}>
            Get started — it&apos;s free
          </button>
          <button
            className="btn secondary btn-lg"
            onClick={() =>
              document
                .getElementById("how")
                ?.scrollIntoView({ behavior: "smooth" })
            }
          >
            How it works
          </button>
        </div>
      </section>

      <section className="features">
        {FEATURES.map((f) => (
          <div className="feature-card" key={f.title}>
            <div className="feature-icon">{f.icon}</div>
            <h3>{f.title}</h3>
            <p className="muted">{f.body}</p>
          </div>
        ))}
      </section>

      <section id="how" className="steps-section">
        <h2 className="landing-h2">How it works</h2>
        <div className="steps">
          {STEPS.map((s) => (
            <div className="step" key={s.n}>
              <div className="step-num">{s.n}</div>
              <div>
                <strong>{s.t}</strong>
                <p className="muted" style={{ margin: "4px 0 0" }}>
                  {s.d}
                </p>
              </div>
            </div>
          ))}
        </div>
      </section>

      <section id="auth">
        <h2 className="landing-h2">
          {mode === "register" ? "Create your free account" : "Welcome back"}
        </h2>
        <div className="auth-card">
          <div className="auth-toggle">
            <button
              className={`tab ${mode === "register" ? "active" : ""}`}
              onClick={() => setMode("register")}
            >
              Create account
            </button>
            <button
              className={`tab ${mode === "login" ? "active" : ""}`}
              onClick={() => setMode("login")}
            >
              Log in
            </button>
          </div>
          <label>Email</label>
          <input value={email} onChange={(e) => setEmail(e.target.value)} />
          <label>Password</label>
          <input
            type="password"
            value={password}
            minLength={8}
            placeholder="At least 8 characters"
            onChange={(e) => setPassword(e.target.value)}
            onKeyDown={(e) => e.key === "Enter" && submit()}
          />
          {mode === "register" && (
            <p className="muted" style={{ marginTop: 6 }}>
              Use at least 8 characters.
            </p>
          )}
          {error && <p className="error">{error}</p>}
          <div style={{ marginTop: 16 }}>
            <button
              className="btn btn-lg"
              onClick={submit}
              disabled={busy}
              style={{ width: "100%" }}
            >
              {busy ? "..." : mode === "register" ? "Get started" : "Log in"}
            </button>
          </div>
        </div>
      </section>

      <footer className="landing-foot muted">
        Work From Vacation · automated job search across full-time, contract,
        freelance &amp; remote
      </footer>
    </div>
  );
}

// ── Dashboard ─────────────────────────────────────────────────────────────
function Dashboard({ onLogout }: { onLogout: () => void }) {
  const [profile, setProfile] = useState<Profile>(EMPTY_PROFILE);
  const [matches, setMatches] = useState<JobMatch[]>([]);
  const [applications, setApplications] = useState<Application[]>([]);
  const [aiEnabled, setAiEnabled] = useState(false);
  const [status, setStatus] = useState("");
  const [busy, setBusy] = useState(false);
  const [feedKey, setFeedKey] = useState(0); // bump to reload the job feed
  const [task, setTask] = useState<Task | null>(null);
  const [notifications, setNotifications] = useState<Notification[]>([]);
  const [resumeEdit, setResumeEdit] = useState(false);

  async function reloadApplications() {
    setApplications(await api.listApplications());
  }

  async function reloadNotifications() {
    setNotifications(await api.notifications());
  }

  useEffect(() => {
    (async () => {
      const p = await api.getProfile();
      if (p) setProfile({ ...EMPTY_PROFILE, ...p });
      setAiEnabled((await api.aiStatus()).enabled);
      setMatches(await api.matches());
      await reloadApplications();
      await reloadNotifications();
    })().catch((e) => setStatus((e as Error).message));
  }, []);

  // Run a background AI task and reflect its progress live.
  async function runTask(
    start: () => Promise<Task>,
    { requireAi = true }: { requireAi?: boolean } = {}
  ) {
    if (requireAi && !aiEnabled) {
      setStatus("AI is disabled. Set ANTHROPIC_API_KEY on the server.");
      return;
    }
    setBusy(true);
    try {
      const created = await start();
      setTask(created);
      const final = await pollTask(created.id, setTask);
      setStatus(final.message || "Done.");
      setMatches(await api.matches());
      await reloadApplications();
      await reloadNotifications();
      setTimeout(() => setTask(null), 2500);
    } catch (e) {
      setStatus((e as Error).message);
      setTask(null);
    } finally {
      setBusy(false);
    }
  }

  // Map of job_id -> application, so job cards can show tracking state.
  const trackedByJob: Record<number, Application> = {};
  for (const a of applications) trackedByJob[a.job_id] = a;

  function logout() {
    clearToken();
    onLogout();
  }

  async function uploadResume(file: File) {
    setBusy(true);
    setStatus(`Parsing ${file.name}...`);
    try {
      const updated = await api.uploadResume(file);
      setProfile({ ...EMPTY_PROFILE, ...updated });
      setStatus(
        `Resume imported (${(updated.resume_text || "").length} characters extracted).`
      );
    } catch (e) {
      setStatus((e as Error).message);
    } finally {
      setBusy(false);
    }
  }

  async function saveProfile() {
    setBusy(true);
    setStatus("Saving profile...");
    try {
      await api.saveProfile(profile);
      setStatus("Profile saved.");
    } catch (e) {
      setStatus((e as Error).message);
    } finally {
      setBusy(false);
    }
  }

  async function refresh() {
    setBusy(true);
    setStatus("Pulling fresh jobs from all sources...");
    try {
      const r = await api.refreshJobs();
      setStatus(
        r.inserted > 0
          ? `Fetched ${r.fetched}, added ${r.inserted} new jobs.`
          : "No new jobs from live sources (they may be unreachable here). Try “Load sample jobs”."
      );
      setFeedKey((k) => k + 1);
    } catch (e) {
      setStatus((e as Error).message);
    } finally {
      setBusy(false);
    }
  }

  async function seed() {
    setBusy(true);
    setStatus("Loading curated sample jobs...");
    try {
      const r = await api.seedJobs();
      setStatus(`Loaded ${r.inserted} sample jobs.`);
      setFeedKey((k) => k + 1);
    } catch (e) {
      setStatus((e as Error).message);
    } finally {
      setBusy(false);
    }
  }

  const submitApplication = (jobId: number, dryRun: boolean) =>
    runTask(() => api.submitApplication(jobId, dryRun), { requireAi: false });

  const runHunt = () =>
    runTask(() =>
      api.runHuntAsync(
        "Find and score the best jobs for me and suggest how to improve my search.",
        15
      )
    );
  const scoreNew = () => runTask(() => api.scoreNew());
  const batchApply = () => runTask(() => api.batchApply(80, 5));

  const list = (v: string[]) => v.join(", ");
  const parse = (s: string) =>
    s
      .split(",")
      .map((x) => x.trim())
      .filter(Boolean);

  return (
    <div className="container">
      <div className="row" style={{ justifyContent: "space-between" }}>
        <div className="row">
          <span className={`pill ${aiEnabled ? "on" : "off"}`}>
            AI {aiEnabled ? "ready" : "disabled"}
          </span>
        </div>
        <div className="row">
          <NotificationBell
            notifications={notifications}
            onChanged={() => reloadNotifications().catch(() => {})}
          />
          <button className="btn secondary" onClick={logout}>
            Log out
          </button>
        </div>
      </div>

      <div className="stats">
        {[
          { label: "AI matches", value: matches.length },
          { label: "Applications", value: applications.length },
          {
            label: "Interviewing",
            value: applications.filter((a) => a.status === "interviewing").length,
          },
          {
            label: "Unread alerts",
            value: notifications.filter((n) => !n.read).length,
          },
        ].map((s) => (
          <div className="stat" key={s.label}>
            <div className="stat-value">{s.value}</div>
            <div className="muted">{s.label}</div>
          </div>
        ))}
      </div>

      {task && (task.status === "running" || task.status === "queued") && (
        <div className="card" style={{ marginTop: 16 }}>
          <div className="row" style={{ justifyContent: "space-between" }}>
            <strong>🤖 {task.kind.replace("_", " ")}</strong>
            <span className="muted">{task.progress}%</span>
          </div>
          <div className="progress">
            <div className="progress-fill" style={{ width: `${task.progress}%` }} />
          </div>
          <div className="muted" style={{ marginTop: 6 }}>
            {task.message}
          </div>
        </div>
      )}

      {status && (
        <div className="card" style={{ marginTop: 16 }}>
          <strong>Status</strong>
          <pre>{status}</pre>
        </div>
      )}

      {/* Quick actions toolbar */}
      <div className="toolbar">
        <button className="btn secondary" onClick={refresh} disabled={busy}>
          ⟳ Refresh jobs
        </button>
        <button className="btn secondary" onClick={seed} disabled={busy}>
          ＋ Load sample jobs
        </button>
        <span className="toolbar-sep" />
        <button
          className="btn"
          onClick={runHunt}
          disabled={busy || !aiEnabled}
          title={aiEnabled ? "" : "Set ANTHROPIC_API_KEY on the server"}
        >
          🤖 Run AI hunt
        </button>
        <button
          className="btn"
          onClick={scoreNew}
          disabled={busy || !aiEnabled}
          title={aiEnabled ? "" : "Set ANTHROPIC_API_KEY on the server"}
        >
          ⚡ Score new
        </button>
        <button
          className="btn"
          onClick={batchApply}
          disabled={busy || !aiEnabled}
          title={aiEnabled ? "" : "Set ANTHROPIC_API_KEY on the server"}
        >
          🚀 Auto-apply top
        </button>
      </div>

      {/* Profile */}
      <h2 className="section-title">Your profile</h2>
      <div className="card">
        <div className="form-grid">
          <div className="full">
            <label>Headline</label>
            <input
              placeholder="e.g. Senior AI Engineer"
              value={profile.headline || ""}
              onChange={(e) => setProfile({ ...profile, headline: e.target.value })}
            />
          </div>
          <div>
            <label>Skills (comma separated)</label>
            <input
              placeholder="python, fastapi, llm"
              value={list(profile.skills)}
              onChange={(e) => setProfile({ ...profile, skills: parse(e.target.value) })}
            />
          </div>
          <div>
            <label>Desired titles</label>
            <input
              placeholder="AI Engineer, Backend Engineer"
              value={list(profile.desired_titles)}
              onChange={(e) =>
                setProfile({ ...profile, desired_titles: parse(e.target.value) })
              }
            />
          </div>
          <div>
            <label>Employment types</label>
            <input
              placeholder="full_time, contract, freelance"
              value={list(profile.desired_employment_types)}
              onChange={(e) =>
                setProfile({
                  ...profile,
                  desired_employment_types: parse(e.target.value),
                })
              }
            />
          </div>
          <div>
            <label>Preferred locations</label>
            <input
              placeholder="Bangalore, Remote"
              value={list(profile.locations)}
              onChange={(e) =>
                setProfile({ ...profile, locations: parse(e.target.value) })
              }
            />
          </div>
          <div>
            <label>Years of experience</label>
            <input
              type="number"
              min={0}
              max={50}
              value={profile.years_experience ?? ""}
              onChange={(e) =>
                setProfile({
                  ...profile,
                  years_experience: e.target.value ? Number(e.target.value) : null,
                })
              }
            />
          </div>
          <div className="remote-row">
            <label className="switch" style={{ marginTop: 22 }}>
              <input
                type="checkbox"
                checked={profile.remote_only}
                onChange={(e) =>
                  setProfile({ ...profile, remote_only: e.target.checked })
                }
              />
              <span className="slider" />
            </label>
            <span className="muted" style={{ marginTop: 24 }}>
              Remote roles only
            </span>
          </div>
        </div>

        {/* Contact details — used to fill real application forms */}
        <div className="contact-head">Contact details (used to fill applications)</div>
        <div className="form-grid">
          <div>
            <label>Full name</label>
            <input
              value={profile.full_name || ""}
              onChange={(e) => setProfile({ ...profile, full_name: e.target.value })}
            />
          </div>
          <div>
            <label>Phone</label>
            <input
              value={profile.phone || ""}
              onChange={(e) => setProfile({ ...profile, phone: e.target.value })}
            />
          </div>
          <div>
            <label>Current location</label>
            <input
              placeholder="Bangalore, India"
              value={profile.current_location || ""}
              onChange={(e) =>
                setProfile({ ...profile, current_location: e.target.value })
              }
            />
          </div>
          <div>
            <label>LinkedIn URL</label>
            <input
              value={profile.linkedin_url || ""}
              onChange={(e) =>
                setProfile({ ...profile, linkedin_url: e.target.value })
              }
            />
          </div>
          <div>
            <label>GitHub URL</label>
            <input
              value={profile.github_url || ""}
              onChange={(e) =>
                setProfile({ ...profile, github_url: e.target.value })
              }
            />
          </div>
          <div>
            <label>Portfolio URL</label>
            <input
              value={profile.portfolio_url || ""}
              onChange={(e) =>
                setProfile({ ...profile, portfolio_url: e.target.value })
              }
            />
          </div>
        </div>

        {/* Resume card */}
        <div className="resume-card">
          <div className="row" style={{ justifyContent: "space-between" }}>
            <strong>📄 Resume</strong>
            <span className="muted">
              {profile.resume_text
                ? `${profile.resume_text.length.toLocaleString()} characters on file`
                : "No resume yet"}
            </span>
          </div>

          {profile.resume_text && !resumeEdit && (
            <div className="resume-preview">
              {profile.resume_text.split("\n").slice(0, 6).join("\n")}
              {profile.resume_text.split("\n").length > 6 ? "\n…" : ""}
            </div>
          )}

          {resumeEdit && (
            <textarea
              rows={10}
              placeholder="Paste your resume here..."
              value={profile.resume_text || ""}
              onChange={(e) =>
                setProfile({ ...profile, resume_text: e.target.value })
              }
            />
          )}

          <div className="row" style={{ marginTop: 10, gap: 8 }}>
            <label className="btn secondary" style={{ margin: 0, cursor: "pointer" }}>
              {profile.resume_text ? "Replace" : "Upload PDF / text"}
              <input
                type="file"
                accept=".pdf,.txt,.md,text/plain,application/pdf"
                style={{ display: "none" }}
                onChange={(e) => {
                  const f = e.target.files?.[0];
                  if (f) uploadResume(f);
                  e.target.value = "";
                }}
              />
            </label>
            <button
              className="btn secondary"
              onClick={() => setResumeEdit((v) => !v)}
            >
              {resumeEdit ? "Done editing" : profile.resume_text ? "✎ Edit" : "Paste"}
            </button>
            {profile.resume_text && (
              <button
                className="link-btn"
                onClick={() => setProfile({ ...profile, resume_text: "" })}
              >
                Clear
              </button>
            )}
            <span className="muted" style={{ fontSize: 12 }}>
              Feeds AI matching, tailoring & cover letters.
            </span>
          </div>
        </div>

        <div className="row" style={{ marginTop: 16 }}>
          <button className="btn" onClick={saveProfile} disabled={busy}>
            Save profile
          </button>
        </div>
      </div>

      {/* Autopilot */}
      <h2 className="section-title">Auto-apply autopilot</h2>
      <div className="card">
        <div className="row" style={{ justifyContent: "space-between" }}>
          <div>
            <strong>Apply automatically to new high-fit roles</strong>
            <p className="muted" style={{ margin: "4px 0 0" }}>
              When on, the scheduler scores new jobs and auto-applies (tailored
              resume + cover letter) to matches above your threshold, up to your
              daily cap.
            </p>
          </div>
          <label className="switch">
            <input
              type="checkbox"
              checked={profile.autopilot_enabled}
              onChange={(e) =>
                setProfile({ ...profile, autopilot_enabled: e.target.checked })
              }
            />
            <span className="slider" />
          </label>
        </div>
        <div className="row" style={{ gap: 20, marginTop: 12 }}>
          <div style={{ flex: 1, minWidth: 160 }}>
            <label>Minimum match score: {profile.autopilot_min_score}</label>
            <input
              type="range"
              min={0}
              max={100}
              value={profile.autopilot_min_score}
              onChange={(e) =>
                setProfile({
                  ...profile,
                  autopilot_min_score: Number(e.target.value),
                })
              }
            />
          </div>
          <div style={{ flex: 1, minWidth: 160 }}>
            <label>Max applications per day</label>
            <input
              type="number"
              min={1}
              max={50}
              value={profile.autopilot_daily_limit}
              onChange={(e) =>
                setProfile({
                  ...profile,
                  autopilot_daily_limit: Number(e.target.value),
                })
              }
            />
          </div>
        </div>
        <div
          className="row"
          style={{ marginTop: 14, gap: 10, alignItems: "flex-start" }}
        >
          <label className="switch">
            <input
              type="checkbox"
              checked={profile.autopilot_auto_submit}
              onChange={(e) =>
                setProfile({ ...profile, autopilot_auto_submit: e.target.checked })
              }
            />
            <span className="slider" />
          </label>
          <div>
            <strong>Actually submit applications</strong>
            <p className="muted" style={{ margin: "2px 0 0", fontSize: 13 }}>
              When on, autopilot doesn&apos;t just prepare materials — it submits
              to supported boards (Greenhouse / Lever / email). Off = prepare &
              track only. Fill your contact details above first.
            </p>
          </div>
        </div>
        <div className="row" style={{ marginTop: 12 }}>
          <button className="btn" onClick={saveProfile} disabled={busy}>
            Save autopilot
          </button>
          <span className={`pill ${profile.autopilot_enabled ? "on" : "off"}`}>
            Autopilot {profile.autopilot_enabled ? "ON" : "off"}
          </span>
          {profile.autopilot_auto_submit && (
            <span className="pill on">Auto-submit ON</span>
          )}
        </div>
      </div>

      {/* Matches */}
      {matches.length > 0 && (
        <>
          <h2 className="section-title">Top AI matches</h2>
          <div className="grid">
            {matches.map((m) => (
              <div className="card" key={m.id}>
                <div className="row" style={{ justifyContent: "space-between" }}>
                  <h3>{m.job.title}</h3>
                  <span className="score">{Math.round(m.score)}</span>
                </div>
                <div className="muted">
                  {m.job.company} · {m.job.employment_type}
                </div>
                {m.summary && <p style={{ fontSize: 14 }}>{m.summary}</p>}
                {m.reasons.slice(0, 3).map((r, i) => (
                  <div key={i} className="muted">
                    ✅ {r}
                  </div>
                ))}
                {m.concerns.slice(0, 2).map((c, i) => (
                  <div key={i} className="muted">
                    ⚠️ {c}
                  </div>
                ))}
                {m.job.url && (
                  <div style={{ marginTop: 10 }}>
                    <a href={m.job.url} target="_blank" rel="noreferrer">
                      View posting →
                    </a>
                  </div>
                )}
              </div>
            ))}
          </div>
        </>
      )}

      {/* Application tracker */}
      <h2 className="section-title">Application tracker</h2>
      <ApplicationsBoard
        applications={applications}
        aiEnabled={aiEnabled}
        busy={busy}
        onChanged={() => reloadApplications().catch(() => {})}
        onStatus={setStatus}
        onSubmit={submitApplication}
      />

      {/* Job feed with employment-type tabs */}
      <h2 className="section-title">Browse jobs</h2>
      <JobFeed
        key={feedKey}
        aiEnabled={aiEnabled}
        trackedByJob={trackedByJob}
        busy={busy}
        onChanged={() => reloadApplications().catch(() => {})}
        onStatus={setStatus}
        onRefresh={refresh}
        onSeed={seed}
      />
    </div>
  );
}
