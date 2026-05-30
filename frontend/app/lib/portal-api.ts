import { apiGet, apiPost, type PaginatedResponse } from "./api-client";

const customerDemoContext = {
  organizationId: "org_demo",
  userId: "user_customer",
  role: "customer"
};

export type PortalCustomer = {
  id: string;
  name: string;
  email: string;
  phone: string | null;
};

export type PortalPolicy = {
  id: string;
  plan_id: string;
  status: string;
  start_date: string;
};

export type PortalIncident = {
  id: string;
  incident_type: string;
  status: string;
  created_at: string;
};

export type PortalAppointment = {
  id: string;
  employee_user_id: string;
  scheduled_at: string;
  status: string;
};

export type PortalConversation = {
  id: string;
  claim_id: string | null;
  employee_user_id: string | null;
  status: string;
  created_at: string;
};

export type PortalSummary = {
  customer: PortalCustomer;
  policies: PortalPolicy[];
  recent_incidents: PortalIncident[];
  upcoming_appointments: PortalAppointment[];
  open_conversations: PortalConversation[];
};

export async function getPortalSummary(): Promise<PortalSummary> {
  return apiGet<PortalSummary>("/insurance/portal/summary", customerDemoContext);
}

export async function getPortalPolicies(): Promise<PortalPolicy[]> {
  const response = await apiGet<PaginatedResponse<PortalPolicy>>(
    "/insurance/portal/policies",
    customerDemoContext
  );
  return response.items;
}

export async function getPortalIncidents(): Promise<PortalIncident[]> {
  const response = await apiGet<PaginatedResponse<PortalIncident>>(
    "/insurance/portal/incidents",
    customerDemoContext
  );
  return response.items;
}

export async function requestPortalAppointment(
  scheduledAt: string
): Promise<PortalAppointment> {
  return apiPost<PortalAppointment>(
    "/insurance/portal/appointments",
    { scheduled_at: scheduledAt },
    customerDemoContext
  );
}

export async function startPortalConversation(): Promise<PortalConversation> {
  return apiPost<PortalConversation>(
    "/insurance/portal/conversations",
    {},
    customerDemoContext
  );
}
