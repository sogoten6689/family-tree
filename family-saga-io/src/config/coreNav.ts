/**
 * Lõi menu dùng chung cho Guest/User/Admin (đã chốt: menu 3 vai trò phải
 * giống nhau, Admin/User chỉ thêm mục chứ không đổi lõi). Mỗi layout tự map
 * key -> path theo đúng prefix của mình và tự tra icon (giữ đúng quy ước
 * icon-map của developerRoutes.ts — config không chứa JSX).
 */
export type CoreNavKey = "upload" | "gia-pha" | "guide";

export interface CoreNavItem {
  key: CoreNavKey;
  labelKey: string;
  labelDefault: string;
}

export const CORE_NAV_ITEMS: CoreNavItem[] = [
  { key: "upload", labelKey: "flow.menu.uploadAnalyze", labelDefault: "Tải lên & Phân tích" },
  { key: "gia-pha", labelKey: "coreNav.giaPha", labelDefault: "Gia phả" },
  { key: "guide", labelKey: "nav.guide", labelDefault: "Hướng dẫn" },
];

/** Path của từng mục lõi theo vai trò. Admin dùng chung route tải lên/hướng
 * dẫn với User (không có bản sao dưới /admin). */
export const CORE_NAV_PATHS: Record<"guest" | "user" | "admin", Record<CoreNavKey, string>> = {
  guest: { upload: "/", "gia-pha": "/gia-pha", guide: "/huong-dan" },
  user: { upload: "/user/document-reader", "gia-pha": "/user/gia-pha", guide: "/user/huong-dan" },
  admin: { upload: "/user/document-reader", "gia-pha": "/admin/gia-pha", guide: "/user/huong-dan" },
};

export function isCoreNavKey(key: string): key is CoreNavKey {
  return CORE_NAV_ITEMS.some((item) => item.key === key);
}
