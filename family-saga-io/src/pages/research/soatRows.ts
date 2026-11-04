/** Thao tác trên các dòng của thẻ Soát. Máy chia theo cột chữ, còn cặp nộp phải theo câu. */
import type { SoatRow } from "@/lib/doiChieuApi";

export interface EditRow extends SoatRow {
  key: number;
}

let nextKey = 1;

export const withKeys = (rows: SoatRow[]): EditRow[] => rows.map((r) => ({ ...r, key: nextKey++ }));

export const stripKeys = (rows: EditRow[]): SoatRow[] => rows.map(({ key: _key, ...r }) => r);

/** Ghép với dòng kế tiếp, kể cả khi dòng đó ở trang sau; dòng ghép giữ trang của dòng đầu. */
export const mergeWithNext = (rows: EditRow[], key: number): EditRow[] => {
  const i = rows.findIndex((r) => r.key === key);
  if (i < 0 || i === rows.length - 1) return rows;
  const [a, b] = [rows[i], rows[i + 1]];
  const merged = { ...a, han: a.han + b.han, viet: [a.viet.trim(), b.viet.trim()].filter(Boolean).join(" ") };
  return [...rows.slice(0, i), merged, ...rows.slice(i + 2)];
};

/** Tách tại vị trí con trỏ của từng ô; phần sau con trỏ sang dòng mới ngay bên dưới. */
export const splitRow = (rows: EditRow[], key: number, hanAt: number, vietAt: number): EditRow[] => {
  const i = rows.findIndex((r) => r.key === key);
  if (i < 0) return rows;
  const r = rows[i];
  const first = { ...r, han: r.han.slice(0, hanAt).trimEnd(), viet: r.viet.slice(0, vietAt).trimEnd() };
  const second = { ...r, key: nextKey++, han: r.han.slice(hanAt).trimStart(), viet: r.viet.slice(vietAt).trimStart() };
  return [...rows.slice(0, i), first, second, ...rows.slice(i + 1)];
};

export const newRow = (trang: string): EditRow => ({ key: nextKey++, trang, han: "", viet: "", bo: false });

/** Số cặp sẽ vào tệp nộp: thuộc trang đã xác nhận, không bị bỏ, không rỗng. */
export const countSubmittable = (rows: SoatRow[], confirmed: string[]): number => {
  const pages = new Set(confirmed);
  return rows.filter((r) => pages.has(r.trang) && !r.bo && (r.han.trim() || r.viet.trim())).length;
};
