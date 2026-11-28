/**
 * Chế độ nghiên cứu (VITE_RESEARCH_MODE=1): web chỉ còn phần nghiên cứu, mọi tính năng khác đóng lại,
 * gia phả chỉ xem. Máy chủ khoá ghi bằng cờ cùng tên (nlp_family_extractor/app/research_mode.py) —
 * ẩn ở đây chỉ là giao diện. Tắt cờ (mặc định) thì web như trước.
 */

export const RESEARCH_HOME = "/nghien-cuu/doi-chieu";

export function researchMode(): boolean {
  return ["1", "true", "yes"].includes(String(import.meta.env.VITE_RESEARCH_MODE ?? "").trim().toLowerCase());
}

/** Trang còn mở: nghiên cứu, gia phả công khai (chỉ xem), đăng nhập (đường dẫn riêng để soát). */
export function isResearchPath(pathname: string): boolean {
  const path = pathname.replace(/\/+$/, "") || "/";
  if (path === "/login" || path === "/403") return true;
  return ["/nghien-cuu", "/gia-pha"].some((base) => path === base || path.startsWith(`${base}/`));
}

export interface ResearchNavGroup {
  key: string;
  label: string;
  children: { key: string; label: string }[];
}

/** Menu của chế độ nghiên cứu; `key` của mục con chính là đường dẫn. */
export const RESEARCH_NAV: ResearchNavGroup[] = [
  {
    key: "research-pipeline",
    label: "OCR · Dịch · Dóng",
    children: [
      { key: RESEARCH_HOME, label: "Đối chiếu & soát" },
      { key: "/nghien-cuu/tien-do", label: "Tiến độ" },
    ],
  },
  {
    key: "research-info",
    label: "Thông tin nghiên cứu",
    children: [
      { key: "/nghien-cuu/quan-ly", label: "Quản lý nghiên cứu" },
      { key: "/nghien-cuu/on-tap", label: "Ôn tập bảo vệ" },
    ],
  },
];
