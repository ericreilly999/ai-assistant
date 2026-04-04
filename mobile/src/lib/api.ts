import { ActionProposal, ExecuteResponse, PlanResponse } from "../types";

const environment = (globalThis as { process?: { env?: Record<string, string | undefined> } }).process?.env ?? {};
const apiBaseUrl = environment.EXPO_PUBLIC_API_BASE_URL ?? "http://localhost:8787";

async function postJson<T>(path: string, payload: Record<string, unknown>): Promise<T> {
  const response = await fetch(`${apiBaseUrl}${path}`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
    },
    body: JSON.stringify(payload),
  });

  if (!response.ok) {
    throw new Error(`Request failed for ${path}`);
  }

  return (await response.json()) as T;
}

export async function planMessage(message: string): Promise<PlanResponse> {
  return postJson<PlanResponse>("/v1/chat/plan", {
    message,
    providers: ["google_calendar", "google_tasks", "google_drive", "microsoft_calendar", "microsoft_todo", "plaid"],
  });
}

export async function executeProposal(proposal: ActionProposal): Promise<ExecuteResponse> {
  return postJson<ExecuteResponse>("/v1/chat/execute", {
    proposal_id: proposal.proposal_id,
    provider: proposal.provider,
    action_type: proposal.action_type,
    approved: true,
    payload: proposal.payload,
    payload_hash: proposal.payload_hash,
    expires_at: proposal.expires_at,
  });
}