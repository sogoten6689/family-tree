import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { render, screen } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import { afterEach, describe, expect, it, vi } from "vitest";

import { markChangedChars, sampleLines, summarize, toCsv } from "./doiChieuGrading";

if (typeof globalThis.ResizeObserver === "undefined") {
  globalThis.ResizeObserver = class {
    observe() {}
    unobserve() {}
    disconnect() {}
  } as unknown as typeof ResizeObserver;
}

const { default: DoiChieuPage } = await import("./DoiChieuPage");

describe("chấm mẫu", () => {
  const lines = Array.from({ length: 1000 }, (_, i) => i + 1);

  it("lấy 5% (tối thiểu 20), cố định theo khoá, không trùng", () => {
    const a = sampleLines(lines, "sv/nom-1");
    expect(a).toHaveLength(50);
    expect(new Set(a).size).toBe(50);
    expect(sampleLines(lines, "sv/nom-1")).toEqual(a);
    expect(sampleLines(lines, "sv/nom-2")).not.toEqual(a);
    expect(sampleLines(lines.slice(0, 100), "k")).toHaveLength(20);
    expect(sampleLines(lines.slice(0, 7), "k")).toHaveLength(7);
  });

  it("tỷ lệ lỗi = cặp lỗi / cặp đã chấm", () => {
    const s = summarize({ 1: "dung", 2: "OMISSION", 3: "ADDITION", 4: "dung" });
    expect(s).toMatchObject({ checked: 4, errors: 2, rate: 0.5, byType: { OMISSION: 1, ADDITION: 1, MISSING: 0 } });
    expect(summarize({}).rate).toBeNull();
  });

  it("CSV có BOM và bao ô có dấu phẩy", () => {
    const csv = toCsv([{ line: 1, han: "公回", viet: "Ông về, lánh đi", verdict: "dung" }]);
    expect(csv.startsWith("﻿dong,han,viet,nhan\n")).toBe(true);
    expect(csv).toContain('"Ông về, lánh đi"');
  });

  it("tô chữ Hán không có trong OCR, bỏ qua dấu câu", () => {
    const marks = markChangedChars("改姓名，", "改性名");
    expect(marks.filter((m) => m.changed).map((m) => m.ch)).toEqual(["姓"]);
  });
});

describe("trang đối chiếu", () => {
  afterEach(() => vi.unstubAllGlobals());

  const renderPage = (url = "/nghien-cuu/doi-chieu") =>
    render(
      <QueryClientProvider client={new QueryClient({ defaultOptions: { queries: { retry: false } } })}>
        <MemoryRouter initialEntries={[url]}>
          <DoiChieuPage />
        </MemoryRouter>
      </QueryClientProvider>,
    );

  it("hiện tiến độ từng sinh viên không cần đăng nhập", async () => {
    const fetchMock = vi.fn().mockResolvedValue(
      new Response(
        JSON.stringify({
          target: 2000,
          error_threshold: 0.3,
          students: [{ id: "sv-a", ten: "Sinh viên A", books: [], valid: 1500, pairs: 1600, format_errors: 3, submitted: 2 }],
        }),
        { status: 200 },
      ),
    );
    vi.stubGlobal("fetch", fetchMock);
    renderPage();
    expect(await screen.findByText("Sinh viên A")).toBeTruthy();
    expect(screen.getByText("1.500")).toBeTruthy();
    const headers = new Headers(fetchMock.mock.calls[0][1].headers);
    expect(headers.has("Authorization")).toBe(false);
  });

  it("báo khi máy chủ chưa có dữ liệu", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn().mockResolvedValue(new Response(JSON.stringify({ target: 2000, error_threshold: 0.3, students: [] }), { status: 200 })),
    );
    renderPage();
    expect(await screen.findByText("Chưa có bài nộp nào")).toBeTruthy();
  });
});
