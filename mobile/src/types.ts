export type ActionProposal = {
  proposal_id: string;
  provider: string;
  action_type: string;
  resource_type: string;
  payload: Record<string, unknown>;
  payload_hash: string;
  summary: string;
  risk_level: string;
  requires_confirmation: boolean;
  expires_at: string;
};

export type PlanResponse = {
  intent: string;
  message: string;
  proposals: ActionProposal[];
  sources: Array<Record<string, string>>;
  warnings: string[];
};

export type ExecuteResponse = {
  message: string;
  provider: string;
  action_type: string;
  receipt: Record<string, unknown>;
  resource: Record<string, unknown>;
};