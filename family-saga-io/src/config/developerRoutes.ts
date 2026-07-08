export const DEVELOPER_BASE = "/admin/developer";

export const DEVELOPER_ROUTES = {
  hannomConfig: `${DEVELOPER_BASE}/hannom-config`,
  storage: `${DEVELOPER_BASE}/storage`,
  logs: `${DEVELOPER_BASE}/logs`,
  docs: `${DEVELOPER_BASE}/docs`,
} as const;

export type DeveloperRouteKey = keyof typeof DEVELOPER_ROUTES;

export interface DeveloperNavItem {
  key: string;
  path: string;
  labelKey: string;
  labelDefault: string;
  breadcrumbKey: string;
  breadcrumbDefault: string;
}

export const DEVELOPER_NAV_ITEMS: DeveloperNavItem[] = [
  {
    key: "developer-hannom",
    path: DEVELOPER_ROUTES.hannomConfig,
    labelKey: "admin.developer.menuHannom",
    labelDefault: "Cấu hình API Kim Hán Nôm",
    breadcrumbKey: "admin.developer.breadcrumbHannom",
    breadcrumbDefault: "API Config",
  },
  {
    key: "developer-storage",
    path: DEVELOPER_ROUTES.storage,
    labelKey: "admin.developer.menuStorage",
    labelDefault: "Lưu trữ MinIO/S3",
    breadcrumbKey: "admin.developer.breadcrumbStorage",
    breadcrumbDefault: "Storage",
  },
  {
    key: "developer-logs",
    path: DEVELOPER_ROUTES.logs,
    labelKey: "admin.developer.menuLogs",
    labelDefault: "Log & Monitoring",
    breadcrumbKey: "admin.developer.breadcrumbLogs",
    breadcrumbDefault: "Logs",
  },
  {
    key: "developer-docs",
    path: DEVELOPER_ROUTES.docs,
    labelKey: "admin.developer.menuDocs",
    labelDefault: "Tài liệu & CURL mẫu",
    breadcrumbKey: "admin.developer.breadcrumbDocs",
    breadcrumbDefault: "Docs",
  },
];

export function isDeveloperPath(pathname: string): boolean {
  return pathname.startsWith(DEVELOPER_BASE);
}

export function getDeveloperNavItem(pathname: string): DeveloperNavItem | undefined {
  return DEVELOPER_NAV_ITEMS.find(
    (item) => pathname === item.path || pathname.startsWith(`${item.path}/`),
  );
}

export function getAdminMenuSelectedKey(pathname: string): string {
  if (pathname.startsWith("/admin/dashboard")) return "dashboard";
  if (pathname.startsWith("/admin/history")) return "history";
  if (pathname.startsWith("/admin/users")) return "users";
  const devItem = getDeveloperNavItem(pathname);
  if (devItem) return devItem.key;
  if (pathname.startsWith("/admin/gia-pha") || pathname.startsWith("/admin/documents")) {
    return "gia-pha";
  }
  return "dashboard";
}
