"use client";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { useCallback, useEffect, useMemo, useState } from "react";
import { checkAnswer } from "@/lib/check";
import { Answer, Gender, Person, REL_TYPES, RelType, Review, ReviewStatus, Sample } from "@/lib/types";
import Highlight from "./Highlight";
import TreeView from "./TreeView";

const STATUS: Record<ReviewStatus, string> = { chua: "chưa soát", da: "đã soát", xem_lai: "cần xem lại" };
const EMPTY: Answer = { persons: [], relations: [] };
const num = (v: string) => (v.trim() === "" || isNaN(Number(v)) ? null : Number(v));
const same = (a: unknown, b: unknown) => JSON.stringify(a) === JSON.stringify(b);

type Props = {
  datasetId: string;
  sample: Sample;
  review: Review | null;
  prevHref: string | null;
  nextHref: string | null;
  phaHe: { lines: string[]; total: number } | null;
  treeId: number | null;
};

export default function Editor({ datasetId, sample, review, prevHref, nextHref, phaHe, treeId }: Props) {
  const router = useRouter();
  const original = sample.answer ?? EMPTY;
  const saved = review?.answer ?? original;
  const [ans, setAns] = useState<Answer>(saved);
  const [status, setStatus] = useState<ReviewStatus>(review?.status ?? "chua");
  const [note, setNote] = useState(review?.note ?? "");
  const [focus, setFocus] = useState<string | null>(null);
  const [msg, setMsg] = useState("");
  const dirty = !same(ans, saved) || status !== (review?.status ?? "chua") || note !== (review?.note ?? "");

  // dữ liệu trên đĩa đổi (tự làm mới) mà mình chưa sửa gì -> nhận bản mới
  useEffect(() => {
    if (!dirty) {
      setAns(review?.answer ?? sample.answer ?? EMPTY);
      setStatus(review?.status ?? "chua");
      setNote(review?.note ?? "");
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [review?.updated_at, sample.answer]);

  const warns = useMemo(() => checkAnswer(ans, sample.input), [ans, sample.input]);
  const psrc = (sample.meta?.person_src ?? {}) as Record<string, string>;
  const rsrc = (sample.meta?.relation_src ?? {}) as Record<string, string>;
  const names = ans.persons.map((p) => p.name);

  const save = useCallback(
    async (st: ReviewStatus, go?: string | null) => {
      setMsg("Đang lưu…");
      const edited = !same(ans, original);
      const body = {
        id: datasetId,
        key: sample.key,
        review: st === "chua" && !edited && !note ? null : { status: st, note, answer: edited ? ans : null },
      };
      const r = await fetch("/api/review", { method: "POST", body: JSON.stringify(body) });
      if (!r.ok) {
        setMsg("Lưu lỗi");
        return;
      }
      setStatus(st);
      setMsg(`Đã lưu lúc ${new Date().toLocaleTimeString("vi-VN")}`);
      if (go) router.push(go);
      else router.refresh();
    },
    [ans, original, note, datasetId, sample.key, router],
  );

  useEffect(() => {
    const onKey = (e: KeyboardEvent) => {
      const typing = (e.target as HTMLElement)?.closest("input,textarea,select");
      if ((e.metaKey || e.ctrlKey) && e.key === "s") {
        e.preventDefault();
        save(status);
      } else if ((e.metaKey || e.ctrlKey) && e.key === "Enter") {
        e.preventDefault();
        save("da", nextHref);
      } else if (!typing && e.altKey && e.key === "ArrowRight" && nextHref) router.push(nextHref);
      else if (!typing && e.altKey && e.key === "ArrowLeft" && prevHref) router.push(prevHref);
    };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [save, status, nextHref, prevHref, router]);

  // ---------- sửa người ----------
  const setPerson = (i: number, patch: Partial<Person>) => {
    setAns((a) => {
      const old = a.persons[i].name;
      const persons = a.persons.map((p, k) => (k === i ? { ...p, ...patch } : p));
      const nn = patch.name;
      const relations =
        nn !== undefined && nn !== old
          ? a.relations.map((r) => ({ ...r, from: r.from === old ? nn : r.from, to: r.to === old ? nn : r.to }))
          : a.relations;
      return { persons, relations };
    });
  };
  const delPerson = (i: number) =>
    setAns((a) => {
      const n = a.persons[i].name;
      return { persons: a.persons.filter((_, k) => k !== i), relations: a.relations.filter((r) => r.from !== n && r.to !== n) };
    });
  const addPerson = (name = "") =>
    setAns((a) => ({
      ...a,
      persons: [...a.persons, { name, birth: null, death: null, generation: null, gender: / thị /i.test(` ${name} `) ? "female" : null }],
    }));
  const addFromSelection = () => {
    const s = window.getSelection()?.toString().trim().replace(/\s+/g, " ");
    if (s && !names.includes(s)) addPerson(s);
    else setMsg(s ? "Người này đã có" : "Hãy bôi đen một tên trong đoạn văn trước");
  };

  // ---------- sửa quan hệ ----------
  const setRel = (i: number, patch: Partial<{ from: string; to: string; type: RelType }>) =>
    setAns((a) => ({ ...a, relations: a.relations.map((r, k) => (k === i ? { ...r, ...patch } : r)) }));
  const delRel = (i: number) => setAns((a) => ({ ...a, relations: a.relations.filter((_, k) => k !== i) }));
  const addRel = () =>
    setAns((a) => ({ ...a, relations: [...a.relations, { from: names[0] ?? "", to: names[1] ?? "", type: "father" }] }));
  const addInverse = () =>
    setAns((a) => {
      const g = new Map(a.persons.map((p) => [p.name, p.gender]));
      const have = new Set(a.relations.map((r) => `${r.from}|${r.to}|${r.type}`));
      const extra = a.relations
        .filter((r) => r.type === "father" || r.type === "mother")
        .flatMap((r) => {
          const cg = g.get(r.to);
          if (!cg) return [];
          const t: RelType = cg === "male" ? "son" : "daughter";
          return have.has(`${r.to}|${r.from}|${t}`) ? [] : [{ from: r.to, to: r.from, type: t }];
        });
      return { ...a, relations: [...a.relations, ...extra] };
    });

  return (
    <>
      <div className="toolbar">
        {prevHref ? <Link href={prevHref}>← Trước</Link> : <span className="muted">← Trước</span>}
        {nextHref ? <Link href={nextHref}>Sau →</Link> : <span className="muted">Sau →</span>}
        <span className={`chip ${status === "da" ? "ok" : status === "xem_lai" ? "warn" : ""}`}>{STATUS[status]}</span>
        {review?.answer && <span className="chip">nhãn đã sửa</span>}
        {treeId && <span className="chip">cây VGP {treeId}</span>}
        {dirty && <span className="dirty">● chưa lưu</span>}
        <span className="spacer" />
        <span className="muted small">{msg}</span>
        <button onClick={() => save(status)} disabled={!dirty} title="Ctrl/⌘ + S">Lưu</button>
        <button onClick={() => save("xem_lai")}>Cần xem lại</button>
        <button className="primary" onClick={() => save("da", nextHref)} title="Ctrl/⌘ + Enter">✓ Đã soát, sang mẫu sau</button>
        <button className="ghost" onClick={() => setAns(original)} disabled={same(ans, original)}>Khôi phục nhãn gốc</button>
      </div>

      <div className="grid2">
        <div>
          <div className="panel">
            <div className="toolbar" style={{ margin: "0 0 8px" }}>
              <b>Đoạn văn</b>
              <span className="spacer" />
              <button onClick={addFromSelection} title="Bôi đen tên trong đoạn văn rồi bấm">+ Thêm người từ chữ bôi đen</button>
            </div>
            <Highlight text={sample.input} persons={ans.persons} focus={focus} />
          </div>
          {phaHe && (
            <>
              <h2>Sơ đồ gốc (pha_he) có nhắc các tên này</h2>
              <div className="panel">
                <p className="muted small" style={{ marginTop: 0 }}>
                  {phaHe.lines.length} / {phaHe.total} dòng của sơ đồ. Số đầu dòng = đời.thứ tự.
                </p>
                <pre className="phahe">{phaHe.lines.join("\n") || "(không dòng nào khớp)"}</pre>
              </div>
            </>
          )}
          <h2>Ghi chú</h2>
          <textarea rows={3} style={{ width: "100%" }} value={note} onChange={(e) => setNote(e.target.value)} placeholder="Ghi chú khi soát (tùy chọn)" />
        </div>
        <div>
          <div className="panel svgwrap">
            <TreeView answer={ans} onPick={setFocus} focus={focus} />
            <p className="muted small" style={{ marginBottom: 0 }}>
              <span style={{ color: "var(--male)" }}>━ cha</span> · <span style={{ color: "var(--female)" }}>━ mẹ</span> ·{" "}
              <span style={{ color: "var(--accent)" }}>┅ vợ chồng</span> · bấm vào ô để tô tên trong đoạn văn
            </p>
          </div>
          {warns.length > 0 && (
            <>
              <h2>Cảnh báo ({warns.length})</h2>
              <div className="panel">
                <ul className="warnlist" style={{ margin: 0, paddingLeft: 18 }}>
                  {warns.map((w) => <li key={w}>{w}</li>)}
                </ul>
              </div>
            </>
          )}
        </div>
      </div>

      <h2>Người ({ans.persons.length})</h2>
      <div className="panel">
        <table>
          <thead>
            <tr><th>Họ tên</th><th>Sinh</th><th>Mất</th><th>Đời</th><th>Giới</th><th>Nguồn</th><th /></tr>
          </thead>
          <tbody>
            {ans.persons.map((p, i) => (
              <tr key={i} className="row" onMouseEnter={() => setFocus(p.name)}>
                <td><input className="cell" value={p.name} onChange={(e) => setPerson(i, { name: e.target.value })} /></td>
                <td><input className="cell num" value={p.birth ?? ""} onChange={(e) => setPerson(i, { birth: num(e.target.value) })} /></td>
                <td><input className="cell num" value={p.death ?? ""} onChange={(e) => setPerson(i, { death: num(e.target.value) })} /></td>
                <td><input className="cell num" value={p.generation ?? ""} onChange={(e) => setPerson(i, { generation: num(e.target.value) })} /></td>
                <td>
                  <select value={p.gender ?? ""} onChange={(e) => setPerson(i, { gender: (e.target.value || null) as Gender })}>
                    <option value="">?</option>
                    <option value="male">nam</option>
                    <option value="female">nữ</option>
                  </select>
                </td>
                <td>{psrc[p.name] ? <span className="chip">{psrc[p.name]}</span> : null}</td>
                <td><button className="ghost" onClick={() => delPerson(i)} title="Xoá người và các quan hệ của người này">✕</button></td>
              </tr>
            ))}
          </tbody>
        </table>
        <div className="toolbar" style={{ marginBottom: 0 }}>
          <button onClick={() => addPerson()}>+ Thêm người</button>
        </div>
      </div>

      <h2>Quan hệ ({ans.relations.length})</h2>
      <div className="panel">
        <table>
          <thead>
            <tr><th>Từ</th><th>là … của</th><th>Đến</th><th>Nguồn</th><th /></tr>
          </thead>
          <tbody>
            {ans.relations.map((r, i) => (
              <tr key={i} className="row">
                <td>
                  <select value={r.from} onChange={(e) => setRel(i, { from: e.target.value })}>
                    {!names.includes(r.from) && <option value={r.from}>{r.from} (không có)</option>}
                    {names.map((n) => <option key={n} value={n}>{n}</option>)}
                  </select>
                </td>
                <td>
                  <select value={r.type} onChange={(e) => setRel(i, { type: e.target.value as RelType })}>
                    {REL_TYPES.map((t) => <option key={t} value={t}>{t}</option>)}
                  </select>
                </td>
                <td>
                  <select value={r.to} onChange={(e) => setRel(i, { to: e.target.value })}>
                    {!names.includes(r.to) && <option value={r.to}>{r.to} (không có)</option>}
                    {names.map((n) => <option key={n} value={n}>{n}</option>)}
                  </select>
                </td>
                <td>{rsrc[`${r.from}|${r.to}|${r.type}`] ? <span className="chip">{rsrc[`${r.from}|${r.to}|${r.type}`]}</span> : null}</td>
                <td><button className="ghost" onClick={() => delRel(i)}>✕</button></td>
              </tr>
            ))}
          </tbody>
        </table>
        <div className="toolbar" style={{ marginBottom: 0 }}>
          <button onClick={addRel} disabled={names.length < 2}>+ Thêm quan hệ</button>
          <button onClick={addInverse} title="Từ father/mother sinh son/daughter (cần biết giới tính của con)">Tự thêm quan hệ ngược</button>
          <span className="muted small">Đọc là: «Từ» là «quan hệ» của «Đến». Ví dụ A father B = A là cha của B.</span>
        </div>
      </div>
      <p className="muted small">
        Phím tắt: <kbd>Ctrl/⌘ S</kbd> lưu · <kbd>Ctrl/⌘ Enter</kbd> đã soát và sang mẫu sau · <kbd>Alt ←/→</kbd> mẫu trước/sau
      </p>
    </>
  );
}
