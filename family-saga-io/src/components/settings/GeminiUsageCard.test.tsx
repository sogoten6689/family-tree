import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";

import { thinkingShare, type GeminiUsageSummary } from "@/lib/settingsApi";

if (typeof globalThis.ResizeObserver === "undefined") {
  globalThis.ResizeObserver = class {
    observe() {}
    unobserve() {}
    disconnect() {}
  } as unknown as typeof ResizeObserver;
}

const api = vi.hoisted(() => ({ getGeminiUsage: vi.fn() }));
vi.mock("@/lib/settingsApi", async (importOriginal) => ({
  ...(await importOriginal<typeof import("@/lib/settingsApi")>()),
  getGeminiUsage: api.getGeminiUsage,
}));

const { GeminiUsageCard } = await import("./GeminiUsageCard");

const summary: GeminiUsageSummary = {
  days: 30,
  total_tokens: 1000,
  total_calls: 3,
  tasks: [
    {
      task: "translate",
      calls: 2,
      errors: 1,
      prompt_tokens: 300,
      output_tokens: 100,
      thinking_tokens: 400,
      total_tokens: 800,
      avg_tokens_per_call: 400,
      avg_duration_ms: 2500,
    },
    {
      task: "ma_dinh_danh",
      calls: 1,
      errors: 0,
      prompt_tokens: 150,
      output_tokens: 50,
      thinking_tokens: 0,
      total_tokens: 200,
      avg_tokens_per_call: 200,
      avg_duration_ms: 900,
    },
  ],
};

describe("thinkingShare", () => {
  it("is thinking tokens over total", () => {
    expect(thinkingShare(summary)).toBeCloseTo(0.4);
  });
  it("is null without tokens", () => {
    expect(thinkingShare({ days: 7, tasks: [], total_tokens: 0, total_calls: 0 })).toBeNull();
  });
});

describe("GeminiUsageCard", { timeout: 15000 }, () => {
  it("shows per-task rows, totals and thinking share", async () => {
    api.getGeminiUsage.mockResolvedValueOnce(summary);
    render(<GeminiUsageCard />);
    expect(await screen.findByText("Dịch nghĩa")).toBeInTheDocument();
    expect(screen.getByText("Trích mã định danh")).toBeInTheDocument();
    expect(screen.getByText(/thinking chiếm 40%/)).toBeInTheDocument();
    expect(screen.getByText("2.5 s")).toBeInTheDocument();
    expect(api.getGeminiUsage).toHaveBeenLastCalledWith(30);
  });

  it("reloads with the chosen range", async () => {
    api.getGeminiUsage.mockResolvedValue(summary);
    render(<GeminiUsageCard />);
    await screen.findByText("Dịch nghĩa");
    fireEvent.click(screen.getByText("7 ngày"));
    await waitFor(() => expect(api.getGeminiUsage).toHaveBeenLastCalledWith(7));
  });

  it("shows empty state when nothing recorded", async () => {
    api.getGeminiUsage.mockResolvedValueOnce({ days: 30, tasks: [], total_tokens: 0, total_calls: 0 });
    render(<GeminiUsageCard />);
    expect(await screen.findByText(/Chưa có lượt gọi Gemini nào trong 30 ngày/)).toBeInTheDocument();
  });

  it("shows the API error", async () => {
    api.getGeminiUsage.mockRejectedValueOnce(new Error("Không có quyền"));
    render(<GeminiUsageCard />);
    expect(await screen.findByText("Không có quyền")).toBeInTheDocument();
  });
});
