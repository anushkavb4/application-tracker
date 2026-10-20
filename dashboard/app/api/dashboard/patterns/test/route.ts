import { forwardApiRequest } from "@/lib/api-proxy";

export async function POST(request: Request) {
  return forwardApiRequest("/api/admin/patterns/test", request);
}
