import { apiGet, apiPost } from "./api-client";

const employeeDemoContext = {
  organizationId: "org_demo",
  userId: "user_employee",
  role: "employee"
};

type ListResponse<T> = {
  items: T[];
};

export type SupportConversation = {
  id: string;
  organization_id: string;
  customer_id: string;
  employee_user_id: string | null;
  status: string;
  created_at: string;
};

export type SupportMessage = {
  id: string;
  organization_id: string;
  conversation_id: string;
  sender_user_id: string | null;
  role: string;
  body: string;
  citations: string[];
  created_at: string;
};

export type SupportConversationDetail = SupportConversation & {
  messages: SupportMessage[];
};

export async function getSupportConversations(): Promise<SupportConversation[]> {
  const response = await apiGet<ListResponse<SupportConversation>>(
    "/insurance/conversations",
    employeeDemoContext
  );
  return response.items;
}

export async function getSupportConversation(
  conversationId: string
): Promise<SupportConversationDetail> {
  return apiGet<SupportConversationDetail>(
    `/insurance/conversations/${encodeURIComponent(conversationId)}`,
    employeeDemoContext
  );
}

export async function sendSupportMessage(
  conversationId: string,
  body: string,
  useAi = true
): Promise<SupportMessage> {
  return apiPost<SupportMessage>(
    `/insurance/conversations/${encodeURIComponent(conversationId)}/messages`,
    {
      body,
      use_ai: useAi
    },
    employeeDemoContext
  );
}
