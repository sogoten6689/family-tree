import { fireEvent, render, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";

import "@/i18n";

const api = vi.hoisted(() => ({ listScanPages: vi.fn() }));
vi.mock("@/lib/userWorkspaceApi", async (importOriginal) => ({
  ...(await importOriginal<typeof import("@/lib/userWorkspaceApi")>()),
  ...api,
}));

const { PageViewer } = await import("./PageViewer");

const PAGES = [
  { page_number: 1, image_url: "https://minio/gia-pha/20/pages/001.jpg?sig", hannom_text: "大尊圖", transliteration_text: null, translation_text: "Đại tôn đồ" },
  { page_number: 2, image_url: null, hannom_text: "家譜", transliteration_text: "Gia phả", translation_text: null },
];

describe("PageViewer", { timeout: 15000 }, () => {
  // KHÔNG dùng beforeEach(mockReset/mockClear): với vitest 3.2.4, có thao tác
  // đó thì test "API error" báo lỗi chính Error giả dù component đã bắt lỗi và
  // hiện Alert (đối chứng 02/10/2026: bỏ beforeEach → 4/4 pass; chưa rõ cơ chế
  // bên trong vitest). Mỗi test tự đặt kết quả giả nên không rò trạng thái.

  it("shows the page image next to its texts and the image count", async () => {
    api.listScanPages.mockResolvedValue(PAGES);
    render(<PageViewer scanId={20} />);
    expect(await screen.findByText("大尊圖")).toBeInTheDocument();
    expect(screen.getByText("Đại tôn đồ")).toBeInTheDocument();
    expect(screen.getByRole("img", { name: "Trang 1" })).toHaveAttribute("src", PAGES[0].image_url);
    expect(screen.getByText("1/2 trang có ảnh")).toBeInTheDocument();
    expect(api.listScanPages).toHaveBeenCalledWith(20);
  });

  it("moves to the next page and shows a placeholder when there is no image", async () => {
    api.listScanPages.mockResolvedValue(PAGES);
    render(<PageViewer scanId={20} />);
    await screen.findByText("大尊圖");
    fireEvent.click(screen.getByTitle("Next Page"));
    expect(await screen.findByText("家譜")).toBeInTheDocument();
    expect(screen.getByText("Chưa có ảnh cho trang này")).toBeInTheDocument();
    expect(screen.queryByRole("img", { name: "Trang 2" })).toBeNull();
  });

  it("shows an empty state when there are no pages", async () => {
    api.listScanPages.mockResolvedValue([]);
    render(<PageViewer scanId={1} />);
    expect(await screen.findByText("Bộ này chưa có trang.")).toBeInTheDocument();
  });

  it("shows the API error (e.g. no access)", async () => {
    api.listScanPages.mockImplementation(() => Promise.reject(new Error("Tài liệu không tồn tại.")));
    render(<PageViewer scanId={1} />);
    expect(await screen.findByText("Tài liệu không tồn tại.")).toBeInTheDocument();
  });
});
