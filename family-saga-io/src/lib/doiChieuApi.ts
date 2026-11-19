import { ApiError, apiRequest, getBackendBaseUrl } from "@/lib/apiClient";

/** Tên đầy đủ, link bản gốc, nguồn cặp câu lấy từ danh_muc.json; null/"anh" khi chưa khai báo. */
export interface BookInfo {
  ten: string | null;
  link: string | null;
  /** "ban_dich_san": cặp nhập từ bản dịch có sẵn (Word/PDF đã dịch); "anh": tự dóng từ ảnh. */
  nguon: "anh" | "ban_dich_san";
}

/** Tổng hợp chấm mẫu của một cuốn (công khai; nhãn từng dòng chỉ admin đọc). */
export interface ChamSummary {
  checked: number;
  /** Cỡ mẫu cần chấm: 5% số cặp hợp lệ, tối thiểu 20. */
  sample: number;
  errors: number;
  by_type: { OMISSION: number; ADDITION: number; MISSING: number };
  rate: number | null;
  /** Đã chấm đủ mẫu. */
  complete: boolean;
  /** Chấm đủ mẫu và tỷ lệ lỗi ≤ ngưỡng: cặp hợp lệ của cuốn tính vào chỉ tiêu. */
  dat: boolean;
}

/** Tổng hợp vote OCR của một cuốn (nhiều engine bỏ phiếu theo dòng nền); null khi chưa có vote.json. */
export interface VoteSummary {
  pages: number;
  /** Trang Paddle khớp kém (sơ đồ cây / viết tay): bỏ phiếu Paddle, cần soát tay. */
  pages_review: number;
  chars: number;
  dong_y: number;
  de_xuat_sua: number;
  can_soat: number;
  soat_tay_dong_ngan: number;
  mot_phieu: number;
  /** Tỷ lệ chữ mọi phiếu đồng ý, trên các chữ có ≥ 2 phiếu. */
  agree_rate: number | null;
}

export type VoteKind = "dong_y" | "de_xuat_sua" | "can_soat" | "soat_tay_dong_ngan" | "mot_phieu";

export interface VoteChar {
  vi_tri: number;
  nen: string;
  phieu: Record<string, number>;
  kq: VoteKind;
}

/** Dòng ≥ 3 chữ có `chu` (chỉ chữ khác "dong_y"); dòng ngắn có `kq`. */
export interface VoteLine {
  nen: string;
  chu?: VoteChar[];
  kq?: VoteKind;
}

export interface VotePage {
  page_id: string;
  nen: string | null;
  so_phieu: number;
  paddle_khop?: number;
  trang_soat_tay?: boolean;
  dong: VoteLine[];
}

export interface VoteResult {
  summary: VoteSummary;
  pages: VotePage[];
}

/** Bộ song song sạch (chỉ nhóm chưa giao): phần người soát đã xác nhận và phần máy chưa soát, tách riêng. */
export interface BoSummary {
  da_soat: number;
  may: number;
  trang: number;
  trang_da_soat: number;
  /** Số cặp bị loại khi làm sạch, theo lý do. */
  bo: { thieu_ve: number; han_khong_co_chu_han: number; viet_lan_chu_han: number; trung: number };
  /** Số cặp phần máy đã bỏ ghi chú của người dịch máy ("(không chắc)", "(bản gốc ghi …)"…). */
  bo_ghi_chu: number;
  /** Cặp đã soát được bỏ ghi chú "(không chắc)". */
  bo_khong_chac_da_soat?: number;
  /** Cặp phần máy đã sửa tay sau khi đối chiếu ảnh (<cuon>/sua_tay.json). */
  sua_tay?: number;
  /** Phần máy: chữ đề xuất sửa của vote đã đối chiếu ảnh và áp; đang chờ đối chiếu; đối chiếu xong giữ chữ nền;
   * không tìm được chỗ; không đưa đi đối chiếu (dòng ngắn, nghi ghép lệch, dễ nhầm hình, ngày giờ/can chi). */
  sua_vote: number;
  sua_vote_cho: number;
  sua_vote_giu_nen: number;
  sua_vote_khong_khop: number;
  sua_vote_nghi_lech: number;
  /** Cặp đã sửa chữ có vế Việt dịch lại / còn dùng bản dịch máy cũ. */
  dich_lai: number;
  dich_lai_con: number;
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
  cham: ChamSummary;
  vote: VoteSummary | null;
  bo: BoSummary | null;
}

export interface StudentSummary {
  id: string;
  ten: string;
  books: BookSummary[];
  valid: number;
  pairs: number;
  format_errors: number;
  submitted: number;
  /** Chỉ số chính: cặp hợp lệ của các cuốn đã chấm đủ mẫu, tỷ lệ lỗi ≤ ngưỡng. */
  quality_pairs: number;
  /** Phần cặp hợp lệ nhập từ bản dịch có sẵn (vẫn tính vào chỉ tiêu, hệ số 1). */
  valid_ban_dich_san: number;
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
  stats: Omit<BookSummary, "id" | "tsv" | "ten" | "link" | "nguon" | "image_pages" | "cham" | "vote" | "bo">;
  cham: ChamSummary;
  vote: VoteSummary | null;
  bo: BoSummary | null;
}

const BASE = "/api/public/doi-chieu";

export const getOverview = () => apiRequest<Overview>(BASE, {}, null);

export const getBook = (student: string, book: string) =>
  apiRequest<BookDetail>(`${BASE}/${encodeURIComponent(student)}/${encodeURIComponent(book)}`, {}, null);

export const getVote = (student: string, book: string) =>
  apiRequest<VoteResult>(`${BASE}/${encodeURIComponent(student)}/${encodeURIComponent(book)}/vote`, {}, null);

export const cleanTsvUrl = (student: string, book: string, kind: "da-soat" | "may") =>
  `${getBackendBaseUrl()}${BASE}/${encodeURIComponent(student)}/${encodeURIComponent(book)}/bo-du-lieu/${kind}.tsv`;

export const pageImageUrl = (student: string, book: string, page: string) =>
  `${getBackendBaseUrl()}${BASE}/${encodeURIComponent(student)}/${encodeURIComponent(book)}/anh/${encodeURIComponent(page)}`;

/** Âm Hán Việt của một ký tự: `a` âm chọn, `k` các âm khác; không phải chữ Hán hoặc chưa có trong từ điển thì chỉ có `c`. */
export interface AmChu {
  c: string;
  a?: string;
  k?: string[];
}

/** Một cặp của bộ song song sạch, xem theo trang. */
export interface CapTrang {
  trang: string;
  han: string;
  viet: string;
  /** "da_soat": người soát đã xác nhận; "may": bản máy đã làm sạch. */
  nguon: "da_soat" | "may";
  /** Vế Hán đã sửa chữ theo vote OCR (đã đối chiếu ảnh). */
  sua_chu: boolean;
  /** Vế Việt đã dịch lại theo vế Hán đã sửa. */
  dich_lai: boolean;
  am: AmChu[];
}

export interface XemTrang {
  trang: string;
  cap: CapTrang[];
  /** Vị trí từng chữ trên ảnh; null khi trang chưa tạo khung. */
  khung: KhungTrang | null;
}

export const getXemTrang = (student: string, book: string, page: string) =>
  apiRequest<XemTrang>(`${BASE}/${encodeURIComponent(student)}/${encodeURIComponent(book)}/trang/${encodeURIComponent(page)}`, {}, null);

export interface SoatRow {
  trang: string;
  han: string;
  viet: string;
  /** Dòng không dùng (số trang, dấu thư viện…): không vào tệp nộp nhưng vẫn phục hồi được. */
  bo: boolean;
  /** Đánh dấu để chạy bổ sung; không vào tệp nộp. */
  danh_dau?: DanhDau | null;
  ghi_chu?: string | null;
  /** Mã nối dòng với gợi ý, tạo khi đánh dấu. */
  ma?: string | null;
  /** Lần chạy của gợi ý mà người soát đã bỏ. */
  bo_goi_y?: number | null;
}

export type DanhDau = "chua_dich" | "ocr";

/** Gợi ý do lần chạy bổ sung tạo, chỉ hiện để người soát nhận hoặc bỏ. */
export interface GoiY {
  han?: string;
  viet?: string;
  lan: number;
  luc?: string;
}

export interface SoatDraft {
  rows: SoatRow[];
  /** Các trang người soát đã xác nhận; chỉ dòng của các trang này mới được nộp. */
  da_soat: string[];
  phien_ban: number;
  /** Chữ bản tâm đã sửa theo trang. */
  ban_tam?: Record<string, string>;
  /** Bản dịch bản tâm đã sửa theo trang; có đủ hai vế thì trang đã xác nhận thêm một cặp khi nộp. */
  ban_tam_viet?: Record<string, string>;
  /** Bản tâm của máy và bản dịch soạn sẵn; chỉ có khi đọc nháp, không gửi lại khi lưu. */
  ban_tam_may?: Record<string, { han: string; viet?: string }>;
  /** Chỉ có khi đọc nháp; không gửi lại khi lưu. */
  goi_y?: Record<string, GoiY>;
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
  /** `u`: vị trí ước lượng, không tách được từ nét mực. `n`: ô do người soát chỉnh hoặc thêm. */
  chu: { c: string; b: [number, number, number, number]; u?: number; n?: "sua" | "them"; d?: number }[];
  /** Số chữ bản máy không định vị được, không có trên lớp phủ. */
  thieu: number;
  /** Cột in giữa ảnh (tên sách, số quyển, số trang), không thuộc các dòng soát. */
  ban_tam?: { text: string; chu: KhungTrang["chu"]; thieu: number };
  /** Trang này đang dùng ô người soát đã sửa, không phải ô máy. */
  da_sua?: boolean;
  /** Phiên bản phần ô đã sửa; chưa sửa thì không có, tức là 0. */
  phien_ban?: number;
}

export interface KhungSua {
  chu: KhungTrang["chu"];
  ban_tam_chu?: KhungTrang["chu"];
  phien_ban: number;
}

/** null khi trang chưa có dữ liệu vị trí chữ. */
export const getKhung = (student: string, book: string, page: string) =>
  apiRequest<KhungTrang>(`${soatPath(student, book)}/khung/${encodeURIComponent(page)}`).catch((e: unknown) => {
    if (e instanceof ApiError && e.status === 404) return null;
    throw e;
  });

export const saveKhung = (student: string, book: string, page: string, edit: KhungSua) =>
  apiRequest<KhungTrang>(`${soatPath(student, book)}/khung/${encodeURIComponent(page)}`, { method: "PUT", body: JSON.stringify(edit) });

/** Quay về ô máy; bản đã sửa được máy chủ giữ trong lịch sử. */
export const restoreKhung = (student: string, book: string, page: string, phienBan: number) =>
  apiRequest<KhungTrang>(`${soatPath(student, book)}/khung/${encodeURIComponent(page)}?phien_ban=${phienBan}`, { method: "DELETE" });

export const getSoat = (student: string, book: string) => apiRequest<SoatDraft>(soatPath(student, book));

export const saveSoat = (student: string, book: string, draft: SoatDraft) =>
  apiRequest<SoatDraft>(soatPath(student, book), { method: "PUT", body: JSON.stringify(draft) });

export const nopSoat = (student: string, book: string) =>
  apiRequest<NopResult>(`${soatPath(student, book)}/nop`, { method: "POST" });

export type LoaiNhanXet = "OMISSION" | "ADDITION" | "MISSING" | "chu_han" | "ten_rieng" | "dinh_dang" | "bao_cao" | "khac";

export interface MucNhanXet {
  /** Số dòng trong TSV bài nộp; không có là nhận xét chung. */
  dong?: number | null;
  loai: LoaiNhanXet;
  noi_dung: string;
}

/** Nhận xét gửi sinh viên cho một cuốn; chỉ admin đọc và ghi. */
export interface NhanXet {
  trang_thai: "nhap" | "da_duyet" | "da_gui";
  mo_dau: string;
  muc: MucNhanXet[];
  ket: string;
  phien_ban: number;
  nguoi_sua?: string;
  luu_luc?: string;
}

const nhanXetPath = (student: string, book: string) =>
  `/api/doi-chieu/${encodeURIComponent(student)}/${encodeURIComponent(book)}/nhan-xet`;

export const getNhanXet = (student: string, book: string) => apiRequest<NhanXet>(nhanXetPath(student, book));

export const saveNhanXet = (student: string, book: string, data: NhanXet) =>
  apiRequest<NhanXet>(nhanXetPath(student, book), { method: "PUT", body: JSON.stringify(data) });

export type Verdict = "dung" | "OMISSION" | "ADDITION" | "MISSING";

/** Nhãn chấm mẫu lưu trên máy chủ (chỉ admin). Khoá là số dòng; nhãn của cặp đã đổi nội dung bị bỏ. */
export interface ChamMau {
  nhan: Record<string, Verdict>;
  phien_ban: number;
  nguoi_sua?: string | null;
  luu_luc?: string | null;
}

const chamPath = (student: string, book: string) => `/api/doi-chieu/${encodeURIComponent(student)}/${encodeURIComponent(book)}/cham-mau`;

export const getChamMau = (student: string, book: string) => apiRequest<ChamMau>(chamPath(student, book));

export const saveChamMau = (student: string, book: string, data: Pick<ChamMau, "nhan" | "phien_ban">) =>
  apiRequest<ChamMau>(chamPath(student, book), { method: "PUT", body: JSON.stringify(data) });

/** Tiến độ khung chữ một cuốn: đếm thẳng từ khung/<trang>.json trên máy chủ. */
export interface TienDoCuon {
  student: string;
  book: string;
  ten: string | null;
  trang_anh: number;
  trang_khung: number;
  /** Chữ có khung (gồm cả ô ước lượng). */
  chu: number;
  /** Ô ước lượng (chia đều trong cột), chưa chắc đúng chỗ. */
  uoc: number;
  /** Chữ chưa có khung. */
  thieu: number;
  /** Lúc trang khung mới nhất được tạo (ISO, UTC). */
  cap_nhat: string | null;
}

/** Ghi chú người làm: Xong / Đang làm / Chờ anh Lâm quyết. */
export interface TrangThai {
  cap_nhat: string | null;
  xong: string[];
  dang_lam: string[];
  cho_quyet: string[];
}

export interface TienDo {
  luc: string;
  trang_thai: TrangThai | null;
  cuon: TienDoCuon[];
}

export const getTienDo = () => apiRequest<TienDo>(`${BASE}/tien-do`, {}, null);
