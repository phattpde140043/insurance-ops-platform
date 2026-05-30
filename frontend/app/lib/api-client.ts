const API_BASE_URL =
  process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://localhost:8000/api/v1";
const FETCH_TIMEOUT_MS = 8000;

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

export type PaginationMeta = {
  limit: number;
  sort: string;
  next_cursor: string | null;
  offset: number;
  total: number | null;
  has_more: boolean;
};

export type PaginatedResponse<T> = {
  items: T[];
  meta: PaginationMeta;
};

export type ApiErrorCode =
  | "unauthorized"
  | "forbidden"
  | "validation"
  | "timeout"
  | "backend_unavailable"
  | "request_failed";

export class ApiClientError extends Error {
  constructor(
    public readonly code: ApiErrorCode,
    message: string,
    public readonly status?: number
  ) {
    super(message);
    this.name = "ApiClientError";
  }
}

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
  return request<T>(path, {
    headers: buildDemoHeaders(context),
    cache: "no-store"
  }, 1);
}

export async function apiPost<T>(
  path: string,
  body: unknown,
  context?: DemoContext,
  idempotencyKey = crypto.randomUUID()
): Promise<T> {
  return request<T>(path, {
    method: "POST",
    headers: {
      ...buildDemoHeaders(context),
      "Content-Type": "application/json",
      "X-Idempotency-Key": idempotencyKey
    },
    body: JSON.stringify(body)
  });
}

async function request<T>(
  path: string,
  init: RequestInit,
  retries = 0
): Promise<T> {
  for (let attempt = 0; attempt <= retries; attempt += 1) {
    const controller = new AbortController();
    const timeout = setTimeout(() => controller.abort(), FETCH_TIMEOUT_MS);
    try {
      const response = await fetch(`${API_BASE_URL}${path}`, {
        ...init,
        signal: controller.signal
      });
      if (response.ok) {
        return response.json() as Promise<T>;
      }
      const error = responseError(response.status);
      if (attempt < retries && error.code === "backend_unavailable") {
        continue;
      }
      throw error;
    } catch (error) {
      if (error instanceof ApiClientError) {
        throw error;
      }
      const timedOut =
        error instanceof Error && error.name === "AbortError";
      const requestError = timedOut
        ? new ApiClientError("timeout", "Request timed out. Please retry shortly.")
        : new ApiClientError(
            "backend_unavailable",
            "Backend unavailable. Please retry shortly."
          );
      if (attempt < retries) {
        continue;
      }
      throw requestError;
    } finally {
      clearTimeout(timeout);
    }
  }
  throw new ApiClientError("request_failed", "API request failed.");
}

function responseError(status: number): ApiClientError {
  if (status === 401) {
    return new ApiClientError("unauthorized", "Authentication is required.", status);
  }
  if (status === 403) {
    return new ApiClientError("forbidden", "You do not have access to this resource.", status);
  }
  if (status === 422) {
    return new ApiClientError("validation", "Request validation failed.", status);
  }
  if (status >= 500) {
    return new ApiClientError("backend_unavailable", "Backend unavailable. Please retry shortly.", status);
  }
  return new ApiClientError("request_failed", `API request failed: ${status}`, status);
}
