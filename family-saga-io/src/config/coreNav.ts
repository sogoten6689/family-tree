/**
 * Lõi menu dùng chung cho Guest/User/Admin (đã chốt: menu 3 vai trò phải
 * giống nhau, Admin/User chỉ thêm mục chứ không đổi lõi). RoleLayout map
 * key -> path theo vai trò và tự tra icon (giữ đúng quy ước icon-map của
 * developerRoutes.ts — config không chứa JSX).
 */
import { getDeveloperNavItem } from "@/config/developerRoutes";

export type CoreNavKey = "upload" | "gia-pha" | "genealogy" | "guide";

export interface CoreNavItem {
  key: CoreNavKey;
  labelKey: string;
  labelDefault: string;
}

export const CORE_NAV_ITEMS: CoreNavItem[] = [
  { key: "upload", labelKey: "flow.menu.uploadAnalyze", labelDefault: "Tải lên & Phân tích" },
  { key: "gia-pha", labelKey: "coreNav.giaPha", labelDefault: "Gia phả" },
  { key: "genealogy", labelKey: "coreNav.genealogy", labelDefault: "Trích xuất gia phả" },
  { key: "guide", labelKey: "nav.guide", labelDefault: "Hướng dẫn" },
];

export type NavRole = "guest" | "user" | "admin";

/** Path của từng mục lõi theo vai trò. Layout là RoleLayout (menu theo vai
 * trò, không theo URL), nên trang dùng chung như /huong-dan hay tải lên vẫn
 * giữ đúng menu của người đang đăng nhập. */
export const CORE_NAV_PATHS: Record<NavRole, Record<CoreNavKey, string>> = {
  guest: { upload: "/", "gia-pha": "/gia-pha", genealogy: "/genealogy-extractor", guide: "/huong-dan" },
  user: { upload: "/user/document-reader", "gia-pha": "/user/gia-pha", genealogy: "/genealogy-extractor", guide: "/huong-dan" },
  admin: { upload: "/user/document-reader", "gia-pha": "/admin/gia-pha", genealogy: "/genealogy-extractor", guide: "/huong-dan" },
};

export function isCoreNavKey(key: string): key is CoreNavKey {
  return CORE_NAV_ITEMS.some((item) => item.key === key);
}

/** Trang chủ theo vai trò — "Trang chủ"/"/" không được đưa người đã đăng
 * nhập về giao diện Guest, cũng không đưa Admin về dashboard của User. */
export function roleHomePath(role: NavRole): string {
  if (role === "admin") return "/admin/dashboard";
  if (role === "user") return "/user/dashboard";
  return "/";
}

/** Mục menu đang chọn — suy từ URL, nhưng KHÔNG quyết định menu nào hiện
 * (menu do vai trò quyết định). Các trang dùng chung giữa vai trò (tải lên,
 * hướng dẫn, chi tiết bộ gia phả) map về cùng 1 key lõi. */
export function resolveMenuKey(pathname: string): string {
  const devItem = getDeveloperNavItem(pathname);
  if (devItem) return devItem.key;
  if (pathname === "/" || pathname.startsWith("/user/documents/new") || pathname.startsWith("/user/document-reader")) {
    return "upload";
  }
  if (
    pathname.startsWith("/gia-pha") ||
    pathname.startsWith("/user/gia-pha") ||
    pathname.startsWith("/admin/gia-pha") ||
    pathname.startsWith("/user/documents") ||
    pathname.startsWith("/admin/documents")
  ) {
    return "gia-pha";
  }
  if (pathname.startsWith("/huong-dan") || pathname.startsWith("/user/huong-dan")) return "guide";
  if (pathname.startsWith("/genealogy-extractor")) return "genealogy";
  if (pathname.startsWith("/user/profile")) return "profile";
  if (pathname.startsWith("/admin/history")) return "history";
  if (pathname.startsWith("/admin/users")) return "users";
  return "dashboard";
}
