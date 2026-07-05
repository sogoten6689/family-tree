import { apiRequest, ApiError, getBackendBaseUrl, getStoredAccessToken, parseApiError } from "@/lib/apiClient";
import type {
  DocumentCreatePayload,
  DocumentListResponse,
  DocumentUpdatePayload,
  FamilyTreeSourceDocument,
  ReorderFilesPayload,
  UploadFilesResponse,
} from "@/types/document";

async function apiFormRequest<T>(path: string, formData: FormData, method = "POST"): Promise<T> {
  const headers = new Headers();
  const token = getStoredAccessToken();
  if (token) {
    headers.set("Authorization", `Bearer ${token}`);
  }

  const response = await fetch(`${getBackendBaseUrl()}${path}`, {
    method,
    body: formData,
    headers,
  });

  if (!response.ok) {
    throw new ApiError(await parseApiError(response), response.status);
  }

  return (await response.json()) as T;
}

export async function listTreeDocuments(treeId: string): Promise<DocumentListResponse> {
  return apiRequest<DocumentListResponse>(`/api/family-trees/${treeId}/documents`);
}

export async function getDocument(documentId: number): Promise<FamilyTreeSourceDocument> {
  return apiRequest<FamilyTreeSourceDocument>(`/api/documents/${documentId}`);
}

export async function createTreeDocument(
  treeId: string,
  payload: DocumentCreatePayload,
): Promise<FamilyTreeSourceDocument> {
  return apiRequest<FamilyTreeSourceDocument>(`/api/family-trees/${treeId}/documents`, {
    method: "POST",
    body: JSON.stringify(payload),
  });
}

export async function updateDocument(
  documentId: number,
  payload: DocumentUpdatePayload,
): Promise<FamilyTreeSourceDocument> {
  return apiRequest<FamilyTreeSourceDocument>(`/api/documents/${documentId}`, {
    method: "PUT",
    body: JSON.stringify(payload),
  });
}

export async function uploadDocumentFiles(
  documentId: number,
  files: File[],
): Promise<UploadFilesResponse> {
  const formData = new FormData();
  files.forEach((file) => formData.append("files", file));
  return apiFormRequest<UploadFilesResponse>(`/api/documents/${documentId}/upload-files`, formData);
}

export async function reorderDocumentFiles(
  documentId: number,
  payload: ReorderFilesPayload,
): Promise<FamilyTreeSourceDocument> {
  return apiRequest<FamilyTreeSourceDocument>(`/api/documents/${documentId}/reorder-files`, {
    method: "PUT",
    body: JSON.stringify(payload),
  });
}

export async function deleteDocumentFile(
  documentId: number,
  fileId: number,
): Promise<FamilyTreeSourceDocument> {
  return apiRequest<FamilyTreeSourceDocument>(`/api/documents/${documentId}/files/${fileId}`, {
    method: "DELETE",
  });
}
