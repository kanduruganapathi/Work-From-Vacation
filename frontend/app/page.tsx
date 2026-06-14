"use client";

import { useEffect, useState } from "react";
import {
  api,
  clearToken,
  getToken,
  Job,
  JobMatch,
  Profile,
} from "@/lib/api";

const EMPTY_PROFILE: Profile = {
  skills: [],
  desired_titles: [],
  desired_employment_types: [],
  locations: [],
  remote_only: true,
  headline: "",
  summary: "",
  resume_text: "",
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

  return (
    <div className="container">
      <div className="hero">
        <h1>Find your next role while you&apos;re on vacation.</h1>
        <p>
          Work From Vacation aggregates full-time, contract, freelance, and remote
          jobs, then runs a multi-agent AI pipeline to match, tailor, and track
          every opportunity for you.
        </p>
      </div>
      <div className="card" style={{ maxWidth: 420, margin: "0 auto" }}>
        <div className="row" style={{ marginBottom: 8 }}>
          <button
            className={`btn ${mode === "register" ? "" : "secondary"}`}
            onClick={() => setMode("register")}
          >
            Create account
          </button>
          <button
            className={`btn ${mode === "login" ? "" : "secondary"}`}
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
          onChange={(e) => setPassword(e.target.value)}
        />
        {error && <p className="error">{error}</p>}
        <div style={{ marginTop: 16 }}>
          <button className="btn" onClick={submit} disabled={busy}>
            {busy ? "..." : mode === "register" ? "Get started" : "Log in"}
          </button>
        </div>
      </div>
    </div>
  );
}

// ── Dashboard ─────────────────────────────────────────────────────────────
function Dashboard({ onLogout }: { onLogout: () => void }) {
  const [profile, setProfile] = useState<Profile>(EMPTY_PROFILE);
  const [jobs, setJobs] = useState<Job[]>([]);
  const [matches, setMatches] = useState<JobMatch[]>([]);
  const [aiEnabled, setAiEnabled] = useState(false);
  const [status, setStatus] = useState("");
  const [busy, setBusy] = useState(false);

  useEffect(() => {
    (async () => {
      const p = await api.getProfile();
      if (p) setProfile({ ...EMPTY_PROFILE, ...p });
      setJobs(await api.listJobs({ limit: "24" }));
      setAiEnabled((await api.aiStatus()).enabled);
      setMatches(await api.matches());
    })().catch((e) => setStatus((e as Error).message));
  }, []);

  function logout() {
    clearToken();
    onLogout();
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
      setStatus(`Fetched ${r.fetched}, added ${r.inserted} new jobs.`);
      setJobs(await api.listJobs({ limit: "24" }));
    } catch (e) {
      setStatus((e as Error).message);
    } finally {
      setBusy(false);
    }
  }

  async function runHunt() {
    setBusy(true);
    setStatus("Running the AI agents — searching, scoring, summarizing...");
    try {
      const r = await api.runHunt(
        "Find and score the best jobs for me and suggest how to improve my search.",
        15
      );
      setStatus(r.summary);
      setMatches(r.matches);
    } catch (e) {
      setStatus((e as Error).message);
    } finally {
      setBusy(false);
    }
  }

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
        <button className="btn secondary" onClick={logout}>
          Log out
        </button>
      </div>

      {status && (
        <div className="card" style={{ marginTop: 16 }}>
          <strong>Status</strong>
          <pre>{status}</pre>
        </div>
      )}

      {/* Profile */}
      <h2 className="section-title">Your profile</h2>
      <div className="card">
        <label>Headline</label>
        <input
          value={profile.headline || ""}
          onChange={(e) => setProfile({ ...profile, headline: e.target.value })}
        />
        <label>Skills (comma separated)</label>
        <input
          value={list(profile.skills)}
          onChange={(e) =>
            setProfile({ ...profile, skills: parse(e.target.value) })
          }
        />
        <label>Desired titles (comma separated)</label>
        <input
          value={list(profile.desired_titles)}
          onChange={(e) =>
            setProfile({ ...profile, desired_titles: parse(e.target.value) })
          }
        />
        <label>Employment types (full_time, contract, freelance, ...)</label>
        <input
          value={list(profile.desired_employment_types)}
          onChange={(e) =>
            setProfile({
              ...profile,
              desired_employment_types: parse(e.target.value),
            })
          }
        />
        <label>Resume text</label>
        <textarea
          rows={5}
          value={profile.resume_text || ""}
          onChange={(e) =>
            setProfile({ ...profile, resume_text: e.target.value })
          }
        />
        <div className="row" style={{ marginTop: 14 }}>
          <button className="btn" onClick={saveProfile} disabled={busy}>
            Save profile
          </button>
          <button className="btn secondary" onClick={refresh} disabled={busy}>
            Refresh jobs
          </button>
          <button
            className="btn"
            onClick={runHunt}
            disabled={busy || !aiEnabled}
            title={aiEnabled ? "" : "Set ANTHROPIC_API_KEY on the server"}
          >
            🤖 Run AI job hunt
          </button>
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

      {/* Job feed */}
      <h2 className="section-title">Latest jobs ({jobs.length})</h2>
      <div className="grid">
        {jobs.map((job) => (
          <div className="card" key={job.id}>
            <h3>{job.title}</h3>
            <div className="muted">
              {job.company || "Unknown"} · {job.location || "—"} ·{" "}
              {job.employment_type}
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
              {job.remote && <span>· remote</span>}
              {job.salary_text && <span>· {job.salary_text}</span>}
            </div>
            {job.url && (
              <div style={{ marginTop: 10 }}>
                <a href={job.url} target="_blank" rel="noreferrer">
                  View posting →
                </a>
              </div>
            )}
          </div>
        ))}
      </div>
    </div>
  );
}
