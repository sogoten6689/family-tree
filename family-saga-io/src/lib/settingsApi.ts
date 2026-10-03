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

export interface GeminiUsageTask {
  task: string;
  calls: number;
  errors: number;
  prompt_tokens: number;
  output_tokens: number;
  thinking_tokens: number;
  total_tokens: number;
  avg_tokens_per_call: number;
  avg_duration_ms: number;
}

export interface GeminiUsageSummary {
  days: number;
  tasks: GeminiUsageTask[];
  total_tokens: number;
  total_calls: number;
}

export async function getGeminiUsage(days: number): Promise<GeminiUsageSummary> {
  return apiRequest<GeminiUsageSummary>(`/api/admin/gemini-usage?days=${days}`, { method: "GET" });
}

/** Tỉ lệ token thinking / tổng (0–1); null khi chưa có token nào. */
export function thinkingShare(summary: GeminiUsageSummary): number | null {
  if (summary.total_tokens === 0) return null;
  return summary.tasks.reduce((sum, t) => sum + t.thinking_tokens, 0) / summary.total_tokens;
}
