export async function forwardApiRequest(endpoint: string, incoming: Request): Promise<Response> {
  const requestUrl = new URL(incoming.url);
  const apiBaseUrl = process.env.API_BASE_URL?.replace(/\/+$/, "");
  const apiKey = process.env.API_KEY;

  if (!apiBaseUrl || !apiKey) {
    return Response.json(
      { detail: "Set API_BASE_URL and API_KEY in dashboard/.env.local." },
      { status: 503, headers: { "Cache-Control": "no-store" } },
    );
  }

  try {
    const healthResponse = await fetch(`${apiBaseUrl}/health`, { cache: "no-store" });
    const health = healthResponse.ok
      ? await healthResponse.json() as { status?: string; environment?: string }
      : null;
    if (health?.status !== "ok" || typeof health.environment !== "string") {
      return Response.json(
        { detail: "API_BASE_URL did not resolve to the Application Tracker backend." },
        { status: 502, headers: { "Cache-Control": "no-store" } },
      );
    }

    const headers = new Headers({ Accept: "application/json", "X-API-Key": apiKey });
    const upstream = await fetch(`${apiBaseUrl}${endpoint}${requestUrl.search}`, {
      headers,
      cache: "no-store",
    });
    const body = await upstream.text();

    return new Response(body, {
      status: upstream.status,
      headers: {
        "Content-Type": upstream.headers.get("content-type") || "application/json",
        "Cache-Control": "no-store",
      },
    });
  } catch {
    return Response.json(
      { detail: "Application API is unavailable. Check that the backend is running." },
      { status: 502, headers: { "Cache-Control": "no-store" } },
    );
  }
}