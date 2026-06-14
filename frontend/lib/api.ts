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

export type TaskStatus = "queued" | "running" | "done" | "error";

export interface Task {
  id: number;
  kind: string;
  status: TaskStatus;
  progress: number;
  message: string | null;
  result: Record<string, unknown> | null;
}

export interface Notification {
  id: number;
  type: string;
  title: string;
  body: string | null;
  job_id: number | null;
  read: boolean;
  created_at: string;
}

export interface InterviewPrep {
  likely_questions: string[];
  talking_points: string[];
  focus_areas: string[];
  summary: string | null;
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
  autopilot_enabled: boolean;
  autopilot_min_score: number;
  autopilot_daily_limit: number;
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
  uploadResume: async (file: File): Promise<Profile> => {
    // Multipart upload — let the browser set the Content-Type boundary.
    const form = new FormData();
    form.append("file", file);
    const headers: Record<string, string> = {};
    const token = getToken();
    if (token) headers["Authorization"] = `Bearer ${token}`;
    const res = await fetch(`${BASE}/api/profile/resume`, {
      method: "POST",
      headers,
      body: form,
    });
    if (!res.ok) {
      const body = await res.json().catch(() => ({}));
      throw new Error(formatError(body, res.status));
    }
    return res.json();
  },

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

  // Background AI tasks
  runHuntAsync: (instruction: string, max_jobs = 15) =>
    request<Task>("/api/ai/run-async", {
      method: "POST",
      body: JSON.stringify({ instruction, max_jobs }),
    }),
  scoreNew: () => request<Task>("/api/ai/score-new", { method: "POST" }),
  batchApply: (min_score = 80, limit = 5) =>
    request<Task>("/api/ai/batch-apply", {
      method: "POST",
      body: JSON.stringify({ min_score, limit }),
    }),
  getTask: (id: number) => request<Task>(`/api/ai/tasks/${id}`),
  interviewPrep: (job_id: number) =>
    request<InterviewPrep>("/api/ai/interview-prep", {
      method: "POST",
      body: JSON.stringify({ job_id }),
    }),

  // Notifications
  notifications: () => request<Notification[]>("/api/notifications"),
  markRead: (id: number) =>
    request<Notification>(`/api/notifications/${id}/read`, { method: "POST" }),
  markAllRead: () =>
    request<void>("/api/notifications/read-all", { method: "POST" }),

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
    patch: Partial<
      Pick<Application, "status" | "notes" | "tailored_resume" | "cover_letter">
    >
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

// Poll a background task until it finishes, calling onUpdate on each tick.
export async function pollTask(
  id: number,
  onUpdate: (t: Task) => void,
  intervalMs = 1500
): Promise<Task> {
  for (;;) {
    const t = await api.getTask(id);
    onUpdate(t);
    if (t.status === "done" || t.status === "error") return t;
    await new Promise((r) => setTimeout(r, intervalMs));
  }
}
