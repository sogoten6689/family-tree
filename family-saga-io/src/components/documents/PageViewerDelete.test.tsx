import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { Modal } from "antd";
import { afterEach, describe, expect, it, vi } from "vitest";

import "@/i18n";

// Tách khỏi PageViewer.test.tsx: file đó đã dài (nhiều hộp thoại antd) nên các test chạy cuối
// bị jsdom làm chậm dần tới hết giờ; file riêng thì mỗi test chỉ vài giây.
const api = vi.hoisted(() => ({
  listScanPages: vi.fn(),
  getScanPage: vi.fn(),
  deleteScanPage: vi.fn(),
  listDeletedScanPages: vi.fn(),
  restoreScanPage: vi.fn(),
}));
vi.mock("@/lib/userWorkspaceApi", async (importOriginal) => ({
  ...(await importOriginal<typeof import("@/lib/userWorkspaceApi")>()),
  ...api,
}));

const { PageViewer } = await import("./PageViewer");

if (typeof globalThis.ResizeObserver === "undefined") {
  globalThis.ResizeObserver = class {
    observe() {}
    unobserve() {}
    disconnect() {}
  } as unknown as typeof ResizeObserver;
}

const PAGES = [
  { page_number: 1, image_url: null, hannom_text: "大尊圖", transliteration_text: null, translation_text: "Đại tôn đồ" },
  { page_number: 2, image_url: null, hannom_text: "家譜", transliteration_text: "Gia phả", translation_text: null },
];
const detailFor = (n: number) => ({ ...PAGES[n - 1], ocr_vote_meta: null });

describe("PageViewer — xoá mềm trang", { timeout: 15000 }, () => {
  // Modal.confirm là hộp thoại tĩnh, nằm ngoài cây React nên RTL không tự dọn.
  afterEach(() => Modal.destroyAll());

  it("soft-deletes the current page after confirmation and moves to the next one", async () => {
    api.listScanPages.mockResolvedValue(PAGES);
    api.getScanPage.mockImplementation((_s: number, n: number) => Promise.resolve(detailFor(n)));
    api.deleteScanPage.mockResolvedValue({ page_number: 1, deleted: true, active_pages: 1 });
    render(<PageViewer scanId={20} />);
    await screen.findByText("大尊圖");
    fireEvent.click(screen.getAllByRole("button", { name: /Xoá trang/ })[0]); // nút trên thanh công cụ
    expect(await screen.findByText(/khôi phục lại được/)).toBeInTheDocument();
    expect(api.deleteScanPage).not.toHaveBeenCalled(); // chưa xác nhận thì không xoá
    fireEvent.click(screen.getAllByRole("button", { name: /Xoá trang/ }).at(-1)!); // nút xác nhận trong hộp thoại
    await waitFor(() => expect(api.deleteScanPage).toHaveBeenCalledWith(20, 1));
    expect(await screen.findByText("家譜")).toBeInTheDocument(); // còn trang 2
    expect(screen.queryByText("大尊圖")).not.toBeInTheDocument();
  });

  it("lists deleted pages and restores one, reloading the page list", async () => {
    const BACK = [PAGES[0], PAGES[1], { page_number: 3, image_url: null, hannom_text: "復", transliteration_text: null, translation_text: null }];
    api.listScanPages.mockResolvedValueOnce(PAGES).mockResolvedValue(BACK);
    api.getScanPage.mockImplementation((_s: number, n: number) => Promise.resolve(detailFor(n)));
    api.listDeletedScanPages.mockResolvedValue([{ page_number: 3, deleted_at: "2026-10-09T08:00:00+00:00", image_url: null, hannom_text: "復" }]);
    api.restoreScanPage.mockResolvedValue({ page_number: 3, deleted: false, active_pages: 3 });
    render(<PageViewer scanId={20} />);
    await screen.findByText("大尊圖");
    fireEvent.click(screen.getByRole("button", { name: /Trang đã xoá/ }));
    expect(await screen.findByText("復")).toBeInTheDocument();
    fireEvent.click(screen.getByRole("button", { name: "Khôi phục" }));
    await waitFor(() => expect(api.restoreScanPage).toHaveBeenCalledWith(20, 3));
    await waitFor(() => expect(api.listScanPages.mock.calls.length).toBeGreaterThan(1));
    expect(await screen.findByText("Không có trang nào đã xoá.")).toBeInTheDocument();
  });

  it("shows the error when a page cannot be deleted and keeps the page", async () => {
    api.listScanPages.mockResolvedValue(PAGES);
    api.getScanPage.mockImplementation((_s: number, n: number) => Promise.resolve(detailFor(n)));
    api.deleteScanPage.mockImplementation(() => Promise.reject(new Error("Tài liệu không tồn tại.")));
    render(<PageViewer scanId={20} />);
    await screen.findByText("大尊圖");
    fireEvent.click(screen.getAllByRole("button", { name: /Xoá trang/ })[0]); // nút trên thanh công cụ
    await screen.findByText(/khôi phục lại được/);
    fireEvent.click(screen.getAllByRole("button", { name: /Xoá trang/ }).at(-1)!); // nút xác nhận trong hộp thoại
    expect(await screen.findByText("Tài liệu không tồn tại.")).toBeInTheDocument();
    expect(screen.getByText("大尊圖")).toBeInTheDocument();
  });
});
