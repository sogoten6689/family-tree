import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { render, screen } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import { describe, expect, it, vi } from "vitest";

import type { TienDo } from "@/lib/doiChieuApi";

if (typeof globalThis.ResizeObserver === "undefined") {
  globalThis.ResizeObserver = class {
    observe() {}
    unobserve() {}
    disconnect() {}
  } as unknown as typeof ResizeObserver;
}

const now = new Date().toISOString();
const DATA: TienDo = {
  luc: now,
  trang_thai: { cap_nhat: "19/11 10:00", xong: ["9 cuốn đã có khung"], dang_lam: ["Vòng kiểm thử 21"], cho_quyet: [] },
  cuon: [
    { student: "chua-giao", book: "tq-950", ten: "Gia phả A", trang_anh: 10, trang_khung: 4, chu: 900, uoc: 10, thieu: 100, cap_nhat: now },
    { student: "chua-giao", book: "tq-588", ten: null, trang_anh: 5, trang_khung: 5, chu: 100, uoc: 0, thieu: 0, cap_nhat: "2026-01-01T00:00:00+00:00" },
  ],
};

vi.mock("@/lib/doiChieuApi", () => ({ getTienDo: () => Promise.resolve(DATA) }));

const { default: TienDoPage, tuLuc } = await import("./TienDoPage");

describe("trang tiến độ khung chữ", () => {
  it("hiện ghi chú Xong / Đang làm / Chờ quyết, tổng và từng cuốn", async () => {
    render(
      <QueryClientProvider client={new QueryClient()}>
        <MemoryRouter>
          <TienDoPage />
        </MemoryRouter>
      </QueryClientProvider>,
    );
    expect(await screen.findByText("9 cuốn đã có khung")).toBeTruthy();
    expect(screen.getByText("Vòng kiểm thử 21")).toBeTruthy();
    expect(screen.getByText("9 / 15")).toBeTruthy();
    expect(screen.getByText("Gia phả A (tq-950)").closest("a")?.getAttribute("href")).toBe("/nghien-cuu/doi-chieu?sv=chua-giao&cuon=tq-950");
    expect(screen.getByText(/đang chạy/)).toBeTruthy();
    expect(screen.getAllByText(/đang chạy/)).toHaveLength(1);
  });

  it("ghi thời gian dễ đọc", () => {
    const t = Date.parse("2026-11-19T10:00:00Z");
    expect(tuLuc("2026-11-19T09:59:30Z", t)).toBe("vừa xong");
    expect(tuLuc("2026-11-19T09:45:00Z", t)).toBe("15 phút trước");
    expect(tuLuc("2026-11-19T07:00:00Z", t)).toBe("3 giờ trước");
    expect(tuLuc(null, t)).toBe("—");
  });
});
