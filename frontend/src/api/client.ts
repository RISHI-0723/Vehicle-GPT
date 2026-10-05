// Centralized HTTP client: base URL, JSON parsing, timeout and error classification.
// UI components never call fetch directly and never parse raw error bodies.

export const API_BASE_URL = (
  import.meta.env.VITE_API_BASE_URL ?? "http://127.0.0.1:8000"
).replace(/\/$/, "");

const REQUEST_TIMEOUT_MS = 15000;

export type ApiErrorKind = "network" | "timeout" | "http";

export class ApiError extends Error {
  readonly kind: ApiErrorKind;
  readonly status: number;

  constructor(kind: ApiErrorKind, status: number, message: string) {
    super(message);
    this.name = "ApiError";
    this.kind = kind;
    this.status = status;
  }
}

export function toApiError(err: unknown): ApiError {
  if (err instanceof ApiError) return err;
  return new ApiError("network", 0, "Network request failed");
}

export interface RequestOptions {
  method?: "GET" | "POST";
  body?: unknown;
}

export async function requestJson<T>(path: string, options: RequestOptions = {}): Promise<T> {
  const { method = "GET", body } = options;
  const controller = new AbortController();
  const timer = setTimeout(() => controller.abort(), REQUEST_TIMEOUT_MS);

  let response: Response;
  try {
    response = await fetch(`${API_BASE_URL}${path}`, {
      method,
      headers: {
        Accept: "application/json",
        ...(body !== undefined ? { "Content-Type": "application/json" } : {}),
      },
      body: body !== undefined ? JSON.stringify(body) : undefined,
      signal: controller.signal,
    });
  } catch (err) {
    const aborted = err instanceof DOMException && err.name === "AbortError";
    throw new ApiError(
      aborted ? "timeout" : "network",
      0,
      aborted ? "Request timed out" : "Network request failed",
    );
  } finally {
    clearTimeout(timer);
  }

  if (!response.ok) {
    throw new ApiError("http", response.status, `HTTP ${response.status}`);
  }
  return (await response.json()) as T;
}

export function withQuery(path: string, params: Record<string, string | number | undefined>): string {
  const search = new URLSearchParams();
  for (const [key, value] of Object.entries(params)) {
    if (value !== undefined) search.set(key, String(value));
  }
  const query = search.toString();
  return query ? `${path}?${query}` : path;
}
