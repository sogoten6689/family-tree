import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";

import "@/i18n";
import type { LlmImportResult, ScanVersion } from "@/lib/llmImportApi";

const api = vi.hoisted(() => ({
  listScanVersions: vi.fn(),
  importLlmResults: vi.fn(),
  reviewVersion: vi.fn(),
  fetchTrainingExport: vi.fn(),
  listEnabledTextEngines: vi.fn(),
  runTextEngine: vi.fn(),
}));
vi.mock("@/lib/llmImportApi", async (importOriginal) => ({
  ...(await importOriginal<typeof import("@/lib/llmImportApi")>()),
  ...api,
}));

const { LlmImportPanel } = await import("./LlmImportPanel");

// jsdom 20.0.3 không có File.prototype.text (trình duyệt thật đều có) —
// polyfill bằng FileReader chỉ trong test này, không đổi code production.
if (typeof File.prototype.text !== "function") {
  File.prototype.text = function text(this: File) {
    return new Promise<string>((resolve, reject) => {
      const reader = new FileReader();
      reader.onload = () => resolve(String(reader.result));
      reader.onerror = () => reject(reader.error);
      reader.readAsText(this);
    });
  };
}

const version = (over: Partial<ScanVersion>): ScanVersion => ({
  version_id: 1,
  version_number: 1,
  is_current: true,
  status: "done",
  parent_version_id: null,
  source: null,
  review_status: null,
  note: null,
  created_at: null,
  ...over,
});

const preview = (over: Partial<LlmImportResult>): LlmImportResult => ({
  ok: true,
  dry_run: true,
  pages: 1,
  records: 1,
  skipped_annotations: 0,
  errors: [],
  warnings: [],
  version: null,
  ...over,
});

async function chooseFile() {
  const file = new File([JSON.stringify([{ page: 1, cn: "乾", sv: "Càn", vi: "Trời" }])], "out.json", {
    type: "application/json",
  });
  fireEvent.click(screen.getByRole("button", { name: /Nhập kết quả LLM/ }));
  fireEvent.change(await screen.findByLabelText("File kết quả"), { target: { files: [file] } });
  await screen.findByText(/out.json: 1 record/);
}

const okButton = () => screen.getByRole("button", { name: "Nhập" });

describe("LlmImportPanel", { timeout: 15000 }, () => {
  beforeEach(() => {
    Object.values(api).forEach((fn) => fn.mockReset());
    api.listEnabledTextEngines.mockResolvedValue(["gemini-web"]);
    api.listScanVersions.mockResolvedValue([
      version({}),
      version({ version_id: 2, version_number: 2, is_current: false, source: "chatgpt-web", review_status: "pending" }),
    ]);
  });

  it("only admins see review and export buttons", async () => {
    const { unmount } = render(<LlmImportPanel scanId={7} isAdmin={false} />);
    await screen.findByText("chatgpt-web");
    expect(screen.queryByRole("button", { name: /Duyệt/ })).toBeNull();
    expect(screen.queryByRole("button", { name: /Xuất dữ liệu train/ })).toBeNull();
    unmount();

    render(<LlmImportPanel scanId={7} isAdmin />);
    await screen.findByText("chatgpt-web");
    expect(screen.getAllByRole("button", { name: /Duyệt/ })).toHaveLength(1); // chỉ version nhập từ LLM
    expect(screen.getByRole("button", { name: /Xuất dữ liệu train/ })).toBeInTheDocument();
  });

  it("approving calls the review API", async () => {
    api.reviewVersion.mockResolvedValue(version({}));
    render(<LlmImportPanel scanId={7} isAdmin />);
    fireEvent.click(await screen.findByRole("button", { name: /Duyệt/ }));
    await waitFor(() => expect(api.reviewVersion).toHaveBeenCalledWith(7, 2, "approved"));
  });

  it("requires a successful preview before importing", async () => {
    api.importLlmResults.mockResolvedValueOnce(preview({ warnings: ["Trang 1: chỉ 50% chữ Hán…"] }));
    api.importLlmResults.mockResolvedValueOnce(preview({ dry_run: false, version: version({ version_number: 3 }) }));
    render(<LlmImportPanel scanId={7} isAdmin={false} />);
    await chooseFile();
    expect(okButton()).toBeDisabled();

    fireEvent.click(screen.getByRole("button", { name: /Kiểm tra/ }));
    await screen.findByText("Trang 1: chỉ 50% chữ Hán…");
    expect(api.importLlmResults).toHaveBeenLastCalledWith(7, expect.objectContaining({ source: "chatgpt-web" }), true);
    expect(okButton()).not.toBeDisabled();

    fireEvent.click(okButton());
    await waitFor(() => expect(api.importLlmResults).toHaveBeenLastCalledWith(7, expect.anything(), false));
  });

  it("blocks import when the preview has errors", async () => {
    api.importLlmResults.mockResolvedValue(preview({ ok: false, errors: ["records[0]: thiếu sv."] }));
    render(<LlmImportPanel scanId={7} isAdmin={false} />);
    await chooseFile();
    fireEvent.click(screen.getByRole("button", { name: /Kiểm tra/ }));
    await screen.findByText("records[0]: thiếu sv.");
    expect(okButton()).toBeDisabled();
  });

  it("runs the selected engine", async () => {
    api.runTextEngine.mockResolvedValue(version({ version_id: 9, version_number: 3, source: "engine-gemini-web" }));
    render(<LlmImportPanel scanId={7} isAdmin />);
    await screen.findByText("gemini-web");
    fireEvent.click(screen.getByRole("button", { name: /Chạy engine/ }));
    await waitFor(() => expect(api.runTextEngine).toHaveBeenCalledWith(7, "gemini-web"));
  });

  it("hides engine runs from non-admins (running costs money)", async () => {
    render(<LlmImportPanel scanId={7} isAdmin={false} />);
    await screen.findByText("chatgpt-web");
    expect(screen.queryByRole("button", { name: /Chạy engine/ })).not.toBeInTheDocument();
    expect(api.listEnabledTextEngines).not.toHaveBeenCalled();
  });

  it("disables running when no engine is enabled", async () => {
    api.listEnabledTextEngines.mockResolvedValue([]);
    render(<LlmImportPanel scanId={7} isAdmin />);
    await screen.findByText("chatgpt-web");
    expect(screen.getByRole("button", { name: /Chạy engine/ })).toBeDisabled();
  });

  it("shows run status and polls while an engine run is active", async () => {
    const running = version({
      version_id: 5,
      version_number: 5,
      is_current: false,
      source: "engine-gemini-web",
      review_status: "approved",
      steps: [
        { step_type: "transliteration", status: "running" },
        { step_type: "translation", status: "running" },
      ],
    });
    const done = {
      ...running,
      steps: [
        { step_type: "transliteration" as const, status: "done" },
        { step_type: "translation" as const, status: "done" },
      ],
    };
    api.listScanVersions.mockResolvedValueOnce([running]).mockResolvedValue([done]);
    vi.useFakeTimers({ shouldAdvanceTime: true });
    try {
      render(<LlmImportPanel scanId={7} isAdmin={false} />);
      await screen.findByText("Đang chạy");
      await vi.advanceTimersByTimeAsync(5000);
      await screen.findByText("Xong");
      const calls = api.listScanVersions.mock.calls.length;
      await vi.advanceTimersByTimeAsync(10000);
      expect(api.listScanVersions.mock.calls.length).toBe(calls); // hết job → ngừng poll
    } finally {
      vi.useRealTimers();
    }
  });
});
