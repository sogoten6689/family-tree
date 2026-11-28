import type { ReviewStatus } from "@/lib/llmSoatApi";

export const PALETTE = ["#f6d58e", "#a7d8f0", "#f5b3c8", "#b8e0b0", "#d7c2f0", "#f7c59f", "#a8e6e0", "#e8d3a9", "#c9d6a3", "#f0b6a8"];
export const colorOf = (i: number) => PALETTE[i % PALETTE.length];

export const STATUS_LABEL: Record<ReviewStatus, string> = { chua: "chưa soát", da: "đã soát", xem_lai: "cần xem lại" };
export const STATUS_COLOR: Record<ReviewStatus, string | undefined> = { chua: undefined, da: "green", xem_lai: "orange" };
