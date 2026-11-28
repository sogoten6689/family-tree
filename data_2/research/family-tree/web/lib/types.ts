export type Gender = "male" | "female" | null;
export type RelType = "spouse" | "father" | "mother" | "son" | "daughter";
export const REL_TYPES: RelType[] = ["spouse", "father", "mother", "son", "daughter"];

export interface Person {
  name: string;
  birth: number | null;
  death: number | null;
  generation: number | null;
  gender: Gender;
}

export interface Relation {
  from: string;
  to: string;
  type: RelType;
}

export interface Answer {
  persons: Person[];
  relations: Relation[];
}

export type ReviewStatus = "chua" | "da" | "xem_lai";

export interface Review {
  status: ReviewStatus;
  note?: string;
  answer?: Answer | null; // null/undefined = giữ nhãn gốc
  updated_at: string;
}

export interface Sample {
  idx: number; // số dòng (0-based)
  key: string; // sha1 của Input, ổn định khi file được sinh lại
  input: string;
  instruction: string;
  answer: Answer | null;
  parseError?: string;
  meta?: Record<string, unknown>;
}

export interface DatasetInfo {
  id: string;
  path: string;
  label: string;
  group: string;
  mtimeMs: number;
  size: number;
}
