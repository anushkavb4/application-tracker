import type { ApiErrorCode } from "@/lib/types";

const NO_STORE = { "Cache-Control": "no-store" };

function errorResponse(code: ApiErrorCode, detail: string, status: number): Response {
  return Response.json({ code, detail }, { status, headers: NO_STORE });
}

function describeUpstreamDetail(detail: unknown): string | null {
  if (typeof detail === "string") return detail;
  if (Array.isArray(detail)) {
    const messages = detail.map((item) => {
      if (!item || typeof item !== "object") return String(item);
      const { loc, msg } = item as { loc?: unknown[]; msg?: string };
      const field = Array.isArray(loc) ? loc.filter((part) => part !== "query" && part !== "body").join(".") : "";
      return field ? `${field}: ${msg}` : msg;
    });
    return messages.filter(Boolean).join("; ") || null;
  }
  return null;
}

async function upstreamError(upstream: Response): Promise<Response> {
  let detail: string | null = null;
  try {
    detail = describeUpstreamDetail(((await upstream.json()) as { detail?: unknown }).detail);
  } catch {
    detail = null;
  }

  if (upstream.status === 401 || upstream.status === 403) {
    return errorResponse("invalid_api_key", "The backend rejected API_KEY. Make dashboard/.env.local match the backend's API_KEY.", upstream.status);
  }
  if (upstream.status === 400 || upstream.status === 422) {
    return errorResponse("validation_error", detail || "The backend rejected the request parameters.", upstream.status);
  }
  return errorResponse("backend_error", detail || `The backend returned HTTP ${upstream.status}.`, upstream.status);
}

export async function forwardApiRequest(endpoint: string, incoming: Request): Promise<Response> {
  const requestUrl = new URL(incoming.url);
  const apiBaseUrl = process.env.API_BASE_URL?.replace(/\/+$/, "");
  const apiKey = process.env.API_KEY;

  if (!apiBaseUrl || !apiKey) {
    return errorResponse("not_configured", "Set API_BASE_URL and API_KEY in dashboard/.env.local.", 503);
  }

  try {
    const healthResponse = await fetch(`${apiBaseUrl}/health`, { cache: "no-store" });
    const health = healthResponse.ok
      ? await healthResponse.json() as { status?: string; environment?: string }
      : null;
    if (health?.status !== "ok" || typeof health.environment !== "string") {
      return errorResponse("backend_unavailable", "API_BASE_URL did not resolve to the Application Tracker backend.", 502);
    }

    const headers = new Headers({ Accept: "application/json", "X-API-Key": apiKey });
    const upstream = await fetch(`${apiBaseUrl}${endpoint}${requestUrl.search}`, {
      headers,
      cache: "no-store",
    });
    if (!upstream.ok) return upstreamError(upstream);
    const body = await upstream.text();

    return new Response(body, {
      status: upstream.status,
      headers: {
        "Content-Type": upstream.headers.get("content-type") || "application/json",
        ...NO_STORE,
      },
    });
  } catch {
    return errorResponse("backend_unavailable", "Application API is unavailable. Check that the backend is running.", 502);
  }
}
