import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { render, screen } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import { describe, expect, it, vi } from "vitest";

import type { Overview, TienDo } from "@/lib/doiChieuApi";

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

const cham = { checked: 0, sample: 20, errors: 0, by_type: { OMISSION: 0, ADDITION: 0, MISSING: 0 }, rate: null, complete: false, dat: false };
const bo = (da_soat: number, may: number, trang_da_soat: number, trang: number) => ({
  da_soat, may, trang, trang_da_soat, bo: { thieu_ve: 0, han_khong_co_chu_han: 0, viet_lan_chu_han: 0, trung: 0 }, bo_ghi_chu: 0,
  sua_vote: 0, sua_vote_cho: 0, sua_vote_giu_nen: 0, sua_vote_khong_khop: 0, sua_vote_nghi_lech: 0, dich_lai: 0, dich_lai_con: 0,
});
const book = (id: string, extra: object) => ({
  id, ten: null, link: null, nguon: "anh" as const, tsv: null, pairs: 0, valid: 0, format_errors: 0, machine_rows: 0, machine_pages: 0,
  ocr_coverage: null, image_pages: 0, cham, vote: null, bo: null, ...extra,
});
const OVERVIEW: Overview = {
  target: 2000,
  error_threshold: 0.15,
  students: [
    {
      id: "chua-giao", ten: "Chưa giao", valid: 0, pairs: 0, format_errors: 0, submitted: 0, quality_pairs: 0, valid_ban_dich_san: 0,
      books: [
        book("tq-950", { ten: "Gia phả A", bo: bo(1706, 0, 103, 103), cham: { ...cham, checked: 86, sample: 86, rate: 0.05, complete: true, dat: true } }),
        book("tq-678", { bo: bo(0, 4529, 0, 83) }),
      ],
    },
    {
      id: "sv-b", ten: "Sinh viên B", valid: 487, pairs: 487, format_errors: 0, submitted: 1, quality_pairs: 0, valid_ban_dich_san: 0,
      books: [book("nom-1", {}), book("nom-2", {})],
    },
  ],
};

vi.mock("@/lib/doiChieuApi", () => ({ getTienDo: () => Promise.resolve(DATA), getOverview: () => Promise.resolve(OVERVIEW) }));

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
    expect(screen.getAllByText("Gia phả A (tq-950)")[0].closest("a")?.getAttribute("href")).toBe("/nghien-cuu/doi-chieu?sv=chua-giao&cuon=tq-950");
    expect(screen.getByText(/đang chạy/)).toBeTruthy();
    expect(screen.getAllByText(/đang chạy/)).toHaveLength(1);
  });

  it("hiện dóng hàng từng cuốn nhóm chưa giao và bài nộp của sinh viên", async () => {
    render(
      <QueryClientProvider client={new QueryClient()}>
        <MemoryRouter>
          <TienDoPage />
        </MemoryRouter>
      </QueryClientProvider>,
    );
    expect(await screen.findByText("1.706")).toBeTruthy();
    expect(screen.getByText("4.529")).toBeTruthy();
    expect(screen.getByText("103 / 186")).toBeTruthy();
    expect(screen.getByText("chưa chấm")).toBeTruthy();
    expect(screen.getByText("đạt")).toBeTruthy();
    const links = screen.getAllByText("Xem kết quả →").map((a) => a.closest("a")?.getAttribute("href"));
    expect(links).toEqual(["/nghien-cuu/doi-chieu?sv=chua-giao&cuon=tq-950", "/nghien-cuu/doi-chieu?sv=chua-giao&cuon=tq-678"]);
    expect(screen.getByText("Sinh viên B")).toBeTruthy();
    expect(screen.getByText("1 / 2")).toBeTruthy();
    expect(screen.queryByText("Chưa giao")).toBeNull();
  });

  it("ghi thời gian dễ đọc", () => {
    const t = Date.parse("2026-11-19T10:00:00Z");
    expect(tuLuc("2026-11-19T09:59:30Z", t)).toBe("vừa xong");
    expect(tuLuc("2026-11-19T09:45:00Z", t)).toBe("15 phút trước");
    expect(tuLuc("2026-11-19T07:00:00Z", t)).toBe("3 giờ trước");
    expect(tuLuc(null, t)).toBe("—");
  });
});
