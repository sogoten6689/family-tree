import { checkAnswer } from "./check";
import { Review, Sample } from "./types";

export type Filter = { q?: string; st?: string; rel?: string; warn?: string; page?: string };

export function buildRows(samples: Sample[], reviews: Record<string, Review>) {
  return samples.map((s) => {
    const rv = reviews[s.key];
    const ans = rv?.answer ?? s.answer;
    return { s, rv, ans, warns: checkAnswer(ans, s.input) };
  });
}

export type Row = ReturnType<typeof buildRows>[number];

export function applyFilter(rows: Row[], sp: Filter): Row[] {
  const q = (sp.q ?? "").trim().toLowerCase();
  return rows.filter(({ s, rv, ans, warns }) => {
    if (q && !s.input.toLowerCase().includes(q) && !ans?.persons.some((p) => p.name.toLowerCase().includes(q))) return false;
    if (sp.st && (rv?.status ?? "chua") !== sp.st) return false;
    if (sp.rel === "1" && !ans?.relations.length) return false;
    if (sp.rel === "0" && ans?.relations.length) return false;
    if (sp.warn === "1" && !warns.length) return false;
    return true;
  });
}
