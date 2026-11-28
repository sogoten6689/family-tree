"use client";
import { Answer } from "@/lib/types";
import { colorOf } from "./Highlight";

const W = 168;
const H = 46;
const GX = 22;
const GY = 64;
const PAD = 16;

/** Vẽ cây theo đời. Người thiếu đời được suy từ quan hệ; vẫn không suy được thì xếp hàng "?". */
export default function TreeView({ answer, onPick, focus }: { answer: Answer; onPick?: (n: string) => void; focus?: string | null }) {
  const persons = answer.persons;
  if (!persons.length) return <p className="muted">Không có người nào.</p>;
  const idx = new Map(persons.map((p, i) => [p.name, i]));
  const gen = new Map<string, number>();
  for (const p of persons) if (p.generation != null) gen.set(p.name, p.generation);
  // suy đời từ quan hệ
  for (let it = 0; it < 6; it++) {
    for (const r of answer.relations) {
      const a = gen.get(r.from);
      const b = gen.get(r.to);
      if (r.type === "spouse") {
        if (a != null && b == null) gen.set(r.to, a);
        if (b != null && a == null) gen.set(r.from, b);
      } else if (r.type === "father" || r.type === "mother") {
        if (a != null && b == null) gen.set(r.to, a + 1);
        if (b != null && a == null) gen.set(r.from, b - 1);
      } else {
        if (a != null && b == null) gen.set(r.to, a - 1);
        if (b != null && a == null) gen.set(r.from, b + 1);
      }
    }
  }
  const rowsKeys = [...new Set(persons.map((p) => gen.get(p.name) ?? Infinity))].sort((x, y) => x - y);
  const spouse = new Map<string, string[]>();
  for (const r of answer.relations)
    if (r.type === "spouse") {
      spouse.set(r.from, [...(spouse.get(r.from) ?? []), r.to]);
      spouse.set(r.to, [...(spouse.get(r.to) ?? []), r.from]);
    }
  const pos = new Map<string, { x: number; y: number }>();
  let maxCols = 1;
  rowsKeys.forEach((g, row) => {
    const inRow = persons.filter((p) => (gen.get(p.name) ?? Infinity) === g).map((p) => p.name);
    const ordered: string[] = [];
    for (const n of inRow) {
      if (ordered.includes(n)) continue;
      ordered.push(n);
      for (const sp of spouse.get(n) ?? []) if (inRow.includes(sp) && !ordered.includes(sp)) ordered.push(sp);
    }
    maxCols = Math.max(maxCols, ordered.length);
    ordered.forEach((n, col) => pos.set(n, { x: PAD + 56 + col * (W + GX), y: PAD + row * (H + GY) }));
  });
  const width = PAD * 2 + 56 + maxCols * (W + GX);
  const height = PAD * 2 + rowsKeys.length * (H + GY) - GY;

  const edges = answer.relations.filter((r) => pos.has(r.from) && pos.has(r.to) && r.type !== "son" && r.type !== "daughter");
  return (
    <svg width={width} height={height} style={{ display: "block" }}>
      {rowsKeys.map((g, row) => (
        <text key={g} x={PAD} y={PAD + row * (H + GY) + H / 2 + 4} fontSize={12} fill="var(--muted)">
          {g === Infinity ? "đời ?" : `đời ${g}`}
        </text>
      ))}
      {edges.map((r, k) => {
        const a = pos.get(r.from)!;
        const b = pos.get(r.to)!;
        if (r.type === "spouse") {
          const [l, rr] = a.x < b.x ? [a, b] : [b, a];
          return (
            <line key={k} x1={l.x + W} y1={l.y + H / 2} x2={rr.x} y2={rr.y + H / 2} stroke="var(--accent)" strokeDasharray="4 3" strokeWidth={1.5} />
          );
        }
        const x1 = a.x + W / 2;
        const y1 = a.y + H;
        const x2 = b.x + W / 2;
        const y2 = b.y;
        const my = (y1 + y2) / 2;
        return (
          <path
            key={k}
            d={`M${x1},${y1} C${x1},${my} ${x2},${my} ${x2},${y2}`}
            fill="none"
            stroke={r.type === "father" ? "var(--male)" : "var(--female)"}
            strokeWidth={1.4}
            opacity={0.85}
          />
        );
      })}
      {persons.map((p, i) => {
        const q = pos.get(p.name);
        if (!q) return null;
        const yrs = p.birth || p.death ? `${p.birth ?? "?"}–${p.death ?? ""}` : "";
        return (
          <g key={i} transform={`translate(${q.x},${q.y})`} onClick={() => onPick?.(p.name)} style={{ cursor: "pointer" }}>
            <rect
              width={W}
              height={H}
              rx={8}
              fill={colorOf(idx.get(p.name) ?? i)}
              stroke={focus === p.name ? "var(--accent)" : p.gender === "male" ? "#2f6fb5" : p.gender === "female" ? "#c2417a" : "#999"}
              strokeWidth={focus === p.name ? 3 : 1.5}
            />
            <text x={8} y={19} fontSize={12.5} fill="#1f2328" fontWeight={600}>
              {p.name.length > 22 ? p.name.slice(0, 21) + "…" : p.name}
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
