import { apiRequest } from "@/lib/apiClient";
import type { BalkanNode, FamilyTreeDocument, FamilyTreeListResponse } from "@/lib/familyTreeApi";

export type OcrStatus = "pending" | "processing" | "completed" | "failed" | "skipped";
export type TreeStatus = "none" | "draft" | "created";

export interface UserStats {
  scanned_documents: number;
  family_trees: number;
  history_total: number;
}

export interface UserScan {
  id: number;
  title: string;
  file_name: string;
  file_type: string;
  page_count: number;
  uploaded_at: string;
  ocr_status: OcrStatus;
  tree_status: TreeStatus;
  family_tree_id?: string | null;
  request_id?: string | null;
}

export interface UserScanListResponse {
  total: number;
  items: UserScan[];
}

export interface AdminStats {
  total_trees: number;
  public_trees: number;
  total_users: number;
  total_scans: number;
  history_total: number;
}

export interface AdminHistoryItem {
  request_id: string;
  created_at: string;
  source: string;
  metadata: Record<string, unknown>;
  people_count: number;
  relationship_count: number;
  warning_count: number;
  user_id?: number | null;
}

export interface AdminHistoryResponse {
  total: number;
  items: AdminHistoryItem[];
}

export async function getUserStats(): Promise<UserStats> {
  return apiRequest<UserStats>("/api/user/stats");
}

export async function listUserDocuments(): Promise<UserScanListResponse> {
  return apiRequest<UserScanListResponse>("/api/user/documents");
}

export async function createUserDocument(payload: {
  title: string;
  file_name: string;
  file_type: string;
  page_count?: number;
  source_text?: string;
}): Promise<UserScan> {
  return apiRequest<UserScan>("/api/user/documents", {
    method: "POST",
    body: JSON.stringify(payload),
  });
}

export async function getUserDocument(scanId: number): Promise<UserScan> {
  return apiRequest<UserScan>(`/api/user/documents/${scanId}`);
}

export async function updateUserDocument(
  scanId: number,
  payload: Partial<{
    title: string;
    ocr_status: OcrStatus;
    tree_status: TreeStatus;
    family_tree_id: string;
    request_id: string;
    source_text: string;
  }>,
): Promise<UserScan> {
  return apiRequest<UserScan>(`/api/user/documents/${scanId}`, {
    method: "PATCH",
    body: JSON.stringify(payload),
  });
}

export async function listUserFamilyTrees(): Promise<FamilyTreeListResponse> {
  return apiRequest<FamilyTreeListResponse>("/api/user/family-trees");
}

export async function createUserFamilyTree(payload: {
  name: string;
  description?: string;
  nodes: BalkanNode[];
  source_scan_id?: number;
}): Promise<FamilyTreeDocument> {
  return apiRequest<FamilyTreeDocument>("/api/user/family-trees", {
    method: "POST",
    body: JSON.stringify(payload),
  });
}

export async function getUserFamilyTree(treeId: string): Promise<FamilyTreeDocument> {
  return apiRequest<FamilyTreeDocument>(`/api/user/family-trees/${treeId}`);
}

export async function updateProfile(payload: {
  full_name?: string;
  password?: string;
}): Promise<{ id: number; email: string; full_name: string; role: string; created_at: string }> {
  return apiRequest("/api/me", {
    method: "PATCH",
    body: JSON.stringify(payload),
  });
}

export async function getAdminStats(): Promise<AdminStats> {
  return apiRequest<AdminStats>("/api/admin/stats");
}

export async function listAdminHistory(limit = 50): Promise<AdminHistoryResponse> {
  return apiRequest<AdminHistoryResponse>(`/api/admin/history?limit=${limit}`);
}
