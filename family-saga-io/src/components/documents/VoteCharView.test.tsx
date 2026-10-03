import { fireEvent, render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";

import "@/i18n";
import { PipelineStepsPanel } from "./PipelineStepsPanel";
import { VoteCharView } from "./VoteCharView";
import { isVoteMetaV2, type VoteMetaV2 } from "./voteMetaV2";

if (typeof globalThis.ResizeObserver === "undefined") {
  globalThis.ResizeObserver = class {
    observe() {}
    unobserve() {}
    disconnect() {}
  } as unknown as typeof ResizeObserver;
}

// Giống đầu ra build_vote_meta (backend) cho nom-147 tr.4: nền Paddle 王, 3 engine kia 三.
const meta: VoteMetaV2 = {
  schema_version: 2,
  vote_method: "char_majority",
  backbone: "paddle_v6",
  page_status: "partial",
  thresholds: { auto_min: 3, suggest_min: 2 },
  stats: { chars: 9, unanimous: 6, auto_fixed: 1, suggested: 1, tie: 1 },
  review_rate: 0.2222,
  uncertain_rate: 0.2222,
  engines: {
    paddle_v6: { text: "先祖考\n朱公字王品", han_chars: 8, voted: true, excluded: null },
    kim_hannom_lab: { text: "先祖妣朱公字三品", han_chars: 8, voted: true, excluded: null },
    deepseek: { text: "先祖妣朱公字三品", han_chars: 8, voted: true, excluded: null },
    google_vision: { text: "先柱考来公字三品", han_chars: 8, voted: true, excluded: null },
    gemini: { text: "日月盈昃".repeat(30), han_chars: 120, voted: false, excluded: "lạc đề: 0% chữ có ở engine khác" },
  },
  lines: ["先祖考", "朱公字三品"],
  slots: [
    { kind: "char", index: 2, line: 0, backbone: "考", final: "考", proposal: "妣", status: "suggested",
      votes: { 考: ["paddle_v6", "google_vision"], 妣: ["kim_hannom_lab", "deepseek"] } },
    { kind: "char", index: 3, line: 1, backbone: "朱", final: "朱", proposal: null, status: "tie",
      votes: { 朱: ["paddle_v6", "kim_hannom_lab"], 来: ["google_vision"], 未: ["deepseek"] } },
    { kind: "char", index: 6, line: 1, backbone: "王", final: "三", proposal: null, status: "auto_fixed",
      votes: { 王: ["paddle_v6"], 三: ["kim_hannom_lab", "deepseek", "google_vision"] } },
  ],
};

describe("VoteCharView", { timeout: 15000 }, () => {
  it("recognises schema 2 only", () => {
    expect(isVoteMetaV2(meta)).toBe(true);
    expect(isVoteMetaV2({ vote_method: "x", uncertain_spans: [] })).toBe(false);
    expect(isVoteMetaV2(null)).toBe(false);
  });

  it("shows a plain-language summary and engines incl. the excluded one", () => {
    render(<VoteCharView meta={meta} />);
    expect(screen.getByText("22%")).toBeInTheDocument();
    expect(screen.getByText("Tự sửa (≥3 phiếu)").nextSibling).toHaveTextContent("1");
    expect(screen.getByText(/Gemini · không bỏ phiếu/)).toBeInTheDocument();
    expect(screen.getByText(/Paddle · nền/)).toBeInTheDocument();
  });

  it("colours characters by status in the page text", () => {
    const { container } = render(<VoteCharView meta={meta} />);
    expect(container.querySelector(".vote-v2-text .vote-c-fixed")?.textContent).toBe("三");
    expect(container.querySelector(".vote-v2-text .vote-c-review")?.textContent).toBe("考");
    expect(container.querySelector(".vote-v2-text .vote-c-tie")?.textContent).toBe("朱");
  });

  it("opens the per-character comparison table for a clicked line", () => {
    const { container } = render(<VoteCharView meta={meta} />);
    fireEvent.click(screen.getByRole("button", { name: "Dòng 2" }));
    const rows = Array.from(container.querySelectorAll(".vote-v2-grid tr")).map((r) => r.textContent);
    expect(rows).toContain("Paddle (nền)朱公字王品");
    expect(rows).toContain("Google Vision来公字三品");
    expect(rows.at(-1)).toBe("Kết quả朱公字三品");
    expect(screen.getByText("Chữ 4: đã sửa “王” → “三”")).toBeInTheDocument();
    fireEvent.click(screen.getByRole("button", { name: "Dòng 1" }));
    expect(screen.getByText("Chữ 3: đề xuất “妣” thay cho “考”")).toBeInTheDocument();
  });

  it("warns when only one engine could read the page", () => {
    render(<VoteCharView meta={{ ...meta, page_status: "unaligned" }} />);
    expect(screen.getByText(/Chỉ 1 engine đọc được trang này/)).toBeInTheDocument();
  });
});

describe("PipelineStepsPanel with schema 2", { timeout: 15000 }, () => {
  it("renders the per-character vote view and engine screening reasons", () => {
    render(<PipelineStepsPanel voteMeta={[meta]} />);
    expect(screen.getByText("lạc đề: 0% chữ có ở engine khác")).toBeInTheDocument();
    fireEvent.click(screen.getByText("2. Vote (hợp nhất)"));
    expect(screen.getByText("Chữ cần soát")).toBeInTheDocument();
    expect(screen.queryByText(/Phương pháp/)).not.toBeInTheDocument();
  });
});
