import type { GiaPhaItem } from "@/lib/giaPhaApi";

export type StatusFilter = "all" | "built" | "pending";
export type CodeFilter = "all" | "has" | "none";
export type SourceFilter = "all" | "catalogue" | "gemini";

export interface GiaPhaFilters {
  q: string;
  status: StatusFilter;
  code: CodeFilter;
  source: SourceFilter;
}

export const EMPTY_FILTERS: GiaPhaFilters = { q: "", status: "all", code: "all", source: "all" };

/** Bỏ dấu tiếng Việt + đ→d + chữ thường: gõ "phan gia" hay "Phan gia" đều khớp
 * "Phan gia công phả"; chữ Hán giữ nguyên. */
export function normalizeForSearch(text: string): string {
  return text
    .normalize("NFD")
    .replace(/[̀-ͯ]/g, "")
    .replace(/[đĐ]/g, "d")
    .toLowerCase()
    .trim();
}

/** Lọc danh sách Gia phả theo mã định danh / tên / họ (không phân biệt dấu,
 * mọi từ khoá phải khớp) + trạng thái + có/chưa có mã + nguồn của mã. */
export function filterGiaPha(items: GiaPhaItem[], filters: GiaPhaFilters): GiaPhaItem[] {
  const terms = normalizeForSearch(filters.q).split(/\s+/).filter(Boolean);
  return items.filter((item) => {
    if (filters.status !== "all" && item.status !== filters.status) return false;
    const hasCode = !item.ma_dinh_danh_pending;
    if (filters.code === "has" && !hasCode) return false;
    if (filters.code === "none" && hasCode) return false;
    if (filters.source !== "all" && item.ma_dinh_danh_nguon !== filters.source) return false;
    if (terms.length === 0) return true;
    const haystack = normalizeForSearch([item.id, item.title, item.ho_toc ?? ""].join(" "));
    return terms.every((term) => haystack.includes(term));
  });
}
