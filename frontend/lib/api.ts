// Lightweight API client for the Work From Vacation backend.

// Default to same-origin: requests go to "/api/..." on the frontend, which
// Next.js proxies to the backend (see next.config.js rewrites). This avoids
// CORS and works behind remote previews / tunnels. Override only if you want
// the browser to hit the backend directly.
const BASE = process.env.NEXT_PUBLIC_API_BASE_URL || "";

const TOKEN_KEY = "wfv_token";

export function getToken(): string | null {
  if (typeof window === "undefined") return null;
  return window.localStorage.getItem(TOKEN_KEY);
}

export function setToken(token: string) {
  window.localStorage.setItem(TOKEN_KEY, token);
}

export function clearToken() {
  window.localStorage.removeItem(TOKEN_KEY);
}

// FastAPI returns `detail` as a string (HTTPException) or an array of
// {loc, msg, type} objects (422 validation). Render both as readable text.
function formatError(body: unknown, status: number): string {
  const detail = (body as { detail?: unknown })?.detail;
  if (typeof detail === "string") return detail;
  if (Array.isArray(detail)) {
    return detail
      .map((e: { loc?: unknown[]; msg?: string }) => {
        const field = Array.isArray(e.loc) ? e.loc[e.loc.length - 1] : "";
        return field ? `${field}: ${e.msg}` : e.msg;
      })
      .filter(Boolean)
      .join("; ");
  }
  return `Request failed (${status})`;
}

async function request<T>(path: string, options: RequestInit = {}): Promise<T> {
  const headers: Record<string, string> = {
    "Content-Type": "application/json",
    ...(options.headers as Record<string, string>),
  };
  const token = getToken();
  if (token) headers["Authorization"] = `Bearer ${token}`;

  const res = await fetch(`${BASE}${path}`, { ...options, headers });
  if (!res.ok) {
    const body = await res.json().catch(() => ({}));
    throw new Error(formatError(body, res.status));
  }
  if (res.status === 204) return undefined as T;
  return res.json();
}

// ── Types ───────────────────────────────────────────────────────────────
export interface Job {
  id: number;
  source: string;
  title: string;
  company: string | null;
  location: string | null;
  remote: boolean;
  employment_type: string;
  tags: string[];
  url: string | null;
  salary_text: string | null;
  description: string | null;
}

export interface JobMatch {
  id: number;
  job_id: number;
  score: number;
  reasons: string[];
  concerns: string[];
  summary: string | null;
  job: Job;
}

export type ApplicationStatus =
  | "saved"
  | "applied"
  | "interviewing"
  | "offer"
  | "rejected"
  | "withdrawn";

export interface Application {
  id: number;
  job_id: number;
  status: ApplicationStatus;
  tailored_resume: string | null;
  cover_letter: string | null;
  notes: string | null;
  created_at: string;
  updated_at: string;
  job: Job;
}

export interface Profile {
  skills: string[];
  desired_titles: string[];
  desired_employment_types: string[];
  locations: string[];
  remote_only: boolean;
  headline?: string | null;
  summary?: string | null;
  resume_text?: string | null;
  min_salary?: number | null;
  years_experience?: number | null;
}

// ── Endpoints ───────────────────────────────────────────────────────────
export const api = {
  register: (email: string, password: string, full_name?: string) =>
    request("/api/auth/register", {
      method: "POST",
      body: JSON.stringify({ email, password, full_name }),
    }),

  login: async (email: string, password: string) => {
    const body = new URLSearchParams({ username: email, password });
    const res = await fetch(`${BASE}/api/auth/login`, {
      method: "POST",
      headers: { "Content-Type": "application/x-www-form-urlencoded" },
      body,
    });
    if (!res.ok) throw new Error("Incorrect email or password");
    const data = await res.json();
    setToken(data.access_token);
    return data;
  },

  me: () => request("/api/auth/me"),

  getProfile: () => request<Profile | null>("/api/profile"),
  saveProfile: (profile: Profile) =>
    request<Profile>("/api/profile", {
      method: "PUT",
      body: JSON.stringify(profile),
    }),

  listJobs: (params: Record<string, string> = {}) => {
    const qs = new URLSearchParams(params).toString();
    return request<Job[]>(`/api/jobs${qs ? `?${qs}` : ""}`);
  },
  refreshJobs: () =>
    request<{ fetched: number; inserted: number; sources: Record<string, number> }>(
      "/api/jobs/refresh",
      { method: "POST" }
    ),
  seedJobs: () =>
    request<{ fetched: number; inserted: number; sources: Record<string, number> }>(
      "/api/jobs/seed",
      { method: "POST" }
    ),

  aiStatus: () => request<{ enabled: boolean }>("/api/ai/status"),
  runHunt: (instruction: string, max_jobs = 15) =>
    request<{ summary: string; matches: JobMatch[] }>("/api/ai/run", {
      method: "POST",
      body: JSON.stringify({ instruction, max_jobs }),
    }),
  matches: () => request<JobMatch[]>("/api/ai/matches"),
  autoApply: (job_id: number) =>
    request<Application>("/api/ai/auto-apply", {
      method: "POST",
      body: JSON.stringify({ job_id }),
    }),

  // Application tracking
  listApplications: () => request<Application[]>("/api/applications"),
  createApplication: (job_id: number, status: ApplicationStatus = "saved") =>
    request<Application>("/api/applications", {
      method: "POST",
      body: JSON.stringify({ job_id, status }),
    }),
  updateApplication: (
    id: number,
    patch: Partial<Pick<Application, "status" | "notes">>
  ) =>
    request<Application>(`/api/applications/${id}`, {
      method: "PATCH",
      body: JSON.stringify(patch),
    }),
  deleteApplication: (id: number) =>
    request<void>(`/api/applications/${id}`, { method: "DELETE" }),
  tailorResume: (job_id: number) =>
    request<{ tailored_resume: string }>("/api/ai/tailor-resume", {
      method: "POST",
      body: JSON.stringify({ job_id }),
    }),
  coverLetter: (job_id: number) =>
    request<{ cover_letter: string }>("/api/ai/cover-letter", {
      method: "POST",
      body: JSON.stringify({ job_id }),
    }),
};
