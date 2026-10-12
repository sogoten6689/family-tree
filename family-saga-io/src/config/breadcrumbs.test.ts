import { describe, expect, it } from "vitest";

import { buildBreadcrumb } from "@/config/breadcrumbs";

const tr = (_key: string, defaultValue: string) => defaultValue;
const labels = (pathname: string, role: "guest" | "user" | "admin" = "admin", search = "") =>
  buildBreadcrumb(pathname, search, role, tr).map((c) => c.label);

describe("buildBreadcrumb: Trang chủ › Menu › Chi tiết › Mục con", () => {
  it("dashboard is just 'Trang chủ' (no duplicate 'Tổng quan')", () => {
    expect(labels("/admin/dashboard")).toEqual(["Trang chủ"]);
    expect(labels("/user/dashboard", "user")).toEqual(["Trang chủ"]);
  });

  it("menu list page: Trang chủ › Gia phả, with the last item as plain text", () => {
    const crumbs = buildBreadcrumb("/admin/gia-pha", "", "admin", tr);
    expect(crumbs.map((c) => c.label)).toEqual(["Trang chủ", "Gia phả"]);
    expect(crumbs[0].to).toBe("/admin/dashboard");
    expect(crumbs[1].to).toBeUndefined();
  });

  it("tree detail: Trang chủ › Gia phả › Chi tiết, and 'Gia phả' links back to the role's list", () => {
    const crumbs = buildBreadcrumb("/admin/gia-pha/tree-1", "", "admin", tr);
    expect(crumbs.map((c) => c.label)).toEqual(["Trang chủ", "Gia phả", "Chi tiết"]);
    expect(crumbs[1].to).toBe("/admin/gia-pha");
    expect(buildBreadcrumb("/user/gia-pha/t", "", "user", tr)[1].to).toBe("/user/gia-pha");
    expect(buildBreadcrumb("/gia-pha/t", "", "guest", tr)[0].to).toBe("/");
  });

  it("document detail with sub-tab: Trang chủ › Gia phả › Tài liệu #id › Trang", () => {
    expect(labels("/user/documents/22", "user", "?tab=pages")).toEqual(["Trang chủ", "Gia phả", "Tài liệu #22", "Trang"]);
    expect(labels("/user/documents/22", "user", "?tab=ocr")).toEqual(["Trang chủ", "Gia phả", "Tài liệu #22", "Trang"]);
    expect(labels("/user/documents/22", "user", "?tab=versions")).toEqual(["Trang chủ", "Gia phả", "Tài liệu #22", "Phiên bản & nhập LLM"]);
    const crumbs = buildBreadcrumb("/user/documents/22", "?tab=pages", "user", tr);
    expect(crumbs[2].to).toBe("/user/documents/22"); // quay lại tab tổng quan
    expect(crumbs[3].to).toBeUndefined();
  });

  it("document detail on the default tab has no sub item; /documents/new is the upload menu page", () => {
    expect(labels("/user/documents/22", "user")).toEqual(["Trang chủ", "Gia phả", "Tài liệu #22"]);
    expect(labels("/user/documents/new", "user")).toEqual(["Trang chủ", "Tải lên & Phân tích"]);
  });

  it("admin document edit: …› Tài liệu #id › Chỉnh sửa", () => {
    expect(labels("/admin/documents/5/edit")).toEqual(["Trang chủ", "Gia phả", "Tài liệu #5", "Chỉnh sửa"]);
  });

  it("developer tools: Trang chủ › Công cụ nghiên cứu › page", () => {
    expect(labels("/admin/developer/storage")).toEqual(["Trang chủ", "Công cụ nghiên cứu", "Lưu trữ"]);
  });

  it("single pages and shared pages", () => {
    expect(labels("/user/profile", "user")).toEqual(["Trang chủ", "Tài khoản"]);
    expect(labels("/admin/history")).toEqual(["Trang chủ", "Lịch sử"]);
    expect(labels("/admin/users")).toEqual(["Trang chủ", "Thành viên"]);
    expect(labels("/huong-dan", "guest")).toEqual(["Trang chủ", "Hướng dẫn"]);
    expect(labels("/genealogy-extractor", "guest")).toEqual(["Trang chủ", "Trích xuất gia phả"]);
  });
});
