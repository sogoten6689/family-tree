import { apiRequest } from "@/lib/apiClient";

export interface ItemVersionStep {
  step_type: "ocr" | "vote" | "transliteration" | "translation";
  status: string;
}

export interface ItemVersion {
  version_id: number;
  version_number: number;
  is_current: boolean;
  ocr_engines?: string[] | null;
  status: string;
  steps: ItemVersionStep[];
}

export interface GiaPhaItem {
  id: string;
  ma_dinh_danh_pending: boolean;
  ma_dinh_danh_nguon?: "catalogue" | "gemini" | null;
  ho_toc?: string | null;
  title: string;
  status: "built" | "pending";
  is_public?: boolean | null;
  updated_at: string;
  scan_id?: number | null;
  tree_id?: string | null;
  node_count?: number | null;
  current_version?: ItemVersion | null;
}

export interface GiaPhaListResponse {
  /** Số bộ sau khi lọc/tìm kiếm (dùng cho phân trang). */
  total: number;
  /** Chỉ trang hiện tại (hoặc tất cả nếu không truyền pageSize). */
  items: GiaPhaItem[];
  /** Số bộ trước khi lọc. */
  total_all?: number;
  page?: number;
  page_size?: number;
}

export interface GiaPhaListParams {
  page?: number;
  pageSize?: number;
  q?: string;
  status?: string;
  code?: string;
  source?: string;
  /** true = bỏ qua cache của server (nút Tải lại). */
  refresh?: boolean;
}

/** Phân trang + tìm kiếm + lọc chạy ở backend; chỉ gửi tham số khác mặc định. */
export async function listGiaPha(params: GiaPhaListParams = {}): Promise<GiaPhaListResponse> {
  const query = new URLSearchParams();
  if (params.page && params.page > 1) query.set("page", String(params.page));
  if (params.pageSize) query.set("page_size", String(params.pageSize));
  if (params.q?.trim()) query.set("q", params.q.trim());
  for (const key of ["status", "code", "source"] as const) {
    const value = params[key];
    if (value && value !== "all") query.set(key, value);
  }
  if (params.refresh) query.set("refresh", "true");
  const suffix = query.toString();
  return apiRequest<GiaPhaListResponse>(`/api/gia-pha${suffix ? `?${suffix}` : ""}`);
}

export async function listGiaPhaVersions(giaPhaId: string): Promise<ItemVersion[]> {
  return apiRequest<ItemVersion[]>(`/api/gia-pha/${encodeURIComponent(giaPhaId)}/versions`);
}

export async function cloneGiaPhaVersion(
  scanId: number,
  versionId: number,
  makeCurrent = false,
): Promise<ItemVersion> {
  return apiRequest<ItemVersion>(`/api/user/documents/${scanId}/versions/${versionId}/clone`, {
    method: "POST",
    body: JSON.stringify({ make_current: makeCurrent }),
  });
}

export interface GiaPhaSummary {
  scope: "public" | "user" | "admin";
  total: number;
  built: number;
  pending: number;
  with_code: number;
  without_code: number;
  code_source: { catalogue: number; gemini: number; other: number };
  public_trees: number;
  nodes: number;
  top_ho_toc: { ho_toc: string; count: number }[];
  /** null với khách: không lộ số liệu riêng tư. */
  pages: {
    scans: number;
    pages: number;
    ocr_pages: number;
    transliteration_pages: number;
    translation_pages: number;
    ocr_percent: number;
    transliteration_percent: number;
    translation_percent: number;
  } | null;
  generated_at: string;
}

/** Thống kê tóm tắt của phạm vi người xem (server cache 30 giây; refresh=true bỏ qua cache). */
export async function getGiaPhaSummary(refresh = false): Promise<GiaPhaSummary> {
  return apiRequest<GiaPhaSummary>(`/api/gia-pha/summary${refresh ? "?refresh=true" : ""}`);
}
