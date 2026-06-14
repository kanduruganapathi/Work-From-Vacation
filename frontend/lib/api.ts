// Lightweight API client for the Work From Vacation backend.

const BASE =
  process.env.NEXT_PUBLIC_API_BASE_URL || "http://localhost:8000";

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

async function request<T>(path: string, options: RequestInit = {}): Promise<T> {
  const headers: Record<string, string> = {
    "Content-Type": "application/json",
    ...(options.headers as Record<string, string>),
  };
  const token = getToken();
  if (token) headers["Authorization"] = `Bearer ${token}`;

  const res = await fetch(`${BASE}${path}`, { ...options, headers });
  if (!res.ok) {
    const detail = await res.json().catch(() => ({}));
    throw new Error(detail.detail || `Request failed: ${res.status}`);
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

  aiStatus: () => request<{ enabled: boolean }>("/api/ai/status"),
  runHunt: (instruction: string, max_jobs = 15) =>
    request<{ summary: string; matches: JobMatch[] }>("/api/ai/run", {
      method: "POST",
      body: JSON.stringify({ instruction, max_jobs }),
    }),
  matches: () => request<JobMatch[]>("/api/ai/matches"),
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
