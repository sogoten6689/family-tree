/** Meta vote theo từng chữ (schema_version 2) + tiện ích dùng chung — tách khỏi
 * VoteCharView.tsx để file component chỉ export component (react-refresh). */
export type VoteSlotStatus = "kept" | "kept_weak" | "auto_fixed" | "suggested" | "tie" | "unaligned";

export type VoteSlot = {
  kind: "char" | "insert";
  index: number;
  line: number;
  backbone: string;
  final: string;
  proposal: string | null;
  status: VoteSlotStatus;
  votes: Record<string, string[]>;
};

export type VoteEngineV2 = {
  text: string;
  han_chars: number;
  voted: boolean;
  excluded: string | null;
};

export type VoteMetaV2 = {
  schema_version: 2;
  vote_method: string;
  backbone: string;
  page_status: "ok" | "partial" | "unaligned";
  thresholds: { auto_min: number; suggest_min: number };
  stats: { chars: number } & Partial<Record<VoteSlotStatus | "unanimous", number>>;
  review_rate: number;
  uncertain_rate: number;
  engines: Record<string, VoteEngineV2>;
  lines: string[];
  slots: VoteSlot[];
  /** Chữ Hán đổi sau khi vote lại → phiên âm/dịch nghĩa có thể chưa khớp. */
  downstream_stale?: boolean;
};

export function isVoteMetaV2(meta: unknown): meta is VoteMetaV2 {
  return !!meta && typeof meta === "object" && (meta as { schema_version?: unknown }).schema_version === 2;
}

const ENGINE_LABELS: Record<string, string> = {
  kim_hannom_lab: "Kim Hán Nôm",
  kimhannom: "Kim Hán Nôm",
  paddle_v6: "Paddle",
  deepseek: "DeepSeek",
  google_vision: "Google Vision",
  gemini: "Gemini",
  gemini_vision: "Gemini",
  gpt_vision: "GPT",
};

export const engineLabel = (name: string) => ENGINE_LABELS[name] ?? name;
