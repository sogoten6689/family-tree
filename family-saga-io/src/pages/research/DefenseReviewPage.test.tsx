import { fireEvent, render, screen } from "@testing-library/react";
import { beforeEach, describe, expect, it } from "vitest";

import { AXES, ERROR_STATEMENTS, FLASHCARDS, GLOSSARY, GLOSSARY_GROUPS, MOCK_QUESTIONS, QUIZ } from "./defenseReviewData";

if (typeof globalThis.ResizeObserver === "undefined") {
  globalThis.ResizeObserver = class {
    observe() {}
    unobserve() {}
    disconnect() {}
  } as unknown as typeof ResizeObserver;
}

const { default: DefenseReviewPage, STORAGE_KEY } = await import("./DefenseReviewPage");

describe("ngân hàng câu hỏi ôn tập", () => {
  it("mỗi trục có ít nhất 3 thẻ hỏi–đáp", () => {
    for (const axis of AXES) {
      expect(FLASHCARDS.filter((c) => c.axis === axis.id).length).toBeGreaterThanOrEqual(3);
    }
  });

  it("id không trùng và đáp án trắc nghiệm nằm trong danh sách lựa chọn", () => {
    const ids = [...FLASHCARDS, ...MOCK_QUESTIONS, ...QUIZ, ...ERROR_STATEMENTS, ...GLOSSARY].map((x) => x.id);
    expect(new Set(ids).size).toBe(ids.length);
    for (const q of QUIZ) {
      expect(q.answer).toBeGreaterThanOrEqual(0);
      expect(q.answer).toBeLessThan(q.options.length);
      expect(new Set(q.options).size).toBe(q.options.length);
    }
  });

  it("mỗi khái niệm thuộc một nhóm đã khai báo, nhóm nào cũng có khái niệm", () => {
    for (const g of GLOSSARY) expect(GLOSSARY_GROUPS).toContain(g.group);
    for (const group of GLOSSARY_GROUPS) expect(GLOSSARY.some((g) => g.group === group)).toBe(true);
  });
});

describe("DefenseReviewPage", () => {
  beforeEach(() => window.localStorage.clear());

  it("tìm khái niệm không dấu", () => {
    render(<DefenseReviewPage />);
    fireEvent.change(screen.getByPlaceholderText(/Tìm khái niệm/), { target: { value: "xlm-r" } });
    expect(screen.getByText("XLM-R (XLM-RoBERTa)")).toBeInTheDocument();
    expect(screen.queryByText("Cohen's kappa, Fleiss' kappa")).not.toBeInTheDocument();
  }, 30000);

  it("lật thẻ hiện đáp án và lưu trạng thái đã thuộc", () => {
    render(<DefenseReviewPage />);
    fireEvent.click(screen.getByText("Thẻ hỏi–đáp"));
    // getByRole trên cây 24 thẻ antd rất chậm trong jsdom, nên tìm theo chữ.
    fireEvent.click(screen.getAllByText("Lật thẻ")[0]);
    expect(screen.getByText(FLASHCARDS[0].answer[0])).toBeInTheDocument();
    fireEvent.click(screen.getByText("Đã thuộc"));
    expect(JSON.parse(window.localStorage.getItem(STORAGE_KEY) ?? "{}").cards[FLASHCARDS[0].id]).toBe("known");
  }, 30000);

  it("trắc nghiệm chấm đúng và nhớ câu trả lời sau khi tải lại", () => {
    const q = QUIZ[0];
    const { unmount } = render(<DefenseReviewPage />);
    fireEvent.click(screen.getByRole("tab", { name: "Trắc nghiệm số liệu" }));
    fireEvent.click(screen.getAllByText(q.options[q.answer])[0]);
    expect(screen.getByText("Đúng")).toBeInTheDocument();
    unmount();

    render(<DefenseReviewPage />);
    fireEvent.click(screen.getByRole("tab", { name: "Trắc nghiệm số liệu" }));
    expect(screen.getByText(`Điểm: 1/${QUIZ.length}`)).toBeInTheDocument();
  }, 30000);

  it("vẫn chạy khi localStorage hỏng", () => {
    window.localStorage.setItem(STORAGE_KEY, "{không phải json");
    render(<DefenseReviewPage />);
    expect(screen.getByText("Ôn tập bảo vệ luận văn")).toBeInTheDocument();
  });
});
