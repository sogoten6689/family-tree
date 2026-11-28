import Link from "next/link";
import { notFound } from "next/navigation";
import ExportButton from "@/components/ExportButton";
import { getDataset, loadReviews, loadSamples } from "@/lib/data";
import { applyFilter, buildRows, Filter } from "@/lib/filter";

export const dynamic = "force-dynamic";
const PAGE = 50;
const STATUS: Record<string, string> = { chua: "chưa soát", da: "đã soát", xem_lai: "cần xem lại" };

type SP = Filter;

export default async function DatasetPage({ params, searchParams }: { params: Promise<{ id: string }>; searchParams: Promise<SP> }) {
  const { id } = await params;
  const sp = await searchParams;
  const ds = getDataset(id);
  if (!ds) notFound();
  const samples = loadSamples(ds);
  const reviews = loadReviews(ds);

  const rows = buildRows(samples, reviews);
  const filtered = applyFilter(rows, sp);
  const page = Math.max(1, Number(sp.page ?? 1));
  const pages = Math.max(1, Math.ceil(filtered.length / PAGE));
  const shown = filtered.slice((page - 1) * PAGE, page * PAGE);
  const qs = (o: Partial<SP>) => {
    const u = new URLSearchParams(Object.entries({ ...sp, ...o }).filter(([, v]) => v) as [string, string][]);
    return `?${u}`;
  };
  // danh sách idx theo bộ lọc để trang chi tiết có nút trước/sau
  const nav = encodeURIComponent(qs({ page: undefined }).slice(1));

  const nDone = Object.values(reviews).filter((r) => r.status === "da").length;
  return (
    <>
      <p className="small">
        <Link href="/">← Bộ dữ liệu</Link>
      </p>
      <h1>{ds.label}</h1>
      <p className="muted small">{ds.path}</p>
      <div className="stats">
        <div className="stat"><b>{samples.length}</b>mẫu</div>
        <div className="stat"><b>{rows.filter((r) => r.ans?.relations.length).length}</b>có quan hệ</div>
        <div className="stat"><b>{rows.filter((r) => r.warns.length).length}</b>có cảnh báo</div>
        <div className="stat"><b>{nDone}</b>đã soát</div>
        <div className="stat"><b>{Object.values(reviews).filter((r) => r.answer).length}</b>đã sửa nhãn</div>
      </div>
      <form className="filters">
        <input name="q" defaultValue={sp.q} placeholder="Tìm chữ hoặc tên người" />
        <select name="st" defaultValue={sp.st ?? ""}>
          <option value="">Mọi trạng thái</option>
          {Object.entries(STATUS).map(([k, v]) => (
            <option key={k} value={k}>{v}</option>
          ))}
        </select>
        <select name="rel" defaultValue={sp.rel ?? ""}>
          <option value="">Có/không quan hệ</option>
          <option value="1">Có quan hệ</option>
          <option value="0">Không có quan hệ</option>
        </select>
        <select name="warn" defaultValue={sp.warn ?? ""}>
          <option value="">Mọi mẫu</option>
          <option value="1">Chỉ mẫu có cảnh báo</option>
        </select>
        <button type="submit">Lọc</button>
        <span className="muted small">{filtered.length} mẫu khớp</span>
        <span style={{ flex: 1 }} />
        <ExportButton id={id} />
      </form>
      <div className="panel">
        <table>
          <thead>
            <tr>
              <th>#</th>
              <th>Đoạn văn</th>
              <th>Người</th>
              <th>Quan hệ</th>
              <th>Cảnh báo</th>
              <th>Trạng thái</th>
            </tr>
          </thead>
          <tbody>
            {shown.map(({ s, rv, ans, warns }) => (
              <tr className="row" key={s.idx}>
                <td><Link href={`/d/${id}/${s.idx}?nav=${nav}`}>{s.idx + 1}</Link></td>
                <td className="small">
                  <Link href={`/d/${id}/${s.idx}?nav=${nav}`} style={{ color: "inherit" }}>
                    {s.input.slice(0, 160)}{s.input.length > 160 ? "…" : ""}
                  </Link>
                  {s.meta?.tree_id ? <span className="chip">cây {String(s.meta.tree_id)}</span> : null}
                </td>
                <td>{ans?.persons.length ?? "–"}</td>
                <td>{ans?.relations.length ?? "–"}</td>
                <td>{warns.length ? <span className="chip warn">{warns.length}</span> : ""}</td>
                <td>
                  <span className={`chip ${rv?.status === "da" ? "ok" : rv?.status === "xem_lai" ? "warn" : ""}`}>
                    {STATUS[rv?.status ?? "chua"]}
                  </span>
                  {rv?.answer ? <span className="chip">đã sửa</span> : null}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
        <div className="pager">
          {page > 1 && <Link href={qs({ page: String(page - 1) })}>← Trước</Link>}
          <span className="muted small">Trang {page}/{pages}</span>
          {page < pages && <Link href={qs({ page: String(page + 1) })}>Sau →</Link>}
        </div>
      </div>
    </>
  );
}
