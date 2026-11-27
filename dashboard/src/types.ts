export type ClaimState =
  "waiting" | "in progress" | "waiting for sign-off" | "decided";

export type DecisionKind = "approve" | "decline" | "refer";

export interface QueueRow {
  claim_id: string;
  customer_name: string;
  claim_type: string;
  amount_claimed: number;
  state: ClaimState;
  decision: DecisionKind | null;
  payout: number | null;
}

export interface Item {
  description: string;
  category: string;
  amount: number;
}

export interface Document {
  name: string;
  type: string;
  content: string;
}

export interface Claim {
  claim_id: string;
  policy_id: string;
  claim_type: string;
  submitted_on: string;
  incident_date: string;
  incident_location: string;
  summary: string;
  story: string;
  items: Item[];
  amount_claimed: number;
  documents: Document[];
}

export interface PreviousClaim {
  claim_id: string;
  filed_on: string;
  claim_type: string;
  summary: string;
  outcome: string;
  amount_paid: number;
}

export interface Customer {
  customer_id: string;
  name: string;
  customer_since: string;
  previous_claims: PreviousClaim[];
}

export interface Policy {
  policy_id: string;
  plan: string;
  add_ons: string[];
  trip: {
    destination: string;
    departs_on: string;
    returns_on: string;
  };
  travelers: string[];
}

export interface Plan {
  plan: string;
  name: string;
}

export interface AddOn {
  add_on: string;
  name: string;
}

export interface Decision {
  decision: DecisionKind;
  payout: number;
  explanation: string;
  policy_section: string;
  decided_at: string;
  signed_off_at: string | null;
}

export interface Payment {
  amount: number;
  paid_at: string;
}

export interface ClaimView {
  claim: Claim;
  customer: Customer;
  policy: Policy;
  plan: Plan;
  add_ons: AddOn[];
  state: ClaimState;
  decision: Decision | null;
  payments: Payment[];
  paid_total: number;
}

export interface ClaimEvent {
  kind: string;
  text: string;
  created_at: string;
}
