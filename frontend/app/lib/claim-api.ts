import { apiGet, apiPost, type PaginatedResponse } from "./api-client";

const employeeDemoContext = {
  organizationId: "org_demo",
  userId: "user_employee",
  role: "employee"
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

export type ClaimCorrection = {
  id: string;
  claim_id: string;
  reviewer_user_id: string;
  status: string;
  corrected_fields: Record<string, string | null>;
  changed_fields: string[];
  approved_by_user_id: string | null;
  approved_at: string | null;
  created_at: string;
};

export async function getClaimDetail(claimId: string): Promise<ClaimDetail> {
  return apiGet<ClaimDetail>(
    `/insurance/claims/${encodeURIComponent(claimId)}`,
    employeeDemoContext
  );
}

export async function getClaimHistory(claimId: string): Promise<ClaimTransition[]> {
  const response = await apiGet<PaginatedResponse<ClaimTransition>>(
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

export async function getClaimCorrections(
  claimId: string
): Promise<ClaimCorrection[]> {
  const response = await apiGet<PaginatedResponse<ClaimCorrection>>(
    `/insurance/claims/${encodeURIComponent(claimId)}/corrections`,
    employeeDemoContext
  );
  return response.items;
}

export async function saveClaimCorrection(
  claimId: string,
  correctedFields: Record<string, string | null>
): Promise<ClaimCorrection> {
  return apiPost<ClaimCorrection>(
    `/insurance/claims/${encodeURIComponent(claimId)}/corrections`,
    { corrected_fields: correctedFields },
    employeeDemoContext
  );
}

export async function approveClaimCorrection(
  claimId: string,
  correctionId: string
): Promise<ClaimCorrection> {
  return apiPost<ClaimCorrection>(
    `/insurance/claims/${encodeURIComponent(claimId)}/corrections/${encodeURIComponent(correctionId)}/approve`,
    {},
    employeeDemoContext
  );
}
