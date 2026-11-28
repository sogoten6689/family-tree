import Link from "next/link";
import { notFound } from "next/navigation";
import Editor from "@/components/Editor";
import { getDataset, loadReviews, loadSamples, phaHeLines } from "@/lib/data";
import { applyFilter, buildRows, Filter } from "@/lib/filter";

export const dynamic = "force-dynamic";

export default async function SamplePage({
  params,
  searchParams,
}: {
  params: Promise<{ id: string; idx: string }>;
  searchParams: Promise<{ nav?: string }>;
}) {
  const { id, idx } = await params;
  const { nav = "" } = await searchParams;
  const ds = getDataset(id);
  if (!ds) notFound();
  const samples = loadSamples(ds);
  const i = Number(idx);
  const s = samples[i];
  if (!s) notFound();
  const reviews = loadReviews(ds);

  const f = Object.fromEntries(new URLSearchParams(nav)) as Filter;
  const order = applyFilter(buildRows(samples, reviews), f).map((r) => r.s.idx);
  const pos = order.indexOf(i);
  const prev = pos > 0 ? order[pos - 1] : null;
  const next = pos >= 0 && pos < order.length - 1 ? order[pos + 1] : null;

  const treeId = typeof s.meta?.tree_id === "number" ? (s.meta.tree_id as number) : null;
  const names = (reviews[s.key]?.answer ?? s.answer)?.persons.map((p) => p.name) ?? [];
  const phaHe = treeId ? phaHeLines(treeId, names) : null;
  const href = (j: number | null) => (j == null ? null : `/d/${id}/${j}?nav=${encodeURIComponent(nav)}`);

  return (
    <>
      <p className="small">
        <Link href="/">Bộ dữ liệu</Link> / <Link href={`/d/${id}?${nav}`}>{ds.label}</Link> / mẫu {i + 1}
        {pos >= 0 && <span className="muted"> · {pos + 1}/{order.length} theo bộ lọc</span>}
      </p>
      <Editor
        key={s.key}
        datasetId={id}
        sample={s}
        review={reviews[s.key] ?? null}
        prevHref={href(prev)}
        nextHref={href(next)}
        phaHe={phaHe}
        treeId={treeId}
      />
    </>
  );
}
