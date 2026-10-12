/**
 * Breadcrumb theo cấu trúc: Trang chủ › Menu › Chi tiết › Mục con.
 * Hàm thuần (không React) để kiểm thử theo từng URL. Mỗi mục có `to` (đi tới được) trừ mục cuối
 * (trang đang xem). Nhãn do `label()` quyết định để layout truyền hàm dịch i18n vào.
 */
import { CORE_NAV_ITEMS, CORE_NAV_PATHS, resolveMenuKey, roleHomePath, type NavRole } from "@/config/coreNav";
import { getDeveloperNavItem } from "@/config/developerRoutes";

export interface Crumb {
  label: string;
  /** Có `to` = bấm để quay lại; mục cuối (trang hiện tại) không có. */
  to?: string;
}

export type Translate = (key: string, defaultValue: string) => string;

/** Tab của trang chi tiết tài liệu → nhãn mục con (tab mặc định "overview" không thêm mục con). */
const DOCUMENT_TAB_LABELS: Record<string, { key: string; label: string }> = {
  extract: { key: "flow.step.extract", label: "Trích xuất" },
  pages: { key: "pageViewer.tab", label: "Trang" },
  ocr: { key: "pageViewer.tab", label: "Trang" }, // link cũ ?tab=ocr mở tab Trang
  versions: { key: "llmImport.tab", label: "Phiên bản & nhập LLM" },
};

const SINGLE_PAGE_MENUS: Record<string, { key: string; label: string }> = {
  profile: { key: "profile.title", label: "Tài khoản" },
  history: { key: "adminHistory.title", label: "Lịch sử" },
  users: { key: "admin.menuUsers", label: "Thành viên" },
};

export function buildBreadcrumb(pathname: string, search: string, role: NavRole, tr: Translate): Crumb[] {
  const home: Crumb = { label: tr("common.backHome", "Trang chủ"), to: roleHomePath(role) };
  const menuKey = resolveMenuKey(pathname);

  // Công cụ nghiên cứu (Admin): Trang chủ › Công cụ nghiên cứu › Hán-Nôm / Cấu hình / …
  const dev = getDeveloperNavItem(pathname);
  if (dev) {
    return [
      home,
      { label: tr("admin.developer.menu", "Công cụ nghiên cứu"), to: dev.path },
      { label: tr(dev.breadcrumbKey, dev.breadcrumbDefault) },
    ];
  }

  // Trang tổng quan: chính là "Trang chủ", không lặp thêm "Tổng quan".
  if (menuKey === "dashboard") return [{ label: home.label }];

  const single = SINGLE_PAGE_MENUS[menuKey];
  if (single) return [home, { label: tr(single.key, single.label) }];

  const core = CORE_NAV_ITEMS.find((item) => item.key === menuKey);
  if (!core) return [home];
  const menuPath = CORE_NAV_PATHS[role][core.key];
  const menu: Crumb = { label: tr(core.labelKey, core.labelDefault), to: menuPath };

  const crumbs = (...rest: Crumb[]): Crumb[] => {
    const all = [home, menu, ...rest];
    // Mục cuối là trang đang xem: bỏ liên kết.
    return all.map((c, i) => (i === all.length - 1 ? { label: c.label } : c));
  };

  // Chi tiết một bộ gia phả (cây): …/gia-pha/:treeId
  if (/^\/(?:user\/|admin\/)?gia-pha\/[^/]+$/.test(pathname)) {
    return crumbs({ label: tr("breadcrumb.detail", "Chi tiết") });
  }

  // Chi tiết một tài liệu: /user/documents/:scanId[?tab=…] (không phải trang tải lên /documents/new)
  const doc = pathname.match(/^\/user\/documents\/([^/]+)$/);
  if (doc && doc[1] !== "new") {
    const detail: Crumb = { label: `${tr("breadcrumb.document", "Tài liệu")} #${doc[1]}`, to: `/user/documents/${doc[1]}` };
    const tab = DOCUMENT_TAB_LABELS[new URLSearchParams(search).get("tab") ?? ""];
    return crumbs(detail, ...(tab ? [{ label: tr(tab.key, tab.label) }] : []));
  }

  // Sửa tài liệu (Admin): /admin/documents/:id/edit
  const edit = pathname.match(/^\/admin\/documents\/([^/]+)\/edit$/);
  if (edit) {
    return crumbs({ label: `${tr("breadcrumb.document", "Tài liệu")} #${edit[1]}`, to: `/user/documents/${edit[1]}` }, { label: tr("breadcrumb.edit", "Chỉnh sửa") });
  }

  // Trang chính của một mục menu (danh sách, hướng dẫn, tải lên, trích xuất…).
  return crumbs();
}
