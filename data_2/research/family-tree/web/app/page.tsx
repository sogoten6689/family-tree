import Link from "next/link";
import { DATA_REPO, listDatasets, loadReviews, loadSamples } from "@/lib/data";

export const dynamic = "force-dynamic";

export default function Home() {
  const ds = listDatasets();
  const groups = [...new Set(ds.map((d) => d.group))];
  return (
    <>
      <h1>Bộ dữ liệu</h1>
      {!DATA_REPO && (
        <p className="chip warn">Không tìm thấy thư mục data/ (VGP). Đặt biến DATA_REPO nếu cần.</p>
      )}
      {groups.map((g) => (
        <section key={g}>
          <h2>{g}</h2>
          <div className="panel">
            <table>
              <thead>
                <tr>
                  <th>File</th>
                  <th>Mẫu</th>
                  <th>Có quan hệ</th>
                  <th>Người / mẫu</th>
                  <th>Đã soát</th>
                  <th>Cần xem lại</th>
                  <th>Sửa lúc</th>
                </tr>
              </thead>
              <tbody>
                {ds
                  .filter((d) => d.group === g)
                  .map((d) => {
                    const s = loadSamples(d);
                    const rv = Object.values(loadReviews(d));
                    const withRel = s.filter((x) => x.answer?.relations?.length).length;
                    const persons = s.reduce((a, x) => a + (x.answer?.persons?.length ?? 0), 0);
                    return (
                      <tr className="row" key={d.id}>
                        <td>
                          <Link href={`/d/${d.id}`}>{d.label}</Link>
                        </td>
                        <td>{s.length}</td>
                        <td>{withRel}</td>
                        <td>{s.length ? (persons / s.length).toFixed(1) : "–"}</td>
                        <td>{rv.filter((r) => r.status === "da").length}</td>
                        <td>{rv.filter((r) => r.status === "xem_lai").length}</td>
                        <td className="muted small">{new Date(d.mtimeMs).toLocaleString("vi-VN")}</td>
                      </tr>
                    );
                  })}
              </tbody>
            </table>
          </div>
        </section>
      ))}
    </>
  );
}
