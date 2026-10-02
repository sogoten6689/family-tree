import { fireEvent, render, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";

import "@/i18n";

const api = vi.hoisted(() => ({ listScanPages: vi.fn(), getScanPage: vi.fn() }));
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

const META = {
  vote_method: "paddle_v6_backbone_line_vote_levenshtein_2_other",
  engines: { paddle_v6: { text: "大尊圖", score: 0.9, similarity_to_others: 0.8 } },
  uncertain_rate: 0.5,
  uncertain_spans: [
    {
      line: 0,
      voted_line: "大尊圖",
      method: "line_no_majority",
      n_agree: 1,
      n_total: 3,
      disagreeing: [{ engine: "gemini", text: "大尊國", similarity: 0.66, diff: [{ op: "equal", text: "大尊" }, { op: "replace", text: "國" }] }],
      voted_segments: [{ text: "大尊", contested: false }, { text: "圖", contested: true }],
    },
  ],
  structural_diffs: [],
};
const detailFor = (n: number) => ({ ...PAGES[n - 1], ocr_vote_meta: n === 1 ? META : null });

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
    api.getScanPage.mockImplementation((_s: number, n: number) => Promise.resolve(detailFor(n)));
    render(<PageViewer scanId={20} />);
    expect(await screen.findByText("大尊圖")).toBeInTheDocument();
    expect(screen.getByRole("img", { name: "Trang 1" })).toHaveAttribute("src", PAGES[0].image_url);
    expect(screen.getByText("1/2 trang có ảnh")).toBeInTheDocument();
    expect(api.listScanPages).toHaveBeenCalledWith(20);
  });

  it("moves to the next page and shows a placeholder when there is no image", async () => {
    api.listScanPages.mockResolvedValue(PAGES);
    api.getScanPage.mockImplementation((_s: number, n: number) => Promise.resolve(detailFor(n)));
    render(<PageViewer scanId={20} />);
    await screen.findByText("大尊圖");
    fireEvent.click(screen.getByTitle("Next Page"));
    expect(await screen.findByText("家譜")).toBeInTheDocument();
    expect(screen.getByText("Chưa có ảnh cho trang này")).toBeInTheDocument();
    expect(screen.queryByRole("img", { name: "Trang 2" })).toBeNull();
    expect(api.getScanPage).toHaveBeenLastCalledWith(20, 2);
    expect(await screen.findByText(/pipeline v1/)).toBeInTheDocument(); // trang 2 không có OCR/vote
  });

  it("shows per-engine OCR and disputed vote lines for the page", async () => {
    api.listScanPages.mockResolvedValue(PAGES);
    api.getScanPage.mockImplementation((_s: number, n: number) => Promise.resolve(detailFor(n)));
    const { container } = render(<PageViewer scanId={20} />);
    expect(await screen.findByText("paddle_v6")).toBeInTheDocument(); // bước OCR
    fireEvent.click(screen.getByText("2. Vote (hợp nhất)"));
    expect(await screen.findByText("Dòng 1")).toBeInTheDocument();
    expect(container.querySelector(".vote-ch-contested")?.textContent).toBe("圖");
    expect(container.querySelector(".vote-dis .vote-ch-rep")?.textContent).toBe("國");
  });

  it("still shows the page when OCR/vote cannot be loaded", async () => {
    api.listScanPages.mockResolvedValue(PAGES);
    api.getScanPage.mockImplementation(() => Promise.reject(new Error("Lỗi OCR")));
    render(<PageViewer scanId={20} />);
    expect(await screen.findByText("Lỗi OCR")).toBeInTheDocument();
    expect(screen.getByText("大尊圖")).toBeInTheDocument();
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
