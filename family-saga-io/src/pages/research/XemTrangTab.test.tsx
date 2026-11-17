import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { cleanup, fireEvent, render, screen, waitFor } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";

import type { BookDetail, XemTrang } from "@/lib/doiChieuApi";

import XemTrangTab, { AmHanViet } from "./XemTrangTab";

if (typeof globalThis.ResizeObserver === "undefined") {
  globalThis.ResizeObserver = class {
    observe() {}
    unobserve() {}
    disconnect() {}
  } as unknown as typeof ResizeObserver;
}

const view: XemTrang = {
  trang: "001",
  cap: [
    {
      trang: "001",
      han: "七信",
      viet: "Thất Tín",
      nguon: "may",
      sua_chu: false,
      dich_lai: false,
      am: [{ c: "七", a: "thất" }, { c: "信", a: "tín", k: ["thân"] }],
    },
    {
      trang: "001",
      han: "任屋，",
      viet: "Nhậm Ốc",
      nguon: "may",
      sua_chu: true,
      dich_lai: true,
      am: [{ c: "任", a: "nhậm", k: ["nhiệm"] }, { c: "屋", a: "ốc" }, { c: "，" }],
    },
  ],
  khung: {
    rong: 100,
    cao: 200,
    thieu: 1,
    chu: [
      { c: "七", b: [80, 10, 90, 20] },
      { c: "信", b: [80, 25, 90, 35] },
      { c: "任", b: [60, 10, 70, 20], u: 1 },
      { c: "屋", b: [60, 25, 70, 35] },
    ],
  },
};

const detail = { student: "chua-giao", book: "tq-1", pages: ["001", "002"] } as BookDetail;

const renderTab = () =>
  render(
    <QueryClientProvider client={new QueryClient({ defaultOptions: { queries: { retry: false } } })}>
      <XemTrangTab detail={detail} />
    </QueryClientProvider>,
  );

describe("xem trang song song", () => {
  afterEach(() => {
    cleanup();
    vi.unstubAllGlobals();
  });

  it("âm Hán Việt giữ dấu câu, đánh dấu chữ nhiều âm và chữ chưa có âm", () => {
    render(<AmHanViet am={[{ c: "七", a: "thất" }, { c: "行", a: "hàng", k: ["hành"] }, { c: "𧦬" }, { c: "，" }]} />);
    expect(document.body.textContent).toBe("thất hàng ?，");
    expect(screen.getAllByTestId("am-nhieu")).toHaveLength(1);
    expect(screen.getAllByTestId("am-thieu")).toHaveLength(1);
  });

  it("hiện ảnh có khung, bảng Hán | Âm | Nghĩa, và bấm dòng thì làm sáng khung của dòng đó", async () => {
    const fetchMock = vi.fn().mockResolvedValue(new Response(JSON.stringify(view), { status: 200 }));
    vi.stubGlobal("fetch", fetchMock);
    renderTab();
    await screen.findByText("Nhậm Ốc");
    expect(String(fetchMock.mock.calls[0][0])).toContain("/api/public/doi-chieu/chua-giao/tq-1/trang/001");
    expect(screen.getByText("thất")).toBeTruthy();
    expect(screen.getByText("sửa chữ")).toBeTruthy();
    expect(screen.getByText("dịch lại")).toBeTruthy();
    expect(screen.getByTestId("do-phu-khung").textContent).toContain("4/5");
    expect(screen.getAllByTestId("o-chu")).toHaveLength(4);
    expect(document.querySelectorAll("rect[data-dang-chon]")).toHaveLength(0);

    fireEvent.click(screen.getByText("Nhậm Ốc"));
    await waitFor(() => expect(document.querySelectorAll("rect[data-dang-chon]")).toHaveLength(2));

    fireEvent.click(screen.getAllByTestId("o-chu")[0]);
    await waitFor(() => expect(document.querySelectorAll("rect[data-dang-chon]")).toHaveLength(2));
    const lit = Array.from(document.querySelectorAll("rect[data-dang-chon]")).map((r) => r.getAttribute("x"));
    expect(lit).toEqual(["80", "80"]);
  }, 20000);

  it("trang chưa có khung vẫn hiện ảnh và bảng", async () => {
    vi.stubGlobal("fetch", vi.fn().mockResolvedValue(new Response(JSON.stringify({ ...view, khung: null }), { status: 200 })));
    renderTab();
    await screen.findByText("Trang này chưa có khung chữ; chỉ hiện ảnh gốc.");
    expect(screen.queryAllByTestId("o-chu")).toHaveLength(0);
    expect(screen.getByText("Thất Tín")).toBeTruthy();
  }, 20000);
});
