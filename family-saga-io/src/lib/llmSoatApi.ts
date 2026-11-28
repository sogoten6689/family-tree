import { apiRequest } from "@/lib/apiClient";

/** Soát nhãn LLM (schema persons/relations) — nlp_family_extractor/app/doi_chieu/llm_soat.py, đòi admin. */

export type Gender = "male" | "female" | null;
export type RelType = "spouse" | "father" | "mother" | "son" | "daughter";
export const REL_TYPES: RelType[] = ["spouse", "father", "mother", "son", "daughter"];

export interface LlmPerson {
  name: string;
  birth: number | null;
  death: number | null;
  generation: number | null;
  gender: Gender;
}

export interface LlmRelation {
  from: string;
  to: string;
  type: RelType;
}

export interface LlmAnswer {
  persons: LlmPerson[];
  relations: LlmRelation[];
}

export type ReviewStatus = "chua" | "da" | "xem_lai";

export interface LlmReview {
  status: ReviewStatus;
  note: string | null;
  answer: LlmAnswer | null;
  updated_at: string;
  by?: string | null;
}

export interface LlmSample {
  idx: number;
  key: string;
  input: string;
  answer: LlmAnswer | null;
  meta: {
    tree_id?: number;
    person_src?: Record<string, string>;
    relation_src?: Record<string, string>;
    [k: string]: unknown;
  } | null;
  error: string | null;
  review: LlmReview | null;
}

export interface LlmDatasetSummary {
  id: string;
  label: string;
  group: string;
  path: string;
  mtime: number;
  mau: number;
  co_quan_he: number;
  nguoi_tb: number;
  da_soat: number;
  xem_lai: number;
  da_sua: number;
}

export interface LlmDatasetList {
  version: string;
  co_du_lieu: boolean;
  datasets: LlmDatasetSummary[];
}

export interface LlmDataset {
  id: string;
  label: string;
  group: string;
  path: string;
  samples: LlmSample[];
}

const BASE = "/api/doi-chieu/llm";

export const getLlmDatasets = () => apiRequest<LlmDatasetList>(BASE);
export const getLlmDataset = (id: string) => apiRequest<LlmDataset>(`${BASE}/${id}`);

export const getLlmPhaHe = (id: string, treeId: number, names: string[]) => {
  const q = new URLSearchParams();
  names.forEach((n) => q.append("ten", n));
  return apiRequest<{ lines: string[]; total: number }>(`${BASE}/${id}/pha-he/${treeId}?${q}`);
};

export const putLlmReview = (id: string, key: string, body: { status: ReviewStatus; note: string | null; answer: LlmAnswer | null }) =>
  apiRequest<{ review: LlmReview }>(`${BASE}/${id}/soat/${key}`, { method: "PUT", body: JSON.stringify(body) });

export const deleteLlmReview = (id: string, key: string) =>
  apiRequest<{ ok: boolean }>(`${BASE}/${id}/soat/${key}`, { method: "DELETE" });

export const exportLlmReviewed = (id: string) =>
  apiRequest<{ path: string; count: number; edited: number }>(`${BASE}/${id}/xuat`, { method: "POST" });
