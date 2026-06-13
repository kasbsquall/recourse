/** API client for the Recourse FastAPI backend. */
import type { Claim, ClaimDetail, Message, Policy } from "./types";

export const API_BASE =
  process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

async function get<T>(path: string): Promise<T> {
  const res = await fetch(`${API_BASE}${path}`, { cache: "no-store" });
  if (!res.ok) throw new Error(`${path} failed: ${res.status}`);
  return res.json();
}

async function post<T>(path: string, body?: unknown): Promise<T> {
  const res = await fetch(`${API_BASE}${path}`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: body ? JSON.stringify(body) : undefined,
    cache: "no-store",
  });
  if (!res.ok) throw new Error(`${path} failed: ${res.status}`);
  return res.json();
}

export interface NewClaimInput {
  policy_id: string;
  incident_date: string;
  incident_type: string;
  location?: string;
  incident_description: string;
  amount_requested: number;
  original_denial_reason?: string;
}

export const getPolicies = () => get<Policy[]>("/api/policies");
export const createClaim = (body: NewClaimInput) =>
  post<Claim>("/api/claims", body);

export const getClaims = () => get<Claim[]>("/api/claims");
export const getClaim = (id: string) => get<ClaimDetail>(`/api/claims/${id}`);
export const adjudicate = (id: string) =>
  post<Claim>(`/api/claims/${id}/adjudicate`);
export const approveClaim = (id: string, approvedBy: string) =>
  post<ClaimDetail>(`/api/claims/${id}/approve`, { approved_by: approvedBy });
export const reviseClaim = (id: string) =>
  post<Claim>(`/api/claims/${id}/revise`);

export const auditUrl = (id: string) => `${API_BASE}/api/claims/${id}/audit`;

/** Subscribe to the live debate stream. Returns an unsubscribe function. */
export function streamDebate(
  id: string,
  onMessage: (m: Message) => void,
  onDone?: (status: string) => void,
): () => void {
  const es = new EventSource(`${API_BASE}/api/claims/${id}/stream`);
  es.addEventListener("message", (e) => {
    try {
      onMessage(JSON.parse((e as MessageEvent).data));
    } catch {
      /* ignore malformed */
    }
  });
  es.addEventListener("done", (e) => {
    onDone?.((e as MessageEvent).data);
    es.close();
  });
  es.onerror = () => es.close();
  return () => es.close();
}
