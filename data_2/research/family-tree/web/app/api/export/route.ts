import { exportReviewed, getDataset } from "@/lib/data";

export const dynamic = "force-dynamic";

export async function POST(req: Request) {
  const { id } = (await req.json()) as { id: string };
  const ds = getDataset(id);
  if (!ds) return Response.json({ error: "không tìm thấy dataset" }, { status: 404 });
  return Response.json(exportReviewed(ds));
}
