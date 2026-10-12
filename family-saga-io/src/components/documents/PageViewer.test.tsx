import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";

import "@/i18n";

const api = vi.hoisted(() => ({ listScanPages: vi.fn(), getScanPage: vi.fn(), editScanPage: vi.fn(), replaceScanPageImage: vi.fn(), ocrScanPage: vi.fn(), listPageEngines: vi.fn(() => Promise.resolve([])), runPageEngine: vi.fn() }));
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

  it("running an engine from the panel reloads the page list (an image-only page may get its first text and boxes)", async () => {
    api.listScanPages.mockResolvedValue(PAGES);
    api.getScanPage.mockImplementation((_s: number, n: number) => Promise.resolve(detailFor(n)));
    api.listPageEngines.mockResolvedValue([
      { name: "kim_hannom_lab", label: "Kim Hán Nôm Lab", present: false, runnable: true, ready: true, reason: null, paid: true },
    ]);
    api.runPageEngine.mockResolvedValue({ version: { version_id: 77, version_number: 3, is_current: false }, forked: true, engine: "kim_hannom_lab", text: "新", adopted_text: true, box_count: 4 });
    render(<PageViewer scanId={20} />);
    await screen.findByText("大尊圖");
    const before = api.listScanPages.mock.calls.length;
    fireEvent.click(await screen.findByRole("button", { name: "Chạy" }));
    fireEvent.click(await screen.findByRole("button", { name: /Chạy \(tốn tiền\)/ }));
    await waitFor(() => expect(api.runPageEngine).toHaveBeenCalled());
    await waitFor(() => expect(api.listScanPages.mock.calls.length).toBeGreaterThan(before)); // tải lại danh sách trang
    expect(api.listScanPages).toHaveBeenLastCalledWith(20, 77); // và xem bản sửa tay vừa tạo
    api.listPageEngines.mockImplementation(() => Promise.resolve([])); // không để mock rò sang test sau (file này không reset mock)
  });

  it("zoom view: next/previous page buttons change the page without closing the view", async () => {
    api.listScanPages.mockResolvedValue(PAGES);
    api.getScanPage.mockImplementation((_s: number, n: number) => Promise.resolve(detailFor(n)));
    render(<PageViewer scanId={20} />);
    await screen.findByText("大尊圖");
    fireEvent.click(screen.getByRole("button", { name: /Phóng to: Trang 1/ }));
    expect(await screen.findByTestId("zoom-position")).toHaveTextContent("1/2");
    expect(screen.getByRole("button", { name: /Trang trước/ })).toBeDisabled();
    fireEvent.click(screen.getByRole("button", { name: /Trang sau/ }));
    await waitFor(() => expect(screen.getByTestId("zoom-position")).toHaveTextContent("2/2"));
    // Trang 2 chưa có ảnh: khung vẫn mở và báo rõ, nút "Trang sau" khoá ở trang cuối, "Trang trước" quay lại được.
    expect(screen.getByTestId("zoom-body")).toHaveTextContent("Chưa có ảnh cho trang này");
    expect(screen.getByRole("button", { name: /Trang sau/ })).toBeDisabled();
    fireEvent.click(screen.getByRole("button", { name: /Trang trước/ }));
    await waitFor(() => expect(screen.getByTestId("zoom-position")).toHaveTextContent("1/2"));
    expect(screen.getByTestId("zoom-body").querySelector("img")).toHaveAttribute("src", PAGES[0].image_url);
  });

  it("boxes per model: a selector switches between the built-in boxes and each engine's boxes", async () => {
    const box = (order: number) => ({ order, bbox_xyxy: [10 * order, 20, 10 * order + 8, 90], han: "字", confidence: 0.9 });
    api.listScanPages.mockResolvedValue(PAGES);
    api.getScanPage.mockImplementation((_s: number, n: number) =>
      Promise.resolve({
        ...detailFor(n),
        ocr_bbox: n === 1 ? [box(1), box(2)] : null,
        ocr_bbox_engines: n === 1 ? { kim_hannom_lab: [box(1), box(2), box(3), box(4), box(5)] } : null,
      }),
    );
    render(<PageViewer scanId={20} />);
    // Mặc định: khung có sẵn (2 khung).
    expect(await screen.findByText(/Khung chữ — 2 khung/)).toBeInTheDocument();
    expect(screen.getByText("Khung có sẵn (2)")).toBeInTheDocument();
    expect(screen.getByText("Kim Hán Nôm Lab (5)")).toBeInTheDocument();
    // Chọn Kim Hán Nôm Lab → 5 khung.
    fireEvent.click(screen.getByText("Kim Hán Nôm Lab (5)"));
    expect(await screen.findByText(/Khung chữ — 5 khung/)).toBeInTheDocument();
  });

  it("boxes per model: no selector when the page has a single set of boxes", async () => {
    api.listScanPages.mockResolvedValue(PAGES);
    api.getScanPage.mockImplementation((_s: number, n: number) =>
      Promise.resolve({ ...detailFor(n), ocr_bbox: [{ order: 1, bbox_xyxy: [1, 2, 3, 4], han: "字" }], ocr_bbox_engines: null }),
    );
    render(<PageViewer scanId={20} />);
    expect(await screen.findByText(/Khung chữ — 1 khung/)).toBeInTheDocument();
    expect(screen.queryByText(/Khung có sẵn \(/)).not.toBeInTheDocument();
  });

  it("boxes per model: only engine boxes (no built-in boxes) are shown with their own label", async () => {
    api.listScanPages.mockResolvedValue(PAGES);
    api.getScanPage.mockImplementation((_s: number, n: number) =>
      Promise.resolve({ ...detailFor(n), ocr_bbox: null, ocr_bbox_engines: { kim_hannom_lab: [{ order: 1, bbox_xyxy: [1, 2, 3, 4], han: "字" }, { order: 2, bbox_xyxy: [5, 2, 7, 4], han: "字" }] } }),
    );
    render(<PageViewer scanId={20} />);
    expect(await screen.findByText(/Khung chữ — 2 khung/)).toBeInTheDocument();
  });

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

  it("replaces the page image, shows the new one and hides stale boxes", async () => {
    const withBoxes = { ...PAGES[0], ocr_vote_meta: null, ocr_bbox: [{ bbox_xyxy: [0, 0, 10, 10], han: "大", confidence: 0.9, order: 1 }] };
    api.listScanPages.mockResolvedValue(PAGES);
    api.getScanPage.mockResolvedValue(withBoxes);
    api.replaceScanPageImage.mockResolvedValue({
      page: { ...PAGES[0], image_url: "https://minio/gia-pha/20/pages/001-ab12cd34.png?sig" },
      previous_image_key: "gia-pha/20/pages/001.jpg",
    });
    render(<PageViewer scanId={20} />);
    await screen.findByText(/Khung chữ — /);
    const file = new File([new Uint8Array([137, 80, 78, 71])], "moi.png", { type: "image/png" });
    fireEvent.change(screen.getByTestId("page-image-input"), { target: { files: [file] } });
    await waitFor(() => expect(api.replaceScanPageImage).toHaveBeenCalledWith(20, 1, file));
    expect(await screen.findByText(/Đã thay ảnh trang này/)).toBeInTheDocument();
    expect(screen.queryByText(/Khung chữ — /)).not.toBeInTheDocument();
    expect(screen.getByRole("img", { name: "Trang 1" })).toHaveAttribute("src", "https://minio/gia-pha/20/pages/001-ab12cd34.png?sig");
  });

  it("shows the error when the image cannot be replaced and keeps the old image", async () => {
    api.listScanPages.mockResolvedValue(PAGES);
    api.getScanPage.mockImplementation((_s: number, n: number) => Promise.resolve(detailFor(n)));
    api.replaceScanPageImage.mockImplementation(() => Promise.reject(new Error("Chỉ nhận ảnh JPG, PNG, WEBP hoặc TIFF.")));
    render(<PageViewer scanId={20} />);
    await screen.findByText("大尊圖");
    fireEvent.change(screen.getByTestId("page-image-input"), { target: { files: [new File(["x"], "a.pdf")] } });
    expect(await screen.findByText("Chỉ nhận ảnh JPG, PNG, WEBP hoặc TIFF.")).toBeInTheDocument();
    expect(screen.getByRole("img", { name: "Trang 1" })).toHaveAttribute("src", PAGES[0].image_url);
    expect(screen.queryByText(/Đã thay ảnh trang này/)).not.toBeInTheDocument();
  });

  it("OCR again: asks for paid confirmation, then switches to the new version and warns about stale text", async () => {
    const OCRED = [{ ...PAGES[0], hannom_text: "新字一" }, PAGES[1]];
    api.listScanPages.mockImplementation((_s: number, v?: number) => Promise.resolve(v === 9 ? OCRED : PAGES));
    api.getScanPage.mockImplementation((_s: number, n: number) => Promise.resolve(detailFor(n)));
    api.ocrScanPage.mockResolvedValue({
      version: { version_id: 9, version_number: 4, is_current: false },
      page: OCRED[0],
      forked: true,
      engine: "kimhannom",
      box_count: 3,
      downstream_stale: true,
    });
    render(<PageViewer scanId={20} />);
    await screen.findByText("大尊圖");
    fireEvent.click(screen.getByRole("button", { name: /OCR lại trang/ }));
    expect(await screen.findByText(/TỐN TIỀN/)).toBeInTheDocument();
    expect(api.ocrScanPage).not.toHaveBeenCalled(); // chưa xác nhận thì không gọi
    fireEvent.click(screen.getByRole("button", { name: /OCR \(tốn tiền\)/ }));
    await waitFor(() => expect(api.ocrScanPage).toHaveBeenCalledWith(20, 1, { versionId: undefined }));
    expect(await screen.findByText("Bản sửa tay v4")).toBeInTheDocument();
    expect(await screen.findByText(/vẫn là của chữ cũ/)).toBeInTheDocument();
    await waitFor(() => expect(api.listScanPages).toHaveBeenLastCalledWith(20, 9));
  });

  it("OCR error is shown and nothing changes", async () => {
    api.listScanPages.mockResolvedValue(PAGES);
    api.getScanPage.mockImplementation((_s: number, n: number) => Promise.resolve(detailFor(n)));
    api.ocrScanPage.mockImplementation(() => Promise.reject(new Error("Kim Hán Nôm không trả về chữ")));
    render(<PageViewer scanId={20} />);
    await screen.findByText("大尊圖");
    fireEvent.click(screen.getByRole("button", { name: /OCR lại trang/ }));
    fireEvent.click(await screen.findByRole("button", { name: /OCR \(tốn tiền\)/ }));
    expect(await screen.findByText("Kim Hán Nôm không trả về chữ")).toBeInTheDocument();
    expect(screen.queryByText(/Bản sửa tay/)).not.toBeInTheDocument();
    expect(screen.queryByText(/vẫn là của chữ cũ/)).not.toBeInTheDocument();
  });
});
