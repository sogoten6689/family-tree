import { apiRequest } from "@/lib/apiClient";

export interface SettingItem {
  key: string;
  masked_value: string | null;
  configured: boolean;
  updated_at: string | null;
}

export async function listSettings(): Promise<SettingItem[]> {
  return apiRequest<SettingItem[]>("/api/admin/settings", { method: "GET" });
}

export async function upsertSetting(key: string, value: string): Promise<SettingItem> {
  return apiRequest<SettingItem>(`/api/admin/settings/${encodeURIComponent(key)}`, {
    method: "PUT",
    body: JSON.stringify({ value }),
  });
}

export async function deleteSetting(key: string): Promise<{ deleted: string }> {
  return apiRequest<{ deleted: string }>(`/api/admin/settings/${encodeURIComponent(key)}`, {
    method: "DELETE",
  });
}

export interface OcrEngineItem {
  name: string;
  label: string;
  enabled: boolean;
  ready: boolean;
  ready_reason: string | null;
}

export interface OcrEngineConfig {
  min_enabled: number;
  engines: OcrEngineItem[];
}

export async function getOcrEngines(): Promise<OcrEngineConfig> {
  return apiRequest<OcrEngineConfig>("/api/admin/ocr-engines", { method: "GET" });
}

export async function updateOcrEngines(enabled: string[]): Promise<OcrEngineConfig> {
  return apiRequest<OcrEngineConfig>("/api/admin/ocr-engines", {
    method: "PUT",
    body: JSON.stringify({ enabled }),
  });
}

/** Engine bật được tắt không: không cho tắt nếu số engine đang bật đã chạm
 * mức tối thiểu (backend cũng chặn — đây chỉ để giao diện báo trước). */
export function canDisable(config: OcrEngineConfig, name: string): boolean {
  const enabledCount = config.engines.filter((e) => e.enabled).length;
  const engine = config.engines.find((e) => e.name === name);
  return !engine?.enabled || enabledCount > config.min_enabled;
}

export interface TextEngineConfig extends OcrEngineConfig {
  load_error: string | null;
}

export async function getTextEngines(): Promise<TextEngineConfig> {
  return apiRequest<TextEngineConfig>("/api/admin/text-engines", { method: "GET" });
}

export async function updateTextEngines(enabled: string[]): Promise<TextEngineConfig> {
  return apiRequest<TextEngineConfig>("/api/admin/text-engines", {
    method: "PUT",
    body: JSON.stringify({ enabled }),
  });
}
