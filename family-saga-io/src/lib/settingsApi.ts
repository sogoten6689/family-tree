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
