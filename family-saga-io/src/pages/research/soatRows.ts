/** Thao tác trên các dòng của thẻ Soát. Máy chia theo cột chữ, còn cặp nộp phải theo câu. */
import type { DanhDau, SoatRow } from "@/lib/doiChieuApi";

export interface EditRow extends SoatRow {
  key: number;
}

let nextKey = 1;

const newCode = () => `m${Date.now().toString(36)}${(nextKey++).toString(36)}`;

export const withKeys = (rows: SoatRow[]): EditRow[] => rows.map((r) => ({ ...r, key: nextKey++ }));

export const stripKeys = (rows: EditRow[]): SoatRow[] => rows.map(({ key: _key, ...r }) => r);

/** Ghép với dòng kế tiếp, kể cả khi dòng đó ở trang sau; dòng ghép giữ trang của dòng đầu. */
export const mergeWithNext = (rows: EditRow[], key: number): EditRow[] => {
  const i = rows.findIndex((r) => r.key === key);
  if (i < 0 || i === rows.length - 1) return rows;
  const [a, b] = [rows[i], rows[i + 1]];
  const merged = {
    ...a,
    han: a.han + b.han,
    viet: [a.viet.trim(), b.viet.trim()].filter(Boolean).join(" "),
    // Dòng sau đang đánh dấu thì dòng ghép vẫn phải giữ dấu đó.
    danh_dau: a.danh_dau ?? b.danh_dau,
    ma: a.danh_dau ? a.ma : (b.ma ?? a.ma),
    ghi_chu: [a.ghi_chu?.trim(), b.ghi_chu?.trim()].filter(Boolean).join("; ") || undefined,
  };
  return [...rows.slice(0, i), merged, ...rows.slice(i + 2)];
};

/** Tách tại vị trí con trỏ của từng ô; phần sau con trỏ sang dòng mới ngay bên dưới. */
export const splitRow = (rows: EditRow[], key: number, hanAt: number, vietAt: number): EditRow[] => {
  const i = rows.findIndex((r) => r.key === key);
  if (i < 0) return rows;
  const r = rows[i];
  const first = { ...r, han: r.han.slice(0, hanAt).trimEnd(), viet: r.viet.slice(0, vietAt).trimEnd() };
  const second = {
    ...r,
    key: nextKey++,
    han: r.han.slice(hanAt).trimStart(),
    viet: r.viet.slice(vietAt).trimStart(),
    // Chưa biết chỗ cần sửa nằm ở nửa nào nên giữ dấu cả hai, nhưng mã phải riêng để không dùng chung gợi ý.
    ma: r.danh_dau ? newCode() : undefined,
  };
  return [...rows.slice(0, i), first, second, ...rows.slice(i + 1)];
};

/** Bật hoặc tắt đánh dấu; bấm lại đúng loại đang chọn là tắt. Mã giữ nguyên để không mất gợi ý đã có. */
export const toggleMark = (row: SoatRow, kind: DanhDau): Partial<SoatRow> =>
  row.danh_dau === kind ? { danh_dau: undefined } : { danh_dau: kind, ma: row.ma ?? newCode() };

const HAN_RE = /[㐀-䶿一-鿿豈-﫿\u{20000}-\u{3ffff}]/u;

/** Vì sao máy nghi dòng này chưa dịch hoặc đọc không rõ. Chỉ là gợi ý: chỗ máy đọc sai mà không báo thì không bắt được. */
export const suspectOf = (row: SoatRow): { kind: DanhDau; reason: string } | null => {
  if (row.bo || !(row.han.trim() || row.viet.trim())) return null;
  if (/\[\?\]|[?？□■]/.test(row.han)) return { kind: "ocr", reason: "Chữ Hán có chỗ không đọc được" };
  if (!row.viet.trim()) return { kind: "chua_dich", reason: "Chưa có bản dịch" };
  if (HAN_RE.test(row.viet)) return { kind: "chua_dich", reason: "Bản dịch lẫn chữ Hán" };
  if (/không chắc|[?？]/i.test(row.viet)) return { kind: "chua_dich", reason: "Bản dịch có chỗ chưa chắc" };
  return null;
};

export const newRow = (trang: string): EditRow => ({ key: nextKey++, trang, han: "", viet: "", bo: false });

/** Số cặp sẽ vào tệp nộp: thuộc trang đã xác nhận, không bị bỏ, không rỗng. */
export const countSubmittable = (rows: SoatRow[], confirmed: string[]): number => {
  const pages = new Set(confirmed);
  return rows.filter((r) => pages.has(r.trang) && !r.bo && (r.han.trim() || r.viet.trim())).length;
};
