const API_BASE = "/api/v1";

function getAuthHeaders(): Record<string, string> {
  if (typeof window === "undefined") return {};
  const token = localStorage.getItem("trustguard_token");
  return token ? { Authorization: `Bearer ${token}` } : {};
}

/** Read the server's error text: FastAPI sends a string, or a list of {msg} for 422s. */
async function errorMessage(res: Response, fallback: string): Promise<string> {
  const err = await res.json().catch(() => ({ detail: fallback }));
  return typeof err.detail === "string" ? err.detail : Array.isArray(err.detail) ? err.detail.map((e: { msg?: string }) => e.msg).join(", ") : fallback;
}

// ─── Auth ───────────────────────────────────────────────────────────

export async function loginUser(
  email: string,
  password: string
): Promise<{ access_token: string; token_type: string }> {
  const body = new URLSearchParams();
  body.append("username", email);
  body.append("password", password);

  const res = await fetch(`${API_BASE}/auth/login`, {
    method: "POST",
    headers: { "Content-Type": "application/x-www-form-urlencoded" },
    body,
  });
  if (!res.ok) {
    throw new Error(await errorMessage(res, "Login failed"));
  }
  return res.json();
}

export async function registerUser(
  email: string,
  password: string,
  full_name: string
): Promise<{ id: number; email: string; full_name: string }> {
  const res = await fetch(`${API_BASE}/auth/register`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ email, password, full_name }),
  });
  if (!res.ok) {
    throw new Error(await errorMessage(res, "Registration failed"));
  }
  return res.json();
}

export async function fetchProfile(): Promise<{
  id: number;
  email: string;
  full_name: string;
  is_active: boolean;
}> {
  const res = await fetch(`${API_BASE}/user/me`, {
    headers: getAuthHeaders(),
  });
  if (!res.ok) throw new Error("Not authenticated");
  return res.json();
}

// ─── Sessions ───────────────────────────────────────────────────────

export async function createSession(): Promise<{
  session_id: string;
  created_at: string;
  status: string;
  challenge: "left" | "right"; // which way the server wants the head turned
}> {
  const res = await fetch(`${API_BASE}/session/create`, {
    method: "POST",
    headers: getAuthHeaders(),
  });
  if (!res.ok) throw new Error("Failed to create session");
  return res.json();
}

export async function runVerification(
  sessionId: string,
  image?: File,
  audio?: Blob,
  behaviorData?: object,
  turnImage?: File
): Promise<SessionResult> {
  const formData = new FormData();
  if (image) formData.append("image", image);
  if (turnImage) formData.append("turn_image", turnImage);
  if (audio) formData.append("audio", audio, "recording.wav");
  if (behaviorData) formData.append("behavior_json", JSON.stringify(behaviorData));

  const res = await fetch(`${API_BASE}/session/${sessionId}/verify`, {
    method: "POST",
    headers: getAuthHeaders(),
    body: formData,
  });
  if (!res.ok) {
    throw new Error(await errorMessage(res, "Verification failed"));
  }
  return res.json();
}

// ─── Detection ──────────────────────────────────────────────────────

export interface FaceBbox {
  x_min: number;
  y_min: number;
  x_max: number;
  y_max: number;
  width_pct: number;
  height_pct: number;
}

export interface FaceCheckResult {
  faceDetected: boolean;
  livenessScore: number;
  faceBbox: FaceBbox | null;
  headYaw: number | null; // 0 = facing the camera, negative = towards your left (mirrored view)
}

export async function checkFace(image: File): Promise<FaceCheckResult> {
  const formData = new FormData();
  formData.append("file", image);

  const res = await fetch(`${API_BASE}/detect/liveness`, {
    method: "POST",
    body: formData,
  });
  if (!res.ok) {
    if (res.status === 429 || res.status >= 500) throw new Error("check unavailable"); // not the same as "no face"
    return { faceDetected: false, livenessScore: 0, faceBbox: null, headYaw: null };
  }
  const data = await res.json();
  return {
    faceDetected: data.checks?.face_detected ?? false,
    livenessScore: data.liveness_score ?? 0,
    faceBbox: data.checks?.face_bbox ?? null,
    headYaw: data.checks?.head_yaw ?? null,
  };
}

// ─── Analytics ──────────────────────────────────────────────────────

export async function getAnalyticsSummary() {
  const res = await fetch(`${API_BASE}/analytics/summary`, {
    headers: getAuthHeaders(),
  });
  if (!res.ok) return null;
  return res.json();
}

export async function getRecentActivity(limit = 10) {
  const res = await fetch(`${API_BASE}/analytics/recent?limit=${limit}`, {
    headers: getAuthHeaders(),
  });
  if (!res.ok) return [];
  return res.json();
}

// ─── Types ──────────────────────────────────────────────────────────

export interface AgentResult {
  score: number;
  risk_level: string;
  details?: Record<string, unknown>;
}

export interface SessionResult {
  session_id: string;
  trust_score: number;
  decision: "PASS" | "REVIEW" | "FAIL";
  explanation: string[];
  agents: Record<string, AgentResult>;
  overall_risk: string;
  quality_gates?: { gate: string; passed: boolean }[];
  processing_time_ms: number;
}
