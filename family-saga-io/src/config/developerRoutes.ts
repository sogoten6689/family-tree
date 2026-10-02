export const DEVELOPER_BASE = "/admin/developer";

export const DEVELOPER_ROUTES = {
  hannomConfig: `${DEVELOPER_BASE}/hannom-config`,
  settings: `${DEVELOPER_BASE}/settings`,
  storage: `${DEVELOPER_BASE}/storage`,
  logs: `${DEVELOPER_BASE}/logs`,
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
    labelDefault: "Hán-Nôm",
    breadcrumbKey: "admin.developer.breadcrumbHannom",
    breadcrumbDefault: "Hán-Nôm",
  },
  {
    key: "developer-settings",
    path: DEVELOPER_ROUTES.settings,
    labelKey: "admin.developer.menuSettings",
    labelDefault: "Cấu hình",
    breadcrumbKey: "admin.developer.breadcrumbSettings",
    breadcrumbDefault: "Cấu hình",
  },
  {
    key: "developer-storage",
    path: DEVELOPER_ROUTES.storage,
    labelKey: "admin.developer.menuStorage",
    labelDefault: "Lưu trữ",
    breadcrumbKey: "admin.developer.breadcrumbStorage",
    breadcrumbDefault: "Lưu trữ",
  },
  {
    key: "developer-logs",
    path: DEVELOPER_ROUTES.logs,
    labelKey: "admin.developer.menuLogs",
    labelDefault: "Nhật ký",
    breadcrumbKey: "admin.developer.breadcrumbLogs",
    breadcrumbDefault: "Nhật ký",
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
