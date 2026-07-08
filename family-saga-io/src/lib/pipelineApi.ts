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

export interface PipelineStep {
  step_id: PipelineStepId;
  status: PipelineStepStatus;
  skipped_reason?: string | null;
  input_ref?: string | null;
  output_ref?: string | null;
  content_hash?: string | null;
  error_message?: string | null;
  started_at?: string | null;
  finished_at?: string | null;
  updated_at?: string | null;
  document_id: number;
}

export interface PipelineResponse {
  family_tree_id: string;
  steps: PipelineStep[];
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

export async function getFamilyTreePipeline(treeId: string): Promise<PipelineResponse> {
  return apiRequest<PipelineResponse>(`/api/family-trees/${encodeURIComponent(treeId)}/pipeline`);
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
