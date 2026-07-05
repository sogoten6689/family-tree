import { apiRequest } from "@/lib/apiClient";

export type Gender = "male" | "female";
export type BalkanNode = Record<string, unknown>;

export interface FamilyTreeSummary {
  id: string;
  name: string;
  description?: string | null;
  created_at: string;
  updated_at: string;
  node_count: number;
}

export interface FamilyTreeDocument {
  id: string;
  name: string;
  description?: string | null;
  created_at: string;
  updated_at: string;
  nodes: BalkanNode[];
}

export interface FamilyTreeListResponse {
  total: number;
  items: FamilyTreeSummary[];
}

export async function listFamilyTrees(): Promise<FamilyTreeListResponse> {
  return apiRequest<FamilyTreeListResponse>("/api/family-trees");
}

export async function getFamilyTree(treeId: string): Promise<FamilyTreeDocument> {
  return apiRequest<FamilyTreeDocument>(`/api/family-trees/${treeId}`);
}

export async function createFamilyTree(payload: {
  name: string;
  description?: string;
  nodes?: BalkanNode[];
}): Promise<FamilyTreeDocument> {
  return apiRequest<FamilyTreeDocument>("/api/family-trees", {
    method: "POST",
    body: JSON.stringify(payload),
  });
}

export async function updateFamilyTree(
  treeId: string,
  payload: { name?: string; description?: string },
): Promise<FamilyTreeDocument> {
  return apiRequest<FamilyTreeDocument>(`/api/family-trees/${treeId}`, {
    method: "PUT",
    body: JSON.stringify(payload),
  });
}

export async function replaceFamilyTreeDocument(
  treeId: string,
  payload: { name: string; description?: string; nodes: BalkanNode[] },
): Promise<FamilyTreeDocument> {
  return apiRequest<FamilyTreeDocument>(`/api/family-trees/${treeId}/document`, {
    method: "PUT",
    body: JSON.stringify(payload),
  });
}

export async function deleteFamilyTree(treeId: string): Promise<void> {
  await apiRequest(`/api/family-trees/${treeId}`, { method: "DELETE" });
}

export async function createNode(
  treeId: string,
  payload: Record<string, unknown>,
): Promise<FamilyTreeDocument> {
  return apiRequest<FamilyTreeDocument>(`/api/family-trees/${treeId}/nodes`, {
    method: "POST",
    body: JSON.stringify(payload),
  });
}

export async function updateNode(
  treeId: string,
  nodeId: number,
  payload: Record<string, unknown>,
): Promise<FamilyTreeDocument> {
  return apiRequest<FamilyTreeDocument>(`/api/family-trees/${treeId}/nodes/${nodeId}`, {
    method: "PUT",
    body: JSON.stringify(payload),
  });
}

export async function removeNode(treeId: string, nodeId: number): Promise<FamilyTreeDocument> {
  return apiRequest<FamilyTreeDocument>(`/api/family-trees/${treeId}/nodes/${nodeId}`, {
    method: "DELETE",
  });
}

export async function createLink(
  treeId: string,
  payload: {
    type: "spouse_of" | "parent_of";
    from_id: number;
    to_id: number;
    side?: "fid" | "mid";
  },
): Promise<FamilyTreeDocument> {
  return apiRequest<FamilyTreeDocument>(`/api/family-trees/${treeId}/links`, {
    method: "POST",
    body: JSON.stringify(payload),
  });
}

export async function deleteLink(
  treeId: string,
  payload: {
    type: "spouse_of" | "parent_of";
    from_id: number;
    to_id: number;
    side?: "fid" | "mid";
  },
): Promise<FamilyTreeDocument> {
  return apiRequest<FamilyTreeDocument>(`/api/family-trees/${treeId}/links`, {
    method: "DELETE",
    body: JSON.stringify(payload),
  });
}

export async function crawlAndSyncVietnamGiaPha(payload: {
  start_id: number;
  end_id: number;
  delay_seconds?: number;
  sync_db: boolean;
}): Promise<Record<string, unknown>> {
  return apiRequest<Record<string, unknown>>("/api/vietnamgiapha/crawl-sync", {
    method: "POST",
    body: JSON.stringify(payload),
  });
}
