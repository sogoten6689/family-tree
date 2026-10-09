import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import { afterEach, describe, expect, it, vi } from "vitest";

import "@/i18n";
import AppShell from "./AppShell";

// jsdom không có ResizeObserver (antd Drawer/Menu cần).
if (typeof globalThis.ResizeObserver === "undefined") {
  globalThis.ResizeObserver = class {
    observe() {}
    unobserve() {}
    disconnect() {}
  } as unknown as typeof ResizeObserver;
}

const setNarrowScreen = (narrow: boolean) => {
  Object.defineProperty(window, "matchMedia", {
    writable: true,
    value: (query: string) => ({
      matches: narrow && query.includes("max-width"),
      media: query,
      onchange: null,
      addListener: () => {},
      removeListener: () => {},
      addEventListener: () => {},
      removeEventListener: () => {},
      dispatchEvent: () => false,
    }),
  });
};

const renderShell = (onMenuClick = vi.fn()) => {
  render(
    <MemoryRouter>
      <AppShell
        panelTitle="Quản trị"
        menuItems={[
          { key: "a", label: "Mục A" },
          { key: "b", label: "Mục B" },
        ]}
        selectedKeys={["a"]}
        onMenuClick={onMenuClick}
        accountSlot={<button type="button">Đăng xuất</button>}
        breadcrumbItems={[{ title: "Trang chủ" }, { title: "Tổng quan" }]}
        pageTitle="Tổng quan"
        headerExtra={<span>admin · quản trị</span>}
      />
    </MemoryRouter>,
  );
  return onMenuClick;
};

describe("AppShell responsive", { timeout: 15000 }, () => {
  afterEach(() => setNarrowScreen(false)); // trả về mặc định (máy tính) cho các test khác

  it("desktop: fixed sidebar with the menu, breadcrumb and header extras visible", () => {
    setNarrowScreen(false);
    renderShell();
    expect(screen.getByText("Mục A")).toBeInTheDocument();
    expect(screen.getByText("Đăng xuất")).toBeInTheDocument();
    expect(screen.getByText("Trang chủ")).toBeInTheDocument(); // breadcrumb
    expect(screen.getByText("admin · quản trị")).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Thu gọn menu" })).toBeInTheDocument();
  });

  it("mobile: no fixed sidebar, compact header (no breadcrumb / header extras)", () => {
    setNarrowScreen(true);
    renderShell();
    expect(screen.queryByText("Mục A")).toBeNull(); // menu nằm trong ngăn kéo, chưa mở
    expect(screen.queryByText("Trang chủ")).toBeNull();
    expect(screen.queryByText("admin · quản trị")).toBeNull();
    expect(screen.getByText("Tổng quan")).toBeInTheDocument(); // vẫn có tiêu đề trang
    expect(screen.getByRole("button", { name: "Mở menu" })).toBeInTheDocument();
  });

  it("mobile: the menu button opens a drawer with the menu and account slot; picking an item closes it", async () => {
    setNarrowScreen(true);
    const onMenuClick = renderShell();
    fireEvent.click(screen.getByRole("button", { name: "Mở menu" }));
    expect(await screen.findByText("Mục A")).toBeInTheDocument();
    expect(screen.getByText("Đăng xuất")).toBeInTheDocument();
    expect(document.querySelector(".ant-drawer-open")).not.toBeNull();
    fireEvent.click(screen.getByText("Mục B"));
    expect(onMenuClick).toHaveBeenCalledTimes(1);
    expect(onMenuClick.mock.calls[0][0].key).toBe("b");
    // chọn mục xong thì đóng ngăn kéo (antd bỏ lớp ant-drawer-open ngay, phần trượt ra là animation)
    await waitFor(() => expect(document.querySelector(".ant-drawer-open")).toBeNull());
  });
});
