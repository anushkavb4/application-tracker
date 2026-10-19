import { forwardApiRequest } from "@/lib/api-proxy";

export async function GET(request: Request) {
  return forwardApiRequest("/api/stats/summary", request);
}