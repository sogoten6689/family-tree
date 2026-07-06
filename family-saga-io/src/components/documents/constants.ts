import type { DocumentType } from "@/types/document";

export const DOCUMENT_TYPE_OPTIONS = [
  { value: "han_nom", label: "Hán-Nôm" },
  { value: "van_ban", label: "Văn bản" },
  { value: "hinh_anh", label: "Hình ảnh" },
  { value: "ket_qua_van_ban", label: "Kết quả văn bản" },
  { value: "ket_qua_hinh_anh", label: "Kết quả hình ảnh" },
] as const;

export const OCR_ELIGIBLE_DOCUMENT_TYPES: DocumentType[] = ["han_nom", "hinh_anh", "van_ban"];

export function getDocumentTypeLabel(type: string): string {
  return DOCUMENT_TYPE_OPTIONS.find((item) => item.value === type)?.label ?? type;
}

export function formatFileSize(bytes: number): string {
  if (bytes < 1024) return `${bytes} B`;
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
  return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
}

export function sortDocumentFiles<T extends { position: number; id: number }>(files: T[]): T[] {
  return [...files].sort((a, b) => a.position - b.position || a.id - b.id);
}
