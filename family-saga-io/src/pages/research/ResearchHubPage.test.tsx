import { fireEvent, render, screen } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import { describe, expect, it } from "vitest";

import { HYPOTHESES, METHODS, RESEARCH_QUESTIONS, RESULTS, STAGES, matches } from "./researchHubData";

if (typeof globalThis.ResizeObserver === "undefined") {
  globalThis.ResizeObserver = class {
    observe() {}
    unobserve() {}
    disconnect() {}
  } as unknown as typeof ResizeObserver;
}

const { default: ResearchHubPage, filterResults } = await import("./ResearchHubPage");

const renderPage = () =>
  render(
    <MemoryRouter>
      <ResearchHubPage />
    </MemoryRouter>,
  );

describe("dữ liệu thông tin nghiên cứu", () => {
  const rqIds = RESEARCH_QUESTIONS.map((q) => q.id);

  it("có đủ 5 RQ, 19 phương pháp, id không trùng", () => {
    expect(rqIds).toEqual(["RQ1", "RQ2", "RQ3", "RQ4", "RQ5"]);
    expect(METHODS.map((m) => m.n)).toEqual(Array.from({ length: 19 }, (_, i) => i + 1));
    const ids = [...HYPOTHESES.map((h) => h.id), ...RESULTS.map((r) => r.id)];
    expect(new Set(ids).size).toBe(ids.length);
  });

  it("mọi tham chiếu RQ và khâu đều tồn tại; RQ nào cũng có giả thuyết", () => {
    for (const h of HYPOTHESES) expect(rqIds).toContain(h.rq);
    for (const m of METHODS) {
      expect(STAGES).toContain(m.stage);
      for (const rq of m.rqs) expect(rqIds).toContain(rq);
    }
    for (const r of RESULTS) for (const rq of r.rqs) expect(rqIds).toContain(rq);
    for (const id of rqIds) expect(HYPOTHESES.some((h) => h.rq === id)).toBe(true);
  });

  it("kết quả đã đo có số, ngày, nguồn; chưa đo thì không có số", () => {
    for (const r of RESULTS) {
      expect(r.source.length).toBeGreaterThan(0);
      if (r.status === "measured") {
        expect(r.value).not.toBeNull();
        expect(r.date).toMatch(/^\d{4}-\d{2}-\d{2}$/);
      } else {
        expect(r.value).toBeNull();
      }
    }
  });

  it("số chính khớp nguồn và đúng loại nhãn", () => {
    const get = (id: string) => RESULTS.find((r) => r.id === id);
    expect(get("r-xlmr-cv5")).toMatchObject({ value: 0.615, labelSource: "human" });
    expect(get("r-phobert-cv5")).toMatchObject({ value: 0.538, labelSource: "human" });
    expect(get("r-semiauto-vs-human")).toMatchObject({ value: 0.4 });
    expect(get("r-re-human-vs-tree")).toMatchObject({ value: 0.472 });
    expect(get("r-sikubert-cv5")).toMatchObject({ value: 0.658, labelSource: "machine" });
    expect(get("r-sikubert-final")).toMatchObject({ value: 0.715, labelSource: "machine" });
  });

  it("lọc kết quả kết hợp RQ, trạng thái, loại nhãn và tìm không dấu", () => {
    const machine = filterResults({ query: "", rq: "all", status: "measured", label: "machine" });
    expect(machine.length).toBeGreaterThan(0);
    expect(machine.every((r) => r.labelSource === "machine" && r.status === "measured")).toBe(true);
    expect(filterResults({ query: "", rq: "RQ4", status: "all", label: "all" }).every((r) => r.rqs.includes("RQ4"))).toBe(true);
    expect(filterResults({ query: "sikubert", rq: "all", status: "todo", label: "all" })).toHaveLength(0);
    expect(matches("chuan vang muc cay", "Chuẩn vàng mức cây")).toBe(true);
  });
});

describe("ResearchHubPage", () => {
  it("là trang cha: dẫn tới đủ 7 trang con", () => {
    renderPage();
    const nav = screen.getByRole("navigation", { name: "Các trang con của đề tài" });
    const hrefs = [...nav.querySelectorAll("a")].map((a) => a.getAttribute("href"));
    expect(hrefs).toEqual([
      "/nghien-cuu/de-cuong.html",
      "/nghien-cuu/ket-qua.html",
      "/nghien-cuu/on-tap",
      "/nghien-cuu/hoi-nghi.html",
      "/nghien-cuu/slide-hoi-nghi.html",
      "/nghien-cuu/goi-viec.html",
      "/nghien-cuu/doi-chieu",
    ]);
  }, 30000);

  it("hiện 5 RQ và lọc theo RQ", async () => {
    renderPage();
    for (const q of RESEARCH_QUESTIONS) expect(screen.getByText(q.question)).toBeInTheDocument();
    fireEvent.change(screen.getByPlaceholderText(/Tìm/), { target: { value: "lan sang cay" } });
    expect(screen.getByText(RESEARCH_QUESTIONS[4].question)).toBeInTheDocument();
    expect(screen.queryByText(RESEARCH_QUESTIONS[0].question)).not.toBeInTheDocument();
  }, 30000);

  it("tab kết quả cảnh báo nhãn máy", () => {
    renderPage();
    fireEvent.click(screen.getByRole("tab", { name: "Kết quả" }));
    expect(screen.getByText("Đọc kết quả theo loại nhãn")).toBeInTheDocument();
    const machineMeasured = RESULTS.filter((r) => r.labelSource === "machine" && r.value !== null).length;
    expect(screen.getAllByText("Đo trên nhãn máy, không phải độ chính xác thật.")).toHaveLength(machineMeasured);
  }, 30000);

  it("tab hỏi–đáp dùng lại thẻ ôn tập và tìm được", () => {
    renderPage();
    fireEvent.click(screen.getByRole("tab", { name: "Hỏi–đáp" }));
    fireEvent.change(screen.getByPlaceholderText(/Tìm/), { target: { value: "research gap" } });
    expect(screen.getByText("Research gap của đề tài là gì?")).toBeInTheDocument();
    expect(screen.queryByText("Phát biểu hình thức bài toán của đề tài.")).not.toBeInTheDocument();
  }, 30000);
});
