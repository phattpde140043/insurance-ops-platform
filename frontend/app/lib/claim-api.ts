import { apiGet, apiPost } from "./api-client";

const employeeDemoContext = {
  organizationId: "org_demo",
  userId: "user_employee",
  role: "employee"
};

type ListResponse<T> = {
  items: T[];
};

export type ClaimDetail = {
  id: string;
  organization_id: string;
  customer_id: string;
  incident_type: string;
  description: string;
  status: string;
  claim_state: string;
  created_at: string;
  allowed_transitions: string[];
};

export type ClaimTransition = {
  id: string;
  organization_id: string;
  claim_id: string;
  actor_user_id: string;
  from_state: string | null;
  to_state: string;
  reason: string;
  created_at: string;
};

export type ClaimConversation = {
  id: string;
  customer_id: string;
  claim_id: string | null;
  status: string;
};

export async function getClaimDetail(claimId: string): Promise<ClaimDetail> {
  return apiGet<ClaimDetail>(
    `/insurance/claims/${encodeURIComponent(claimId)}`,
    employeeDemoContext
  );
}

export async function getClaimHistory(claimId: string): Promise<ClaimTransition[]> {
  const response = await apiGet<ListResponse<ClaimTransition>>(
    `/insurance/claims/${encodeURIComponent(claimId)}/history`,
    employeeDemoContext
  );
  return response.items;
}

export async function transitionClaim(
  claimId: string,
  toState: string,
  reason: string
): Promise<ClaimDetail> {
  return apiPost<ClaimDetail>(
    `/insurance/claims/${encodeURIComponent(claimId)}/transitions`,
    {
      to_state: toState,
      reason
    },
    employeeDemoContext
  );
}

export async function openClaimConversation(
  claimId: string
): Promise<ClaimConversation> {
  return apiPost<ClaimConversation>(
    `/insurance/claims/${encodeURIComponent(claimId)}/conversation`,
    {},
    employeeDemoContext
  );
}
