import { ApiError, apiRequest, getBackendBaseUrl, getStoredAccessToken, parseApiError } from "@/lib/apiClient";

export type ReviewStatus = "pending" | "approved" | "rejected";

export interface VersionStep {
  step_type: "ocr" | "vote" | "transliteration" | "translation";
  status: string;
  error_message?: string | null;
}

export interface ScanVersion {
  version_id: number;
  version_number: number;
  is_current: boolean;
  status: string;
  parent_version_id: number | null;
  source: string | null;
  review_status: ReviewStatus | null;
  note: string | null;
  created_at: string | null;
  steps?: VersionStep[];
}

/** Version do engine phiên âm/dịch tạo (chạy nền ở backend). */
export const ENGINE_SOURCE_PREFIX = "engine-";

/** Trạng thái 2 bước phiên âm/dịch của 1 version engine; null nếu không phải. */
export function engineRunStatus(version: ScanVersion): "pending" | "running" | "done" | "error" | null {
  if (!version.source?.startsWith(ENGINE_SOURCE_PREFIX)) return null;
  const statuses = (version.steps ?? [])
    .filter((s) => s.step_type === "transliteration" || s.step_type === "translation")
    .map((s) => s.status);
  if (statuses.includes("error")) return "error";
  if (statuses.includes("running")) return "running";
  if (statuses.length > 0 && statuses.every((s) => s === "done")) return "done";
  return "pending";
}

export function listEnabledTextEngines(): Promise<string[]> {
  return apiRequest<string[]>("/api/user/text-engines");
}

export function runTextEngine(scanId: number, engine: string, pages?: number[]): Promise<ScanVersion> {
  return apiRequest<ScanVersion>(`/api/user/documents/${scanId}/text-engine-runs`, {
    method: "POST",
    body: JSON.stringify({ engine, pages: pages && pages.length ? pages : null }),
  });
}

export interface LlmImportRecord {
  page: number;
  cn: string;
  sv: string;
  vi: string;
}

export interface LlmImportPayload {
  source: string;
  model_note?: string;
  records: LlmImportRecord[];
}

export interface LlmImportResult {
  ok: boolean;
  dry_run: boolean;
  pages: number;
  records: number;
  skipped_annotations: number;
  errors: string[];
  warnings: string[];
  version: ScanVersion | null;
}

export function listScanVersions(scanId: number): Promise<ScanVersion[]> {
  return apiRequest<ScanVersion[]>(`/api/user/documents/${scanId}/versions`);
}

export function importLlmResults(scanId: number, payload: LlmImportPayload, dryRun: boolean): Promise<LlmImportResult> {
  return apiRequest<LlmImportResult>(`/api/user/documents/${scanId}/imports`, {
    method: "POST",
    body: JSON.stringify({ ...payload, dry_run: dryRun }),
  });
}

export function reviewVersion(scanId: number, versionId: number, reviewStatus: ReviewStatus): Promise<ScanVersion> {
  return apiRequest<ScanVersion>(`/api/user/documents/${scanId}/versions/${versionId}/review`, {
    method: "PATCH",
    body: JSON.stringify({ review_status: reviewStatus }),
  });
}

/** Tải JSONL các cặp câu đã duyệt (admin) — trả về text, không phải JSON. */
export async function fetchTrainingExport(): Promise<string> {
  const headers = new Headers();
  const token = getStoredAccessToken();
  if (token) headers.set("Authorization", `Bearer ${token}`);
  const response = await fetch(`${getBackendBaseUrl()}/api/admin/training-export`, { headers });
  if (!response.ok) throw new ApiError(await parseApiError(response), response.status);
  return response.text();
}

type ParsedFile = { records: unknown[]; source?: string; model_note?: string };

/**
 * Đọc file kết quả tool LLM. Nhận 3 dạng:
 * - JSON object `{source?, model_note?, records: [...]}`
 * - JSON array `[{page, cn, sv, vi}, ...]`
 * - JSONL: mỗi dòng 1 record; dòng có `source` mà không có `cn` là dòng mô tả.
 * Chỉ tách cấu trúc — kiểm tra nội dung (trường thiếu, trang lạ…) do backend làm.
 */
export function parseImportFile(text: string): ParsedFile {
  const trimmed = text.trim();
  if (!trimmed) throw new Error("File rỗng.");
  try {
    const data: unknown = JSON.parse(trimmed);
    if (Array.isArray(data)) return { records: data };
    if (data && typeof data === "object" && Array.isArray((data as { records?: unknown }).records)) {
      const obj = data as { records: unknown[]; source?: unknown; model_note?: unknown };
      return {
        records: obj.records,
        source: typeof obj.source === "string" ? obj.source : undefined,
        model_note: typeof obj.model_note === "string" ? obj.model_note : undefined,
      };
    }
    // 1 object đơn lẻ không có `records` → coi như JSONL 1 dòng ở dưới.
  } catch {
    // không phải JSON nguyên khối → thử JSONL
  }
  const parsed: ParsedFile = { records: [] };
  trimmed.split(/\r?\n/).forEach((line, index) => {
    if (!line.trim()) return;
    let row: unknown;
    try {
      row = JSON.parse(line);
    } catch {
      throw new Error(`Dòng ${index + 1} không phải JSON hợp lệ.`);
    }
    const obj = row as Record<string, unknown>;
    if (obj && typeof obj === "object" && !("cn" in obj) && typeof obj.source === "string") {
      parsed.source = obj.source;
      if (typeof obj.model_note === "string") parsed.model_note = obj.model_note;
      return;
    }
    parsed.records.push(row);
  });
  if (parsed.records.length === 0) throw new Error("Không tìm thấy record nào trong file.");
  return parsed;
}
