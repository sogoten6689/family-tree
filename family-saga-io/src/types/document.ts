export type DocumentType =
  | "han_nom"
  | "van_ban"
  | "hinh_anh"
  | "ket_qua_van_ban"
  | "ket_qua_hinh_anh";

export interface DocumentFile {
  id: number;
  file_name: string;
  file_key: string;
  file_type: string;
  size: number;
  position: number;
  created_at: string;
  download_url?: string | null;
}

export interface FamilyTreeSourceDocument {
  id: number;
  family_tree_id: string;
  title: string;
  description?: string | null;
  type: DocumentType;
  created_at: string;
  files: DocumentFile[];
}

export interface DocumentListResponse {
  total: number;
  items: FamilyTreeSourceDocument[];
}

export interface DocumentCreatePayload {
  title: string;
  description?: string;
  type: DocumentType;
}

export interface DocumentUpdatePayload {
  title?: string;
  description?: string | null;
  type?: DocumentType;
}

export interface ReorderFilesPayload {
  files: Array<{ id: number; position: number }>;
}

export interface UploadFilesResponse {
  document_id: number;
  uploaded: DocumentFile[];
}

export interface OcrTransliterateResponse {
  source_document_id: number;
  result_document_id: number;
  ocr_text: string;
  ocr_lines: string[];
  transcription_lines: string[];
  transcription_text: string;
  saved_file: DocumentFile;
  result_document: FamilyTreeSourceDocument;
}
