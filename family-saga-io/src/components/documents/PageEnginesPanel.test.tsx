import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";

import "@/i18n";

const api = vi.hoisted(() => ({ listPageEngines: vi.fn(), runPageEngine: vi.fn() }));
vi.mock("@/lib/userWorkspaceApi", async (importOriginal) => ({
  ...(await importOriginal<typeof import("@/lib/userWorkspaceApi")>()),
  ...api,
}));

const { PageEnginesPanel } = await import("./PageEnginesPanel");

const ENGINES = [
  { name: "paddle_v6", label: "PaddleOCR v6", present: true, runnable: false, ready: false, reason: "Server chưa cài PaddleOCR", paid: false },
  { name: "gemini", label: "Gemini Vision", present: false, runnable: true, ready: true, reason: null, paid: true },
  { name: "deepseek", label: "DeepSeek OCR", present: false, runnable: false, ready: false, reason: "Chưa có adapter DeepSeek", paid: true },
];

describe("PageEnginesPanel", () => {
  it("shows which engines have a result and offers a run button only for runnable missing ones", async () => {
    api.listPageEngines.mockResolvedValue(ENGINES);
    render(<PageEnginesPanel scanId={20} pageNumber={3} onRan={() => {}} />);
    expect(await screen.findByText("PaddleOCR v6 ✓")).toBeInTheDocument();
    expect(screen.getByText(/1\/3 engine có kết quả/)).toBeInTheDocument();
    const runButtons = screen.getAllByRole("button", { name: "Chạy" });
    expect(runButtons).toHaveLength(2);
    expect(runButtons[0]).toBeEnabled(); // Gemini chạy được
    expect(runButtons[1]).toBeDisabled(); // DeepSeek chưa có adapter
    expect(api.listPageEngines).toHaveBeenCalledWith(20, 3, undefined);
  });

  it("asks for a paid confirmation, runs the engine, then reports the new version", async () => {
    api.listPageEngines.mockResolvedValue(ENGINES);
    api.runPageEngine.mockResolvedValue({ version: { version_id: 77, version_number: 3 }, forked: true, engine: "gemini", text: "字" });
    const onRan = vi.fn();
    render(<PageEnginesPanel scanId={20} pageNumber={3} versionId={5} onRan={onRan} />);
    await screen.findByText("PaddleOCR v6 ✓");
    fireEvent.click(screen.getAllByRole("button", { name: "Chạy" })[0]);
    expect(api.runPageEngine).not.toHaveBeenCalled(); // chưa xác nhận thì chưa gọi (tốn tiền)
    fireEvent.click(await screen.findByRole("button", { name: /Chạy \(tốn tiền\)/ }));
    await waitFor(() => expect(api.runPageEngine).toHaveBeenCalledWith(20, 3, "gemini", { versionId: 5 }));
    await waitFor(() => expect(onRan).toHaveBeenCalledTimes(1));
  });

  it("shows the API error and keeps the list", async () => {
    api.listPageEngines.mockResolvedValue(ENGINES);
    api.runPageEngine.mockRejectedValue(new Error("Gemini Vision không trả về chữ"));
    render(<PageEnginesPanel scanId={20} pageNumber={3} onRan={() => {}} />);
    await screen.findByText("PaddleOCR v6 ✓");
    fireEvent.click(screen.getAllByRole("button", { name: "Chạy" })[0]);
    fireEvent.click(await screen.findByRole("button", { name: /Chạy \(tốn tiền\)/ }));
    expect(await screen.findByText("Gemini Vision không trả về chữ")).toBeInTheDocument();
    expect(screen.getByText("PaddleOCR v6 ✓")).toBeInTheDocument();
  });
});
