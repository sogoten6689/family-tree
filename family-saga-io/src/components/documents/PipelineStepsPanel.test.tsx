import { fireEvent, render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";

import "@/i18n";
import { PipelineStepsPanel, type VoteMeta } from "./PipelineStepsPanel";

// jsdom không có ResizeObserver (antd Select cần) — stub chỉ trong test này.
if (typeof globalThis.ResizeObserver === "undefined") {
  globalThis.ResizeObserver = class {
    observe() {}
    unobserve() {}
    disconnect() {}
  } as unknown as typeof ResizeObserver;
}

const meta = (method: string): VoteMeta => ({
  vote_method: method,
  engines: { kimhannom: { text: `text-${method}`, score: null, similarity_to_others: 1 } },
  uncertain_spans: [],
  uncertain_rate: 0,
  structural_diffs: [],
});

describe("PipelineStepsPanel", { timeout: 15000 }, () => {
  it("renders nothing when there is no data at all", () => {
    const { container } = render(<PipelineStepsPanel pipelineVersion="v1" />);
    expect(container).toBeEmptyDOMElement();
  });

  it("shows for a v1 / reopened scan with only transliteration, marking OCR as unavailable", () => {
    render(<PipelineStepsPanel transliterationText="Càn khôn" />);
    expect(screen.getByText(/pipeline v1/)).toBeInTheDocument();
  });

  it("jumps directly to any step when its title is clicked", () => {
    render(<PipelineStepsPanel transliterationText="Càn khôn" translationText="Trời đất" />);
    fireEvent.click(screen.getByText("4. Dịch nghĩa"));
    expect(screen.getByText("Trời đất")).toBeInTheDocument();
    fireEvent.click(screen.getByText("3. Dịch âm (phiên âm)"));
    expect(screen.getByText("Càn khôn")).toBeInTheDocument();
  });

  it("shows a page selector for multi-page vote data and switches the page shown", () => {
    render(<PipelineStepsPanel voteMeta={[meta("p1"), meta("p2")]} />);
    expect(screen.getByText("text-p1")).toBeInTheDocument();
    fireEvent.mouseDown(screen.getByRole("combobox", { name: "Trang" }));
    fireEvent.click(screen.getByTitle("2/2"));
    expect(screen.getByText("text-p2")).toBeInTheDocument();
  });

  it("has no page selector for single-page data", () => {
    render(<PipelineStepsPanel voteMeta={[meta("only")]} />);
    expect(screen.queryByRole("combobox", { name: "Trang" })).toBeNull();
  });
});
