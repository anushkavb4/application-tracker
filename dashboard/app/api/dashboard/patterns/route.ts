import { forwardApiRequest } from "@/lib/api-proxy";

export async function GET(request: Request) {
  return forwardApiRequest("/api/admin/patterns", request);
}

export async function POST(request: Request) {
  return forwardApiRequest("/api/admin/patterns", request);
}
