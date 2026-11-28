import { getDataset, saveReview } from "@/lib/data";
import { Review } from "@/lib/types";

export const dynamic = "force-dynamic";

export async function POST(req: Request) {
  const body = (await req.json()) as { id: string; key: string; review: Review | null };
  const ds = getDataset(body.id);
  if (!ds || !body.key) return Response.json({ error: "không tìm thấy dataset" }, { status: 404 });
  const review = body.review ? { ...body.review, updated_at: new Date().toISOString() } : null;
  saveReview(ds, body.key, review);
  return Response.json({ ok: true, review });
}
