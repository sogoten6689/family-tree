import { render, screen } from "@testing-library/react";
import { MemoryRouter, Route, Routes } from "react-router-dom";
import { afterEach, describe, expect, it, vi } from "vitest";

import "@/i18n";
import { ResearchGate } from "@/components/ResearchGate";
import { roleHomePath } from "@/config/coreNav";
import { RESEARCH_HOME, isResearchPath, researchMode } from "@/config/researchMode";

type FakeAuth = { user: null; isAuthenticated: boolean; isAdmin: boolean; isLoading: boolean; logout: () => void };
let auth: FakeAuth = { user: null, isAuthenticated: false, isAdmin: false, isLoading: false, logout: () => {} };
vi.mock("@/contexts/AuthContext", () => ({ useAuth: () => auth }));

const { default: RoleLayout } = await import("@/layouts/RoleLayout");

afterEach(() => {
  vi.unstubAllEnvs();
  auth = { ...auth, isAuthenticated: false, isAdmin: false };
});

const renderGate = (path: string) =>
  render(
    <MemoryRouter initialEntries={[path]}>
      <ResearchGate>
        <Routes>
          <Route path={RESEARCH_HOME} element={<div>trang đối chiếu</div>} />
          <Route path="*" element={<div>trang khác</div>} />
        </Routes>
      </ResearchGate>
    </MemoryRouter>,
  );

describe("chế độ nghiên cứu", { timeout: 15000 }, () => {
  it("mặc định tắt, mọi trang mở như trước", () => {
    expect(researchMode()).toBe(false);
    renderGate("/admin/users");
    expect(screen.getByText("trang khác")).toBeInTheDocument();
  });

  it.each(["/", "/register", "/huong-dan", "/genealogy-extractor", "/user/profile", "/admin/users", "/gia-pha-x"])(
    "đóng %s, chuyển về trang đối chiếu",
    (path) => {
      vi.stubEnv("VITE_RESEARCH_MODE", "1");
      renderGate(path);
      expect(screen.getByText("trang đối chiếu")).toBeInTheDocument();
    },
  );

  it.each(["/login", "/gia-pha", "/gia-pha/abc", "/nghien-cuu/tien-do", "/nghien-cuu/quan-ly/"])("giữ %s", (path) => {
    expect(isResearchPath(path)).toBe(true);
  });

  it("trang chủ của mọi vai trò là trang đối chiếu", () => {
    vi.stubEnv("VITE_RESEARCH_MODE", "1");
    expect([roleHomePath("guest"), roleHomePath("user"), roleHomePath("admin")]).toEqual(Array(3).fill(RESEARCH_HOME));
  });

  it.each([false, true])("menu chỉ còn phần nghiên cứu (đã đăng nhập: %s)", (loggedIn) => {
    vi.stubEnv("VITE_RESEARCH_MODE", "1");
    auth = { ...auth, isAuthenticated: loggedIn, isAdmin: loggedIn };
    render(
      <MemoryRouter initialEntries={[RESEARCH_HOME]}>
        <Routes>
          <Route element={<RoleLayout />}>
            <Route path="*" element={<div>page</div>} />
          </Route>
        </Routes>
      </MemoryRouter>,
    );
    const labels = Array.from(document.querySelectorAll(".ant-menu-item, .ant-menu-submenu-title")).map((e) => e.textContent);
    expect(labels).toEqual([
      "OCR · Dịch · Dóng",
      "Đối chiếu & soát",
      "Tiến độ",
      "Thông tin nghiên cứu",
      "Quản lý nghiên cứu",
      "Ôn tập bảo vệ",
    ]);
    expect(screen.queryByText("Đăng nhập")).toBeNull();
    expect(screen.queryByText("Đăng ký")).toBeNull();
    expect(screen.queryByText("Đăng xuất") !== null).toBe(loggedIn);
  });
});
