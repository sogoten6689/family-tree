/** Chấm mẫu lỗi theo Guideline CV mục 7–8: lấy mẫu cặp, gắn nhãn, tính tỷ lệ lỗi. */

export type Verdict = "dung" | "OMISSION" | "ADDITION" | "MISSING";

export const VERDICT_LABEL: Record<Verdict, string> = {
  dung: "Đúng",
  OMISSION: "OMISSION – thiếu ý",
  ADDITION: "ADDITION – thừa ý",
  MISSING: "MISSING – thiếu vế/cặp",
};

export const SAMPLE_RATE = 0.05;
export const SAMPLE_MIN = 20;

/** Số ngẫu nhiên có hạt giống: cùng sinh viên + cùng cuốn luôn ra cùng mẫu, chấm lại không bị đổi. */
const mulberry32 = (seed: number) => () => {
  seed = (seed + 0x6d2b79f5) | 0;
  let t = Math.imul(seed ^ (seed >>> 15), 1 | seed);
  t = (t + Math.imul(t ^ (t >>> 7), 61 | t)) ^ t;
  return ((t ^ (t >>> 14)) >>> 0) / 4294967296;
};

const hash = (s: string) => {
  let h = 2166136261;
  for (const ch of s) h = Math.imul(h ^ ch.codePointAt(0)!, 16777619);
  return h >>> 0;
};

/** Trả về số dòng (line) của các cặp được chọn, theo thứ tự tăng dần. */
export const sampleLines = (lines: number[], key: string, rate = SAMPLE_RATE, min = SAMPLE_MIN): number[] => {
  const n = Math.min(lines.length, Math.max(min, Math.ceil(lines.length * rate)));
  const rand = mulberry32(hash(key));
  const pool = [...lines];
  for (let i = pool.length - 1; i > 0; i--) {
    const j = Math.floor(rand() * (i + 1));
    [pool[i], pool[j]] = [pool[j], pool[i]];
  }
  return pool.slice(0, n).sort((a, b) => a - b);
};

export interface GradeSummary {
  checked: number;
  errors: number;
  rate: number | null;
  byType: Record<Exclude<Verdict, "dung">, number>;
}

export const summarize = (verdicts: Record<number, Verdict>): GradeSummary => {
  const byType = { OMISSION: 0, ADDITION: 0, MISSING: 0 };
  let checked = 0;
  for (const v of Object.values(verdicts)) {
    checked++;
    if (v !== "dung") byType[v]++;
  }
  const errors = byType.OMISSION + byType.ADDITION + byType.MISSING;
  return { checked, errors, rate: checked ? errors / checked : null, byType };
};

const csvCell = (s: string) => (/[",\n]/.test(s) ? `"${s.replace(/"/g, '""')}"` : s);

export const toCsv = (rows: { line: number; han: string; viet: string; verdict: Verdict | undefined }[]) =>
  "﻿" +
  [["dong", "han", "viet", "nhan"], ...rows.map((r) => [String(r.line), r.han, r.viet, r.verdict ?? ""])]
    .map((r) => r.map(csvCell).join(","))
    .join("\n");

/** Đánh dấu chữ Hán của sinh viên không xuất hiện trong đoạn OCR tương ứng (thường là chữ đã sửa). */
export const markChangedChars = (han: string, ocr: string): { ch: string; changed: boolean }[] => {
  const seen = new Set(Array.from(ocr));
  const isHan = /\p{Script=Han}/u;
  return Array.from(han).map((ch) => ({ ch, changed: isHan.test(ch) && !seen.has(ch) }));
};

export const storageKey = (student: string, book: string) => `doi-chieu:cham:${student}/${book}`;

export const loadVerdicts = (key: string): Record<number, Verdict> => {
  try {
    const raw = localStorage.getItem(key);
    return raw ? (JSON.parse(raw) as Record<number, Verdict>) : {};
  } catch {
    return {};
  }
};

export const saveVerdicts = (key: string, v: Record<number, Verdict>) => {
  try {
    localStorage.setItem(key, JSON.stringify(v));
  } catch {
    // trình duyệt chặn lưu thì vẫn chấm được trong phiên, chỉ không nhớ khi tải lại
  }
};
