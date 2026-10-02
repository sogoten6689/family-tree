import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";

import { canDisable, type OcrEngineConfig } from "@/lib/settingsApi";

const api = vi.hoisted(() => ({ getOcrEngines: vi.fn(), updateOcrEngines: vi.fn() }));
vi.mock("@/lib/settingsApi", async (importOriginal) => ({
  ...(await importOriginal<typeof import("@/lib/settingsApi")>()),
  getOcrEngines: api.getOcrEngines,
  updateOcrEngines: api.updateOcrEngines,
}));

const { OcrEnginesCard } = await import("./OcrEnginesCard");

const cfg = (enabled: Record<string, boolean>): OcrEngineConfig => ({
  min_enabled: 1,
  engines: Object.entries(enabled).map(([name, on]) => ({
    name,
    label: name,
    enabled: on,
    ready: true,
    ready_reason: null,
  })),
});

describe("canDisable", () => {
  it("blocks turning off the last enabled engine", () => {
    expect(canDisable(cfg({ kimhannom: true, gemini_vision: false }), "kimhannom")).toBe(false);
  });
  it("allows turning off when another engine stays on", () => {
    expect(canDisable(cfg({ kimhannom: true, gemini_vision: true }), "kimhannom")).toBe(true);
  });
  it("always allows a disabled engine (it can be turned on)", () => {
    expect(canDisable(cfg({ kimhannom: true, gemini_vision: false }), "gemini_vision")).toBe(true);
  });
});

describe("OcrEnginesCard", { timeout: 15000 }, () => {
  beforeEach(() => {
    api.getOcrEngines.mockReset();
    api.updateOcrEngines.mockReset();
  });

  it("locks the switch of the only enabled engine", async () => {
    api.getOcrEngines.mockResolvedValue(cfg({ kimhannom: true, gemini_vision: false }));
    render(<OcrEnginesCard />);
    const kim = await screen.findByRole("switch", { name: "Bật/tắt kimhannom" });
    expect(kim).toBeDisabled();
    expect(screen.getByRole("switch", { name: "Bật/tắt gemini_vision" })).not.toBeDisabled();
  });

  it("sends the remaining enabled list when an engine is turned off", async () => {
    api.getOcrEngines.mockResolvedValue(cfg({ kimhannom: true, gemini_vision: true }));
    api.updateOcrEngines.mockResolvedValue(cfg({ kimhannom: true, gemini_vision: false }));
    const onSaved = vi.fn();
    render(<OcrEnginesCard onSaved={onSaved} />);
    fireEvent.click(await screen.findByRole("switch", { name: "Bật/tắt gemini_vision" }));
    await waitFor(() => expect(api.updateOcrEngines).toHaveBeenCalledWith(["kimhannom"]));
    await waitFor(() => expect(onSaved).toHaveBeenCalled());
    expect(await screen.findByRole("switch", { name: "Bật/tắt kimhannom" })).toBeDisabled();
  });
});
