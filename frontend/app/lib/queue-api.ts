import { apiGet, type PaginatedResponse } from "./api-client";

const employeeDemoContext = {
  organizationId: "org_demo",
  userId: "user_employee",
  role: "employee"
};

export type QueueItem = {
  id: string;
  item_type: string;
  source_id: string;
  customer_id: string;
  employee_user_id: string | null;
  status: string;
  priority: string;
  due_at: string | null;
  created_at: string;
};

export async function getMyQueue(): Promise<QueueItem[]> {
  const response = await apiGet<PaginatedResponse<QueueItem>>(
    "/insurance/queues/my",
    employeeDemoContext
  );
  return response.items;
}
