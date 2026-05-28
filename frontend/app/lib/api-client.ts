const API_BASE_URL =
  process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://localhost:8000/api/v1";

const demoHeaders = {
  "X-Organization-Id": "org_demo",
  "X-User-Id": "user_admin",
  "X-Role": "admin"
};

type DemoContext = {
  organizationId?: string;
  userId?: string;
  role?: string;
};

function buildDemoHeaders(context?: DemoContext) {
  return {
    "X-Organization-Id": context?.organizationId ?? demoHeaders["X-Organization-Id"],
    "X-User-Id": context?.userId ?? demoHeaders["X-User-Id"],
    "X-Role": context?.role ?? demoHeaders["X-Role"]
  };
}

export async function apiGet<T>(
  path: string,
  context?: DemoContext
): Promise<T> {
  const response = await fetch(`${API_BASE_URL}${path}`, {
    headers: buildDemoHeaders(context),
    cache: "no-store"
  });

  if (!response.ok) {
    throw new Error(`API request failed: ${response.status}`);
  }

  return response.json() as Promise<T>;
}

export async function apiPost<T>(
  path: string,
  body: unknown,
  context?: DemoContext
): Promise<T> {
  const response = await fetch(`${API_BASE_URL}${path}`, {
    method: "POST",
    headers: {
      ...buildDemoHeaders(context),
      "Content-Type": "application/json"
    },
    body: JSON.stringify(body)
  });

  if (!response.ok) {
    throw new Error(`API request failed: ${response.status}`);
  }

  return response.json() as Promise<T>;
}
