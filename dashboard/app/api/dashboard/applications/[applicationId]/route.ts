import { forwardApiRequest } from "@/lib/api-proxy";

export async function PATCH(
  request: Request,
  { params }: { params: Promise<{ applicationId: string }> },
) {
  const { applicationId } = await params;
  return forwardApiRequest(`/api/applications/${encodeURIComponent(applicationId)}`, request);
}