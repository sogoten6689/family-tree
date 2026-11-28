"use client";
import { Person } from "@/lib/types";

export const PALETTE = ["#f6d58e", "#a7d8f0", "#f5b3c8", "#b8e0b0", "#d7c2f0", "#f7c59f", "#a8e6e0", "#e8d3a9", "#c9d6a3", "#f0b6a8"];

export function colorOf(i: number) {
  return PALETTE[i % PALETTE.length];
}

/** Tô mọi lần xuất hiện của tên người trong đoạn văn (không phân biệt hoa thường, ưu tiên tên dài). */
export default function Highlight({ text, persons, focus }: { text: string; persons: Person[]; focus?: string | null }) {
  const low = text.toLowerCase();
  const marks: { s: number; e: number; i: number }[] = [];
  const order = persons.map((p, i) => ({ p, i })).filter(({ p }) => p.name.trim()).sort((a, b) => b.p.name.length - a.p.name.length);
  for (const { p, i } of order) {
    const n = p.name.toLowerCase();
    let from = 0;
    for (;;) {
      const k = low.indexOf(n, from);
      if (k < 0) break;
      const e = k + n.length;
      if (!marks.some((m) => k < m.e && e > m.s)) marks.push({ s: k, e, i });
      from = e;
    }
  }
  marks.sort((a, b) => a.s - b.s);
  const out: React.ReactNode[] = [];
  let cur = 0;
  for (const m of marks) {
    if (m.s > cur) out.push(text.slice(cur, m.s));
    const isFocus = focus && persons[m.i].name === focus;
    out.push(
      <mark
        key={m.s}
        className="p"
        title={persons[m.i].name}
        style={{ background: colorOf(m.i), outline: isFocus ? "2px solid var(--accent)" : undefined, color: "#1f2328" }}
      >
        {text.slice(m.s, m.e)}
      </mark>,
    );
    cur = m.e;
  }
  out.push(text.slice(cur));
  return <div className="text">{out}</div>;
}
