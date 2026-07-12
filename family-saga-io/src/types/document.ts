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
  subtype?: string | null;
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
  subtype?: string;
}

export interface DocumentUpdatePayload {
  title?: string;
  description?: string | null;
  type?: DocumentType;
  subtype?: string | null;
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
  merged_page_count?: number;
  pipeline_synced?: boolean;
}

export interface OcrBatchItemResult {
  file_id: number;
  file_name: string;
  result_document_id: number;
  transcription_text: string;
}

export interface OcrBatchError {
  file_id: number;
  file_name: string;
  error: string;
}

export interface OcrBatchResponse {
  source_document_id: number;
  processed: number;
  skipped: number;
  results: OcrBatchItemResult[];
  errors: OcrBatchError[];
  combined_transcription_text: string;
  merged_page_count: number;
  pipeline_synced: boolean;
}

export interface OcrPageStatusItem {
  file_id: number;
  file_name: string;
  position: number;
  ocr_done: boolean;
}

export interface OcrPageStatusResponse {
  source_document_id: number;
  result_document_id?: number | null;
  total_pages: number;
  ocr_done_count: number;
  pages: OcrPageStatusItem[];
  merged_page_count: number;
}

export interface OcrMergeResponse {
  source_document_id: number;
  result_document_id?: number | null;
  merged_page_count: number;
  combined_transcription_text: string;
  pipeline_synced: boolean;
}
