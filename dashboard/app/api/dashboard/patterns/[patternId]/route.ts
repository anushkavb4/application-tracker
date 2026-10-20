import { forwardApiRequest } from "@/lib/api-proxy";

export async function PATCH(
  request: Request,
  { params }: { params: Promise<{ patternId: string }> },
) {
  const { patternId } = await params;
  return forwardApiRequest(`/api/admin/patterns/${encodeURIComponent(patternId)}`, request);
}

export async function DELETE(
  request: Request,
  { params }: { params: Promise<{ patternId: string }> },
) {
  const { patternId } = await params;
  return forwardApiRequest(`/api/admin/patterns/${encodeURIComponent(patternId)}`, request);
}
