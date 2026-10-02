import { render, screen } from "@testing-library/react";
import { MemoryRouter, Route, Routes } from "react-router-dom";
import { beforeEach, describe, expect, it, vi } from "vitest";

import "@/i18n";
import { resolveMenuKey, roleHomePath } from "@/config/coreNav";

type FakeAuth = {
  user: { full_name: string; role: string } | null;
  isAuthenticated: boolean;
  isAdmin: boolean;
  isLoading: boolean;
  logout: () => void;
};

let auth: FakeAuth;
vi.mock("@/contexts/AuthContext", () => ({ useAuth: () => auth }));

const { default: RoleLayout } = await import("./RoleLayout");

const asGuest = (): FakeAuth => ({ user: null, isAuthenticated: false, isAdmin: false, isLoading: false, logout: () => {} });
const asUser = (): FakeAuth => ({
  user: { full_name: "User A", role: "user" },
  isAuthenticated: true,
  isAdmin: false,
  isLoading: false,
  logout: () => {},
});
const asAdmin = (): FakeAuth => ({
  user: { full_name: "Admin", role: "admin" },
  isAuthenticated: true,
  isAdmin: true,
  isLoading: false,
  logout: () => {},
});

function renderAt(path: string) {
  return render(
    <MemoryRouter initialEntries={[path]}>
      <Routes>
        <Route element={<RoleLayout />}>
          <Route path="*" element={<div>page</div>} />
        </Route>
      </Routes>
    </MemoryRouter>,
  );
}

const menuLabels = () => Array.from(document.querySelectorAll(".ant-menu-item, .ant-menu-submenu-title")).map((e) => e.textContent);

// Render antd Menu/Sider thật trong jsdom: đo 2–4,4s/test khi máy tải cao
// (load avg 128–382, 2026-10-02) — vượt mặc định 5s gây flaky, không phải lỗi.
describe("RoleLayout — menu theo vai trò, không theo URL", { timeout: 15000 }, () => {
  beforeEach(() => {
    auth = asGuest();
  });

  // Các tình huống lỗi trong bảng thiết kế: Admin vào trang /user/* hoặc trang
  // công khai từng bị mất menu Admin.
  it.each(["/user/document-reader", "/user/documents/12", "/user/profile", "/huong-dan", "/gia-pha"])(
    "admin at %s keeps admin menu and no guest login buttons",
    (path) => {
      auth = asAdmin();
      renderAt(path);
      expect(menuLabels()).toEqual(
        expect.arrayContaining(["Tải lên & Phân tích", "Gia phả", "Hướng dẫn", "Lịch sử", "Thành viên"]),
      );
      expect(screen.queryByText("Đăng nhập")).toBeNull();
      expect(screen.getByText("Đăng xuất")).toBeInTheDocument();
    },
  );

  it.each(["/huong-dan", "/gia-pha", "/gia-pha/abc"])("user at public %s keeps user menu", (path) => {
    auth = asUser();
    renderAt(path);
    expect(menuLabels()).toEqual(expect.arrayContaining(["Tổng quan", "Tài khoản"]));
    expect(menuLabels()).not.toContain("Thành viên");
    expect(screen.queryByText("Đăng nhập")).toBeNull();
  });

  it("guest sees only the core menu plus login/register", () => {
    renderAt("/gia-pha");
    expect(menuLabels()).toEqual(["Tải lên & Phân tích", "Gia phả", "Hướng dẫn"]);
    expect(screen.getByText("Đăng nhập")).toBeInTheDocument();
  });

  it("shows a spinner instead of a guest menu while auth is loading", () => {
    auth = { ...asAdmin(), isLoading: true };
    renderAt("/admin/dashboard");
    expect(menuLabels()).toEqual([]);
  });
});

describe("roleHomePath / resolveMenuKey", () => {
  it("sends each role to its own home", () => {
    expect(roleHomePath("admin")).toBe("/admin/dashboard");
    expect(roleHomePath("user")).toBe("/user/dashboard");
    expect(roleHomePath("guest")).toBe("/");
  });

  it.each([
    ["/", "upload"],
    ["/user/documents/new", "upload"],
    ["/user/documents/5", "gia-pha"],
    ["/admin/gia-pha/x", "gia-pha"],
    ["/huong-dan", "guide"],
    ["/admin/users", "users"],
    ["/admin/developer/settings", "developer-settings"],
  ])("%s -> %s", (path, key) => {
    expect(resolveMenuKey(path)).toBe(key);
  });
});
