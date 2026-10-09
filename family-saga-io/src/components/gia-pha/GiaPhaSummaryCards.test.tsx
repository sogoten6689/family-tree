import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";

import "@/i18n";
import type { GiaPhaSummary } from "@/lib/giaPhaApi";

const api = vi.hoisted(() => ({ getGiaPhaSummary: vi.fn() }));
vi.mock("@/lib/giaPhaApi", async (importOriginal) => ({
  ...(await importOriginal<typeof import("@/lib/giaPhaApi")>()),
  ...api,
}));

const { GiaPhaSummaryCards } = await import("./GiaPhaSummaryCards");

if (typeof globalThis.ResizeObserver === "undefined") {
  globalThis.ResizeObserver = class {
    observe() {}
    unobserve() {}
    disconnect() {}
  } as unknown as typeof ResizeObserver;
}

const SUMMARY: GiaPhaSummary = {
  scope: "admin",
  total: 22,
  built: 5,
  pending: 17,
  with_code: 12,
  without_code: 10,
  code_source: { catalogue: 9, gemini: 3, other: 0 },
  public_trees: 2,
  nodes: 340,
  top_ho_toc: [
    { ho_toc: "Nguyễn", count: 6 },
    { ho_toc: "Phan", count: 3 },
  ],
  pages: {
    scans: 22,
    pages: 1298,
    ocr_pages: 1298,
    transliteration_pages: 1212,
    translation_pages: 1298,
    ocr_percent: 100,
    transliteration_percent: 93.4,
    translation_percent: 100,
  },
  generated_at: "2026-10-09T10:00:00+00:00",
};

const renderCards = (props: { compact?: boolean } = {}) =>
  render(
    <QueryClientProvider client={new QueryClient({ defaultOptions: { queries: { retry: false, gcTime: 0 } } })}>
      <GiaPhaSummaryCards {...props} />
    </QueryClientProvider>,
  );

describe("GiaPhaSummaryCards", { timeout: 15000 }, () => {
  beforeEach(() => {
    api.getGiaPhaSummary.mockReset();
    api.getGiaPhaSummary.mockResolvedValue(SUMMARY);
  });

  it("shows loading placeholders, then the key numbers", async () => {
    renderCards();
    expect(screen.getByTestId("gia-pha-summary-loading")).toBeInTheDocument();
    expect(await screen.findByText("Tổng số bộ gia phả")).toBeInTheDocument();
    expect(screen.getByText("22")).toBeInTheDocument();
    expect(screen.getByText("Đã dựng cây")).toBeInTheDocument();
    expect(screen.getByText("23% tổng số bộ")).toBeInTheDocument(); // 5/22
    expect(screen.getByText("Chờ dựng cây")).toBeInTheDocument();
    expect(screen.getByText("12/22")).toBeInTheDocument();
    expect(screen.getByText("340 nhân vật trong các cây")).toBeInTheDocument();
  });

  it("full mode shows progress, code sources and the top family names", async () => {
    renderCards();
    await screen.findByText("Tiến độ xử lý văn bản");
    expect(screen.getByText("1.298 trang")).toBeInTheDocument();
    expect(screen.getByText("1.212/1.298 trang")).toBeInTheDocument(); // phiên âm
    expect(screen.getByText("Nguồn mã định danh")).toBeInTheDocument();
    expect(screen.getByText("Họ tộc nhiều bộ nhất")).toBeInTheDocument();
    expect(screen.getByText("Nguyễn")).toBeInTheDocument();
  });

  it("compact mode shows only the number tiles", async () => {
    renderCards({ compact: true });
    await screen.findByText("Tổng số bộ gia phả");
    expect(screen.queryByText("Tiến độ xử lý văn bản")).toBeNull();
    expect(screen.queryByText("Họ tộc nhiều bộ nhất")).toBeNull();
  });

  it("hides the private page progress for guests (pages = null)", async () => {
    api.getGiaPhaSummary.mockResolvedValue({ ...SUMMARY, scope: "public", pages: null });
    renderCards();
    await screen.findByText("Nguồn mã định danh");
    expect(screen.queryByText("Tiến độ xử lý văn bản")).toBeNull();
    expect(screen.queryByText(/nhân vật trong các cây/)).toBeNull(); // khách không thấy số nhân vật
  });

  it("the refresh button bypasses the server cache", async () => {
    renderCards();
    await screen.findByText("Tổng số bộ gia phả");
    expect(api.getGiaPhaSummary).toHaveBeenLastCalledWith(false);
    fireEvent.click(screen.getByRole("button", { name: /Làm mới số liệu/ }));
    await waitFor(() => expect(api.getGiaPhaSummary).toHaveBeenCalledTimes(2));
    expect(api.getGiaPhaSummary).toHaveBeenLastCalledWith(true);
  });

  it("shows an error with a retry button when the API fails", async () => {
    api.getGiaPhaSummary.mockRejectedValueOnce(new Error("boom"));
    renderCards();
    expect(await screen.findByText("Không tải được thống kê")).toBeInTheDocument();
    fireEvent.click(screen.getByRole("button", { name: /Tải lại/ }));
    expect(await screen.findByText("Tổng số bộ gia phả")).toBeInTheDocument();
  });
});
