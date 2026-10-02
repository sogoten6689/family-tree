import { fireEvent, render, screen } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import { describe, expect, it, vi } from "vitest";

import "@/i18n";

vi.mock("@/lib/giaPhaApi", () => ({
  listGiaPha: vi.fn().mockResolvedValue({
    total: 2,
    items: [
      { id: "F-B-PN-GiaThien-001-1930", ma_dinh_danh_pending: false, title: "Phan gia công phả", ho_toc: "Phan", status: "built", updated_at: "2026-10-02" },
      { id: "nom-147", ma_dinh_danh_pending: true, title: "Nguyễn tộc phả", ho_toc: "Nguyễn", status: "pending", updated_at: "2026-10-02" },
    ],
  }),
}));

if (typeof globalThis.ResizeObserver === "undefined") {
  globalThis.ResizeObserver = class {
    observe() {}
    unobserve() {}
    disconnect() {}
  } as unknown as typeof ResizeObserver;
}

const { default: GiaPhaListPage } = await import("./GiaPhaListPage");

const renderAt = (path: string) =>
  render(
    <MemoryRouter initialEntries={[path]}>
      <GiaPhaListPage scope="admin" />
    </MemoryRouter>,
  );

describe("GiaPhaListPage search", { timeout: 15000 }, () => {
  it("filters rows as you type (diacritic-insensitive) and shows the count", async () => {
    renderAt("/admin/gia-pha");
    await screen.findByText("Phan gia công phả");
    fireEvent.change(screen.getByRole("searchbox", { name: "Tìm kiếm gia phả" }), { target: { value: "nguyen" } });
    expect(screen.queryByText("Phan gia công phả")).toBeNull();
    expect(screen.getByText("Nguyễn tộc phả")).toBeInTheDocument();
    expect(screen.getByText("1/2 bộ")).toBeInTheDocument();
  });

  it("reads the query from the URL", async () => {
    renderAt("/admin/gia-pha?q=phan");
    await screen.findByText("Phan gia công phả");
    expect(screen.queryByText("Nguyễn tộc phả")).toBeNull();
  });

  it("shows a no-match message instead of the empty-list message", async () => {
    renderAt("/admin/gia-pha?q=zzz");
    expect(await screen.findByText("Không có bộ nào khớp tìm kiếm/bộ lọc")).toBeInTheDocument();
  });
});
