import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";

import "@/i18n";
import type { UserScan } from "@/lib/userWorkspaceApi";

const api = vi.hoisted(() => ({ autoMaDinhDanh: vi.fn() }));
vi.mock("@/lib/userWorkspaceApi", async (importOriginal) => ({
  ...(await importOriginal<typeof import("@/lib/userWorkspaceApi")>()),
  ...api,
}));

const { MaDinhDanhField } = await import("./MaDinhDanhField");

const scan = (over: Partial<UserScan>): UserScan => ({
  id: 3,
  title: "GP",
  file_name: "a",
  file_type: "pdf",
  page_count: 1,
  uploaded_at: "2026-10-02T00:00:00Z",
  ocr_status: "completed",
  tree_status: "none",
  source_text: "bản dịch",
  ...over,
});

describe("MaDinhDanhField", { timeout: 15000 }, () => {
  beforeEach(() => api.autoMaDinhDanh.mockReset());

  it("shows a confirmed code with its source and no generate button", () => {
    render(<MaDinhDanhField scan={scan({ ma_dinh_danh: "F-B-PN-GiaThien-001-1930", ma_dinh_danh_nguon: "catalogue" })} onChanged={() => {}} />);
    expect(screen.getByText("F-B-PN-GiaThien-001-1930")).toBeInTheDocument();
    expect(screen.getByText("Đã chốt")).toBeInTheDocument();
    expect(screen.queryByRole("button", { name: /Tạo mã tự động/ })).toBeNull();
  });

  it("marks Gemini-generated codes", () => {
    render(<MaDinhDanhField scan={scan({ ma_dinh_danh: "F-B-NG-BoiKhe-009-1496", ma_dinh_danh_nguon: "gemini" })} onChanged={() => {}} />);
    expect(screen.getByText("Tự tạo (Gemini)")).toBeInTheDocument();
  });

  it("generates a code and refreshes on success", async () => {
    api.autoMaDinhDanh.mockResolvedValue({ ma_dinh_danh: "F-B-NG-BoiKhe-009-1496", ma_dinh_danh_nguon: "gemini", problems: [] });
    const onChanged = vi.fn();
    render(<MaDinhDanhField scan={scan({})} onChanged={onChanged} />);
    fireEvent.click(screen.getByRole("button", { name: /Tạo mã tự động/ }));
    await waitFor(() => expect(onChanged).toHaveBeenCalled());
    expect(api.autoMaDinhDanh).toHaveBeenCalledWith(3);
  });

  it("shows the reasons when no code could be generated", async () => {
    api.autoMaDinhDanh.mockResolvedValue({ ma_dinh_danh: null, ma_dinh_danh_nguon: null, problems: ["ho None không hợp lệ"] });
    const onChanged = vi.fn();
    render(<MaDinhDanhField scan={scan({})} onChanged={onChanged} />);
    fireEvent.click(screen.getByRole("button", { name: /Tạo mã tự động/ }));
    await screen.findByText("ho None không hợp lệ");
    expect(onChanged).not.toHaveBeenCalled();
  });

  it("disables generation without any text", () => {
    render(<MaDinhDanhField scan={scan({ source_text: null, transliteration_text: null })} onChanged={() => {}} />);
    expect(screen.getByRole("button", { name: /Tạo mã tự động/ })).toBeDisabled();
  });
});
