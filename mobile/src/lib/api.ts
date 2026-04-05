import { ActionProposal, ExecuteResponse, PlanResponse } from "../types";

const environment = (globalThis as { process?: { env?: Record<string, string | undefined> } }).process?.env ?? {};
const apiBaseUrl = environment.EXPO_PUBLIC_API_BASE_URL ?? "http://localhost:8787";

// ---------------------------------------------------------------------------
// Error types
// ---------------------------------------------------------------------------
export class ApiError extends Error {
  constructor(
    message: string,
    public readonly statusCode: number,
  ) {
    super(message);
    this.name = "ApiError";
  }
}

export class AuthError extends Error {
  constructor(message = "Session expired. Please sign in again.") {
    super(message);
    this.name = "AuthError";
  }
}

// ---------------------------------------------------------------------------
// Core fetch helper
// ---------------------------------------------------------------------------
async function postJson<T>(
  path: string,
  payload: Record<string, unknown>,
  idToken?: string,
): Promise<T> {
  const headers: Record<string, string> = {
    "Content-Type": "application/json",
  };
  if (idToken) {
    headers["Authorization"] = `Bearer ${idToken}`;
  }

  const response = await fetch(`${apiBaseUrl}${path}`, {
    method: "POST",
    headers,
    body: JSON.stringify(payload),
  });

  if (response.status === 401) {
    throw new AuthError();
  }

  if (!response.ok) {
    const body: { message?: string } = await response.json().catch(() => ({}));
    throw new ApiError(
      body.message ?? `Request failed for ${path} (${response.status})`,
      response.status,
    );
  }

  return (await response.json()) as T;
}

// ---------------------------------------------------------------------------
// Public API functions
// ---------------------------------------------------------------------------
export async function planMessage(message: string, idToken?: string): Promise<PlanResponse> {
  return postJson<PlanResponse>(
    "/v1/chat/plan",
    {
      message,
      providers: [
        "google_calendar",
        "google_tasks",
        "google_drive",
        "microsoft_calendar",
        "microsoft_todo",
        "plaid",
      ],
    },
    idToken,
  );
}

export async function executeProposal(
  proposal: ActionProposal,
  idToken?: string,
): Promise<ExecuteResponse> {
  return postJson<ExecuteResponse>(
    "/v1/chat/execute",
    {
      proposal_id: proposal.proposal_id,
      provider: proposal.provider,
      action_type: proposal.action_type,
      approved: true,
      payload: proposal.payload,
      payload_hash: proposal.payload_hash,
      expires_at: proposal.expires_at,
    },
    idToken,
  );
}
