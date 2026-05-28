import { apiGet } from "./api-client";

type ListResponse<T> = {
  items: T[];
};

export type InsuranceCustomer = {
  id: string;
  organization_id: string;
  name: string;
  email: string;
  phone: string | null;
  assigned_employee_id: string | null;
  created_at: string;
};

export type InsuranceCustomerRow = {
  id: string;
  name: string;
  plan: string;
  employee: string;
  status: string;
};

export async function getInsuranceCustomers(): Promise<InsuranceCustomerRow[]> {
  const response = await apiGet<ListResponse<InsuranceCustomer>>(
    "/insurance/customers"
  );
  return response.items.map((customer) => ({
    id: customer.id,
    name: customer.name,
    plan: "Policy data pending",
    employee: customer.assigned_employee_id ?? "Unassigned",
    status: "active"
  }));
}
