import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";

import "@/i18n";
import { VoteDiffLine, type UncertainSpan } from "./VoteDiffLine";

// Dữ liệu lấy nguyên từ output thật của vote_from_results + annotate_vote_diffs
// (app/hannom/vote_diff.py), gồm chữ ngoài BMP 𠀀 (U+20000) = 2 đơn vị UTF-16.
const span: UncertainSpan = {
  line: 0,
  voted_line: "阮族家譜𠀀記",
  method: "line_confirmed_majority",
  n_agree: 2,
  n_total: 3,
  disagreeing: [
    {
      engine: "d",
      text: "阮族家譜𠀁記",
      similarity: 0.8333,
      diff: [
        { op: "equal", text: "阮族家譜" },
        { op: "replace", text: "𠀁" },
        { op: "equal", text: "記" },
      ],
    },
  ],
  positional: {
    uncertain_positions: [
      {
        backbone_pos: 4,
        backbone_char: "𠀀",
        resolved: null,
        method: "position_no_majority",
        votes: { __keep__: ["a", "b"], "𠀁": ["d"] },
      },
    ],
  },
  voted_segments: [
    { text: "阮族家譜", contested: false },
    { text: "𠀀", contested: true },
    { text: "記", contested: false },
  ],
};

describe("VoteDiffLine", () => {
  it("underlines exactly the contested non-BMP char on the winning line", () => {
    const { container } = render(<VoteDiffLine span={span} />);
    const contested = container.querySelectorAll(".vote-ch-contested");
    expect(contested).toHaveLength(1);
    expect(contested[0].textContent).toBe("𠀀");
  });

  it("colours the replaced char of the disagreeing engine and keeps its full text", () => {
    const { container } = render(<VoteDiffLine span={span} />);
    const replaced = container.querySelectorAll(".vote-dis .vote-ch-rep");
    expect(replaced).toHaveLength(1);
    expect(replaced[0].textContent).toBe("𠀁");
    expect(container.querySelector(".vote-dis .vote-han")?.textContent).toBe("阮族家譜𠀁記");
  });

  it("shows winner count, method label and per-position votes", () => {
    render(<VoteDiffLine span={span} />);
    expect(screen.getByText("Thắng 2/3")).toBeInTheDocument();
    expect(screen.getByText("Giữ backbone (đa số)")).toBeInTheDocument();
    expect(screen.getByText(/giữ nguyên backbone: a, b · "𠀁": d/)).toBeInTheDocument();
  });

  it("renders a delete segment as faded dots", () => {
    const { container } = render(
      <VoteDiffLine
        span={{
          ...span,
          positional: undefined,
          disagreeing: [{ engine: "e", text: "族家", similarity: 0.5, diff: [{ op: "delete", missing: 2 }, { op: "equal", text: "族家" }] }],
        }}
      />,
    );
    expect(container.querySelector(".vote-ch-gap")?.textContent).toBe("··");
  });

  it("falls back to plain text when backend sent no diff (older stored vote_meta)", () => {
    const { container } = render(
      <VoteDiffLine
        span={{ ...span, voted_segments: undefined, disagreeing: [{ engine: "d", text: "阮族", similarity: 0.3 }] }}
      />,
    );
    expect(container.querySelectorAll(".vote-ch-contested")).toHaveLength(0);
    expect(container.querySelector(".vote-dis .vote-han")?.textContent).toBe("阮族");
  });
});
