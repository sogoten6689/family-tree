import { ApiError, apiRequest, getBackendBaseUrl } from "@/lib/apiClient";

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

export interface SoatRow {
  trang: string;
  han: string;
  viet: string;
  /** Dòng không dùng (số trang, dấu thư viện…): không vào tệp nộp nhưng vẫn phục hồi được. */
  bo: boolean;
}

export interface SoatDraft {
  rows: SoatRow[];
  /** Các trang người soát đã xác nhận; chỉ dòng của các trang này mới được nộp. */
  da_soat: string[];
  phien_ban: number;
}

export interface NopResult {
  nop: boolean;
  so_cap: number;
  ly_do: string | null;
  tsv?: string;
  loi: { trang: string; han: string; viet: string; loi: string[] }[];
}

const soatPath = (student: string, book: string) =>
  `/api/doi-chieu/${encodeURIComponent(student)}/${encodeURIComponent(book)}/soat`;

/** Vị trí từng chữ trên ảnh, theo pixel ảnh gốc. */
export interface KhungTrang {
  rong: number;
  cao: number;
  chu: { c: string; b: [number, number, number, number] }[];
  /** Số chữ bản máy không định vị được, không có trên lớp phủ. */
  thieu: number;
}

/** null khi trang chưa có dữ liệu vị trí chữ. */
export const getKhung = (student: string, book: string, page: string) =>
  apiRequest<KhungTrang>(`${soatPath(student, book)}/khung/${encodeURIComponent(page)}`).catch((e: unknown) => {
    if (e instanceof ApiError && e.status === 404) return null;
    throw e;
  });

export const getSoat = (student: string, book: string) => apiRequest<SoatDraft>(soatPath(student, book));

export const saveSoat = (student: string, book: string, draft: SoatDraft) =>
  apiRequest<SoatDraft>(soatPath(student, book), { method: "PUT", body: JSON.stringify(draft) });

export const nopSoat = (student: string, book: string) =>
  apiRequest<NopResult>(`${soatPath(student, book)}/nop`, { method: "POST" });
