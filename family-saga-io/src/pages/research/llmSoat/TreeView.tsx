import type { LlmAnswer, LlmPerson } from "@/lib/llmSoatApi";

import { inferGenerations } from "./check";
import { colorOf } from "./ui";


const W = 168;
const H = 46;
const GX = 22;
const GY = 64;
const PAD = 16;
const LEFT = 56;

/** Cây theo đời; người thiếu đời được suy từ quan hệ, vẫn không suy được thì nằm hàng "đời ?". */
export default function TreeView({ answer, focus, onPick }: { answer: LlmAnswer; focus?: string | null; onPick?: (n: string) => void }) {
  const persons = answer.persons;
  if (!persons.length) return <p className="text-muted-foreground">Không có người nào.</p>;
  const gen = inferGenerations(answer);
  const genOf = (p: LlmPerson) => gen.get(p.name) ?? Infinity;
  const rows = [...new Set(persons.map(genOf))].sort((a, b) => a - b);
  const spouse = new Map<string, string[]>();
  for (const r of answer.relations)
    if (r.type === "spouse") {
      spouse.set(r.from, [...(spouse.get(r.from) ?? []), r.to]);
      spouse.set(r.to, [...(spouse.get(r.to) ?? []), r.from]);
    }
  const pos = new Map<string, { x: number; y: number }>();
  let cols = 1;
  rows.forEach((g, row) => {
    const inRow = persons.filter((p) => genOf(p) === g).map((p) => p.name);
    const ordered: string[] = [];
    for (const n of inRow) {
      if (ordered.includes(n)) continue;
      ordered.push(n);
      for (const s of spouse.get(n) ?? []) if (inRow.includes(s) && !ordered.includes(s)) ordered.push(s);
    }
    cols = Math.max(cols, ordered.length);
    ordered.forEach((n, col) => pos.set(n, { x: PAD + LEFT + col * (W + GX), y: PAD + row * (H + GY) }));
  });
  const width = PAD * 2 + LEFT + cols * (W + GX);
  const height = PAD * 2 + rows.length * (H + GY) - GY;
  const edges = answer.relations.filter((r) => pos.has(r.from) && pos.has(r.to) && r.type !== "son" && r.type !== "daughter");

  return (
    <svg width={width} height={height} role="img" aria-label="Cây gia phả của mẫu" style={{ display: "block" }}>
      {rows.map((g, row) => (
        <text key={String(g)} x={PAD} y={PAD + row * (H + GY) + H / 2 + 4} fontSize={12} fill="currentColor" opacity={0.6}>
          {g === Infinity ? "đời ?" : `đời ${g}`}
        </text>
      ))}
      {edges.map((r, k) => {
        const a = pos.get(r.from)!;
        const b = pos.get(r.to)!;
        if (r.type === "spouse") {
          const [l, rr] = a.x < b.x ? [a, b] : [b, a];
          return <line key={k} x1={l.x + W} y1={l.y + H / 2} x2={rr.x} y2={rr.y + H / 2} stroke="#b8860b" strokeDasharray="4 3" strokeWidth={1.5} />;
        }
        const x1 = a.x + W / 2;
        const y1 = a.y + H;
        const x2 = b.x + W / 2;
        const y2 = b.y;
        const my = (y1 + y2) / 2;
        return (
          <path key={k} d={`M${x1},${y1} C${x1},${my} ${x2},${my} ${x2},${y2}`} fill="none"
            stroke={r.type === "father" ? "#2f6fb5" : "#c2417a"} strokeWidth={1.4} opacity={0.85} />
        );
      })}
      {persons.map((p, i) => {
        const q = pos.get(p.name);
        if (!q) return null;
        const yrs = p.birth || p.death ? `${p.birth ?? "?"}–${p.death ?? ""}` : "";
        const on = focus === p.name;
        return (
          <g key={i} transform={`translate(${q.x},${q.y})`} onClick={() => onPick?.(p.name)} style={{ cursor: "pointer" }}>
            <rect width={W} height={H} rx={8} fill={colorOf(i)} strokeWidth={on ? 3 : 1.5}
              stroke={on ? "#8a5a2b" : p.gender === "male" ? "#2f6fb5" : p.gender === "female" ? "#c2417a" : "#999"} />
            <text x={8} y={19} fontSize={12.5} fill="#1f2328" fontWeight={600}>
              {p.name.length > 22 ? `${p.name.slice(0, 21)}…` : p.name}
            </text>
            <text x={8} y={36} fontSize={11} fill="#4b5563">
              {(p.gender === "male" ? "♂ " : p.gender === "female" ? "♀ " : "? ") + yrs}
            </text>
          </g>
        );
      })}
    </svg>
  );
}

/** Tô mọi lần xuất hiện của tên trong đoạn văn (không phân biệt hoa thường, ưu tiên tên dài). */
export function Highlight({ text, persons, focus }: { text: string; persons: LlmPerson[]; focus?: string | null }) {
  const low = text.toLowerCase();
  const marks: { s: number; e: number; i: number }[] = [];
  const order = persons.map((p, i) => ({ p, i })).filter(({ p }) => p.name.trim()).sort((a, b) => b.p.name.length - a.p.name.length);
  for (const { p, i } of order) {
    const n = p.name.toLowerCase();
    for (let from = 0, k = low.indexOf(n); k >= 0; from = k + n.length, k = low.indexOf(n, from)) {
      const e = k + n.length;
      if (!marks.some((m) => k < m.e && e > m.s)) marks.push({ s: k, e, i });
    }
  }
  marks.sort((a, b) => a.s - b.s);
  const out: React.ReactNode[] = [];
  let cur = 0;
  for (const m of marks) {
    if (m.s > cur) out.push(text.slice(cur, m.s));
    out.push(
      <mark key={m.s} title={persons[m.i].name}
        style={{ background: colorOf(m.i), color: "#1f2328", borderRadius: 4, padding: "0 2px",
          outline: focus && persons[m.i].name === focus ? "2px solid #8a5a2b" : undefined }}>
        {text.slice(m.s, m.e)}
      </mark>,
    );
    cur = m.e;
  }
  out.push(text.slice(cur));
  return <div style={{ whiteSpace: "pre-wrap", lineHeight: 1.75, maxHeight: 520, overflow: "auto" }}>{out}</div>;
}
