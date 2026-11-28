import { versionStamp } from "@/lib/data";

export const dynamic = "force-dynamic";

export function GET() {
  return Response.json({ v: versionStamp() });
}
