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
  total: number;
  items: GiaPhaItem[];
}

export async function listGiaPha(): Promise<GiaPhaListResponse> {
  return apiRequest<GiaPhaListResponse>("/api/gia-pha");
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
