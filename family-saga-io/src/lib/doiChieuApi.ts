import { apiRequest, getBackendBaseUrl } from "@/lib/apiClient";

/** Tên đầy đủ và link bản gốc lấy từ danh_muc.json; null khi chưa khai báo. */
export interface BookInfo {
  ten: string | null;
  link: string | null;
}

export interface BookSummary extends BookInfo {
  id: string;
  tsv: string | null;
  pairs: number;
  valid: number;
  format_errors: number;
  machine_rows: number;
  machine_pages: number;
  /** Tỷ lệ chữ Hán OCR của cuốn đã có cặp sinh viên phủ tới; null khi chưa có bản máy. */
  ocr_coverage: number | null;
  /** Số ảnh trang có trên máy chủ (xem được cả khi chưa có bản máy). */
  image_pages: number;
}

export interface StudentSummary {
  id: string;
  ten: string;
  books: BookSummary[];
  valid: number;
  pairs: number;
  format_errors: number;
  submitted: number;
}

export interface Overview {
  target: number;
  error_threshold: number;
  students: StudentSummary[];
}

export interface AlignedPair {
  line: number;
  han: string;
  viet: string;
  errors: string[];
  may_han: string;
  may_viet: string;
  trang: string[];
  coverage: number;
}

export interface MissingRow {
  index: number;
  trang: string;
  dong: string;
  han: string;
  viet: string;
}

export interface BookDetail extends BookInfo {
  student: string;
  book: string;
  tsv: string | null;
  pairs: AlignedPair[];
  missing: MissingRow[];
  /** Tên các trang có ảnh, theo thứ tự. */
  pages: string[];
  stats: Omit<BookSummary, "id" | "tsv" | "ten" | "link" | "image_pages">;
}

const BASE = "/api/public/doi-chieu";

export const getOverview = () => apiRequest<Overview>(BASE, {}, null);

export const getBook = (student: string, book: string) =>
  apiRequest<BookDetail>(`${BASE}/${encodeURIComponent(student)}/${encodeURIComponent(book)}`, {}, null);

export const pageImageUrl = (student: string, book: string, page: string) =>
  `${getBackendBaseUrl()}${BASE}/${encodeURIComponent(student)}/${encodeURIComponent(book)}/anh/${encodeURIComponent(page)}`;
