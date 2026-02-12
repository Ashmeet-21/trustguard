const API_BASE = "/api/v1";

export async function createSession(): Promise<{ session_id: string; created_at: string; status: string }> {
  const res = await fetch(`${API_BASE}/session/create`, { method: "POST" });
  if (!res.ok) throw new Error("Failed to create session");
  return res.json();
}

export async function runVerification(
  sessionId: string,
  image?: File,
  audio?: Blob,
  behaviorData?: object
): Promise<SessionResult> {
  const formData = new FormData();
  if (image) formData.append("image", image);
  if (audio) formData.append("audio", audio, "recording.wav");
  if (behaviorData) formData.append("behavior_json", JSON.stringify(behaviorData));

  const res = await fetch(`${API_BASE}/session/${sessionId}/verify`, {
    method: "POST",
    body: formData,
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: "Verification failed" }));
    throw new Error(err.detail || "Verification failed");
  }
  return res.json();
}

export async function getAnalyticsSummary() {
  const res = await fetch(`${API_BASE}/analytics/summary`);
  if (!res.ok) return null;
  return res.json();
}

export async function getRecentActivity(limit = 10) {
  const res = await fetch(`${API_BASE}/analytics/recent?limit=${limit}`);
  if (!res.ok) return [];
  return res.json();
}

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
