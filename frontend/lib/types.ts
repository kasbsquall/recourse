export type ClaimStatus =
  | "pending"
  | "in_review"
  | "approved"
  | "denied"
  | "partial";

export interface Policy {
  id: string;
  policy_number: string;
  insured_name: string;
  policy_type: string;
  state: string;
  coverage_limit: string;
  deductible: string;
  insurance_company: string;
}

export interface Message {
  id: string;
  agent_slug: string;
  agent_display_name: string;
  content: string;
  message_type: string; // case_file | message | resolution | error
  sent_at: string | null;
}

export interface Resolution {
  id: string;
  decision: string; // APPROVED | DENIED | PARTIAL | UNCLEAR
  approved_amount: string | null;
  legal_reasoning: string;
  cited_clauses: string[];
  audit_trail: Record<string, unknown>;
  approved_by: string | null;
  approved_at: string | null;
}

export interface Claim {
  id: string;
  claim_number: string;
  incident_date: string;
  incident_type: string;
  location: string | null;
  amount_requested: string;
  status: ClaimStatus;
  original_denial_reason: string | null;
  band_room_id: string | null;
  created_at: string;
  insured_name?: string | null;
}

export interface ClaimDetail extends Claim {
  incident_description: string;
  supporting_docs: SupportingDoc[];
  policy: Policy | null;
  messages: Message[];
  resolution: Resolution | null;
}

export interface SupportingDoc {
  type: string;
  ref: string;
  summary: string;
  url?: string;
}
