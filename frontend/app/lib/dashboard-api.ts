import { apiGet } from "./api-client";

const adminDemoContext = {
  organizationId: "org_demo",
  userId: "user_admin",
  role: "admin"
};

type ListResponse<T> = {
  items: T[];
};

export type DashboardCard = {
  label: string;
  value: number;
};

export type ChartPoint = {
  label: string;
  value: number;
};

export type ChartSeries = {
  key: string;
  label: string;
  data: ChartPoint[];
};

export type DashboardSummary = {
  role: string;
  cards: DashboardCard[];
  metrics: {
    overdue_work_items: number;
    claim_states: Record<string, number>;
    queue_status: Record<string, number>;
    support_activity: Record<string, number>;
  };
};

export type SlaAlert = {
  id: string;
  target_type: string;
  target_id: string;
  severity: string;
  status: string;
  breached_at: string;
  resolved_at: string | null;
};

export async function getDashboardSummary(): Promise<DashboardSummary> {
  return apiGet<DashboardSummary>("/dashboard/summary", adminDemoContext);
}

export async function getDashboardCharts(): Promise<ChartSeries[]> {
  const response = await apiGet<{ series: ChartSeries[] }>(
    "/dashboard/charts",
    adminDemoContext
  );
  return response.series;
}

export async function getSlaAlerts(): Promise<SlaAlert[]> {
  const response = await apiGet<ListResponse<SlaAlert>>(
    "/dashboard/alerts",
    adminDemoContext
  );
  return response.items;
}
