import { apiRequest } from "@/lib/apiClient";
import type { FamilyTreeDocument, FamilyTreeListResponse } from "@/lib/familyTreeApi";
import type { DocumentListResponse } from "@/types/document";

export async function listPublicFamilyTrees(): Promise<FamilyTreeListResponse> {
  return apiRequest<FamilyTreeListResponse>("/api/public/family-trees");
}

export async function getPublicFamilyTree(treeId: string): Promise<FamilyTreeDocument> {
  return apiRequest<FamilyTreeDocument>(`/api/public/family-trees/${treeId}`);
}

export async function listPublicFamilyTreeDocuments(treeId: string): Promise<DocumentListResponse> {
  return apiRequest<DocumentListResponse>(`/api/public/family-trees/${treeId}/documents`);
}
