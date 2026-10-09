import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";

import "@/i18n";

const api = vi.hoisted(() => ({ listScanPages: vi.fn(), getScanPage: vi.fn(), editScanPage: vi.fn() }));
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
    // Trang có vote → mở sẵn bước Vote.
    expect(await screen.findByText("Dòng 1")).toBeInTheDocument();
    expect(container.querySelector(".vote-ch-contested")?.textContent).toBe("圖");
    expect(container.querySelector(".vote-dis .vote-ch-rep")?.textContent).toBe("國");
    fireEvent.click(screen.getByText("1. OCR (theo từng engine)"));
    expect(await screen.findByText("paddle_v6")).toBeInTheDocument();
  });

  it("shows the boxed image and lists agreed lines in a collapsed section", async () => {
    const page = { ...PAGES[0], hannom_text: "大尊圖\n朱族家譜" };
    const boxes = [{ order: 1, bbox_xyxy: [10, 20, 60, 900], han: "大尊圖", confidence: 0.9 }];
    api.listScanPages.mockResolvedValue([page]);
    api.getScanPage.mockResolvedValue({ ...page, ocr_vote_meta: META, ocr_bbox: boxes });
    render(<PageViewer scanId={20} />);
    expect(await screen.findByText(/1 khung, số = thứ tự đọc/)).toBeInTheDocument();
    expect(screen.getByRole("img", { name: "Trang 1 có khung chữ" })).toHaveAttribute("src", page.image_url);
    fireEvent.click(screen.getByText("Các dòng đã thống nhất (1)"));
    expect(await screen.findByText("朱族家譜")).toBeInTheDocument();
    expect(screen.getByText("Dòng 2")).toBeInTheDocument();
  });

  it("says when a page has no boxes", async () => {
    api.listScanPages.mockResolvedValue(PAGES);
    api.getScanPage.mockImplementation((_s: number, n: number) => Promise.resolve(detailFor(n)));
    render(<PageViewer scanId={20} />);
    expect(await screen.findByText("Chưa có khung chữ cho trang này.")).toBeInTheDocument();
  });

  it("warns when the Han text changed after a re-vote", async () => {
    const v2 = { schema_version: 2, vote_method: "char_majority", backbone: "paddle_v6", page_status: "ok",
      thresholds: { auto_min: 3, suggest_min: 2 }, stats: { chars: 3 }, review_rate: 0, uncertain_rate: 0,
      engines: {}, lines: ["大尊圖"], slots: [], downstream_stale: true };
    api.listScanPages.mockResolvedValue(PAGES);
    api.getScanPage.mockImplementation((_s: number, n: number) => Promise.resolve({ ...PAGES[n - 1], ocr_vote_meta: v2 }));
    render(<PageViewer scanId={20} />);
    expect(await screen.findByText(/đã đổi sau khi vote lại/)).toBeInTheDocument();
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

  it("edits a page: sends only changed fields, forks a manual-edit version and switches to it", async () => {
    const EDITED = [{ ...PAGES[0], hannom_text: "大尊國" }, PAGES[1]];
    api.listScanPages.mockImplementation((_s: number, v?: number) => Promise.resolve(v === 7 ? EDITED : PAGES));
    api.getScanPage.mockImplementation((_s: number, n: number) => Promise.resolve(detailFor(n)));
    api.editScanPage.mockResolvedValue({
      version: { version_id: 7, version_number: 3, is_current: false },
      page: EDITED[0],
      forked: true,
    });
    render(<PageViewer scanId={20} />);
    await screen.findByText("大尊圖");
    fireEvent.click(screen.getByRole("button", { name: /Sửa trang/ }));
    fireEvent.change(await screen.findByLabelText("Chữ Hán Nôm"), { target: { value: "大尊國" } });
    fireEvent.click(screen.getByRole("button", { name: "Lưu" }));
    await waitFor(() => expect(api.editScanPage).toHaveBeenCalledTimes(1));
    expect(api.editScanPage).toHaveBeenCalledWith(20, 1, { version_id: undefined, hannom_text: "大尊國" });
    expect(await screen.findByText("Bản sửa tay v3")).toBeInTheDocument();
    await waitFor(() => expect(api.listScanPages).toHaveBeenLastCalledWith(20, 7));
    expect(await screen.findByText("大尊國")).toBeInTheDocument();
  });

  it("does not call the API when nothing changed", async () => {
    api.listScanPages.mockResolvedValue(PAGES);
    api.getScanPage.mockImplementation((_s: number, n: number) => Promise.resolve(detailFor(n)));
    api.editScanPage.mockClear();
    render(<PageViewer scanId={20} />);
    await screen.findByText("大尊圖");
    fireEvent.click(screen.getByRole("button", { name: /Sửa trang/ }));
    fireEvent.click(await screen.findByRole("button", { name: "Lưu" }));
    await waitFor(() => expect(screen.queryByRole("button", { name: "Lưu" })).not.toBeInTheDocument());
    expect(api.editScanPage).not.toHaveBeenCalled();
  });

  it("shows the save error and keeps the dialog open", async () => {
    api.listScanPages.mockResolvedValue(PAGES);
    api.getScanPage.mockImplementation((_s: number, n: number) => Promise.resolve(detailFor(n)));
    api.editScanPage.mockImplementation(() => Promise.reject(new Error("Tài liệu không tồn tại.")));
    render(<PageViewer scanId={20} />);
    await screen.findByText("大尊圖");
    fireEvent.click(screen.getByRole("button", { name: /Sửa trang/ }));
    fireEvent.change(await screen.findByLabelText("Phiên âm"), { target: { value: "Đại tôn" } });
    fireEvent.click(screen.getByRole("button", { name: "Lưu" }));
    expect(await screen.findByText("Tài liệu không tồn tại.")).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Lưu" })).toBeInTheDocument();
  });
});
