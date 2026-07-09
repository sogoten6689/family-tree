import { apiRequest } from "@/lib/apiClient";

export type PipelineStepId =
  | "name"
  | "hannom_image"
  | "ocr"
  | "han_chars"
  | "quoc_ngu"
  | "distilled"
  | "output";

export type PipelineStepStatus = "pending" | "running" | "done" | "skipped" | "error";

export type PipelineSkippedReason =
  | "already_exists"
  | "not_applicable"
  | "user_skip"
  | "source_has_later_step"
  | "vgp_entry";

export interface PipelineStep {
  step_id: PipelineStepId;
  status: PipelineStepStatus;
  skipped_reason?: string | null;
  input_ref?: string | null;
  output_ref?: string | null;
  content_hash?: string | null;
  error_message?: string | null;
  manual_override?: boolean;
  admin_note?: string | null;
  started_at?: string | null;
  finished_at?: string | null;
  updated_at?: string | null;
  document_id: number;
}

export interface PipelineContext {
  family_tree_id: string;
  tree_name?: string | null;
  external_url?: string | null;
  source_type?: string | null;
  node_count: number;
}

export interface PipelineResponse {
  family_tree_id: string;
  context: PipelineContext;
  steps: PipelineStep[];
}

export interface PipelineArtifactFile {
  id: number;
  filename: string;
  mime_type: string;
  url?: string | null;
  size: number;
}

export interface PipelineArtifact {
  kind: "none" | "text" | "document" | "family_tree";
  message?: string | null;
  document_id?: number | null;
  title?: string | null;
  type?: string | null;
  preview_text?: string | null;
  node_count?: number | null;
  files: PipelineArtifactFile[];
}

export interface PipelineStepDetail extends PipelineStep {
  artifact: PipelineArtifact;
  context: PipelineContext;
}

export interface PipelineStepUpdatePayload {
  status?: PipelineStepStatus;
  skipped_reason?: string | null;
  input_ref?: string | null;
  output_ref?: string | null;
  error_message?: string | null;
  document_id?: number;
  admin_note?: string | null;
}

export const PIPELINE_STEP_LABELS: Record<PipelineStepId, { vi: string; en: string }> = {
  name: { vi: "Tên dòng họ", en: "Lineage name" },
  hannom_image: { vi: "Ảnh Hán-Nôm", en: "Hán-Nôm images" },
  ocr: { vi: "OCR", en: "OCR" },
  han_chars: { vi: "Ký tự Hán", en: "Han characters" },
  quoc_ngu: { vi: "Quốc ngữ", en: "Vietnamese text" },
  distilled: { vi: "Cô đọng gia phả", en: "Distilled genealogy" },
  output: { vi: "Cây / VB gia phả", en: "Tree / structured output" },
};

export const PIPELINE_SKIPPED_REASONS: Array<{ value: PipelineSkippedReason; vi: string; en: string }> = [
  { value: "already_exists", vi: "Đã có sẵn", en: "Already exists" },
  { value: "not_applicable", vi: "Không áp dụng", en: "Not applicable" },
  { value: "user_skip", vi: "Admin bỏ qua", en: "Skipped by admin" },
  { value: "source_has_later_step", vi: "Nguồn đã có bước sau", en: "Source has later step" },
  { value: "vgp_entry", vi: "Nguồn VGP", en: "VGP source" },
];

export async function getFamilyTreePipeline(treeId: string): Promise<PipelineResponse> {
  return apiRequest<PipelineResponse>(`/api/family-trees/${encodeURIComponent(treeId)}/pipeline`);
}

export async function getPipelineStepDetail(
  treeId: string,
  stepId: PipelineStepId,
): Promise<PipelineStepDetail> {
  return apiRequest<PipelineStepDetail>(
    `/api/family-trees/${encodeURIComponent(treeId)}/pipeline/${stepId}`,
  );
}

export async function updatePipelineStep(
  treeId: string,
  stepId: PipelineStepId,
  payload: PipelineStepUpdatePayload,
): Promise<PipelineStep> {
  return apiRequest<PipelineStep>(
    `/api/family-trees/${encodeURIComponent(treeId)}/pipeline/${stepId}`,
    {
      method: "PATCH",
      body: JSON.stringify(payload),
    },
  );
}

export async function resyncPipeline(
  treeId: string,
  stepId?: PipelineStepId,
): Promise<PipelineResponse> {
  return apiRequest<PipelineResponse>(
    `/api/family-trees/${encodeURIComponent(treeId)}/pipeline/resync`,
    {
      method: "POST",
      body: JSON.stringify(stepId ? { step_id: stepId } : {}),
    },
  );
}

export async function runPipelineStep(treeId: string, stepId: PipelineStepId): Promise<PipelineStep> {
  return apiRequest<PipelineStep>(
    `/api/family-trees/${encodeURIComponent(treeId)}/pipeline/${stepId}/run`,
    { method: "POST" },
  );
}

export async function skipPipelineStep(
  treeId: string,
  stepId: PipelineStepId,
  reason = "user_skip",
): Promise<PipelineStep> {
  return apiRequest<PipelineStep>(
    `/api/family-trees/${encodeURIComponent(treeId)}/pipeline/${stepId}/skip`,
    {
      method: "POST",
      body: JSON.stringify({ reason }),
    },
  );
}

export async function runAllPipelineSteps(treeId: string): Promise<{
  family_tree_id: string;
  ran: string[];
  skipped: string[];
  errors: string[];
}> {
  return apiRequest(`/api/family-trees/${encodeURIComponent(treeId)}/pipeline/run-all`, {
    method: "POST",
  });
}

export function pipelineStepStatusColor(status: PipelineStepStatus): string {
  switch (status) {
    case "done":
      return "success";
    case "running":
      return "processing";
    case "skipped":
      return "default";
    case "error":
      return "error";
    default:
      return "warning";
  }
}

export function formatPipelineTimestamp(value?: string | null): string {
  if (!value) return "—";
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return value;
  return date.toLocaleString();
}

export function skippedReasonLabel(reason: string | null | undefined, lang: "vi" | "en"): string {
  if (!reason) return "—";
  const match = PIPELINE_SKIPPED_REASONS.find((item) => item.value === reason);
  if (!match) return reason;
  return lang === "en" ? match.en : match.vi;
}

export function sourceTypeLabel(sourceType: string | null | undefined, lang: "vi" | "en"): string {
  switch (sourceType) {
    case "vgp":
      return lang === "en" ? "VietnamGiaPha" : "VietnamGiaPha";
    case "nom":
      return lang === "en" ? "Nom Foundation" : "Nom Foundation";
    case "upload":
      return lang === "en" ? "Upload / manual" : "Upload / thủ công";
    default:
      return sourceType ?? "—";
  }
}
