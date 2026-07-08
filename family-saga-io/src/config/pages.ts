export type PageZone = "public" | "user" | "admin";

export interface AppPageMeta {
  id: string;
  zone: PageZone;
  path: string;
  titleKey: string;
  descKey: string;
  requiresAuth?: boolean;
  requiresAdmin?: boolean;
}

export const APP_PAGES: AppPageMeta[] = [
  {
    id: "home",
    zone: "public",
    path: "/",
    titleKey: "pages.home.title",
    descKey: "pages.home.desc",
  },
  {
    id: "guide",
    zone: "public",
    path: "/huong-dan",
    titleKey: "pages.guide.title",
    descKey: "pages.guide.desc",
  },
  {
    id: "login",
    zone: "public",
    path: "/login",
    titleKey: "pages.login.title",
    descKey: "pages.login.desc",
  },
  {
    id: "register",
    zone: "public",
    path: "/register",
    titleKey: "pages.register.title",
    descKey: "pages.register.desc",
  },
  {
    id: "user-dashboard",
    zone: "user",
    path: "/user/dashboard",
    titleKey: "pages.userDashboard.title",
    descKey: "pages.userDashboard.desc",
    requiresAuth: true,
  },
  {
    id: "user-document-reader",
    zone: "user",
    path: "/user/document-reader",
    titleKey: "pages.userDocumentReader.title",
    descKey: "pages.userDocumentReader.desc",
    requiresAuth: true,
  },
  {
    id: "user-family-tree",
    zone: "user",
    path: "/user/family-tree",
    titleKey: "pages.userFamilyTree.title",
    descKey: "pages.userFamilyTree.desc",
    requiresAuth: true,
  },
  {
    id: "admin-gia-pha",
    zone: "admin",
    path: "/admin/gia-pha",
    titleKey: "pages.adminGiaPha.title",
    descKey: "pages.adminGiaPha.desc",
    requiresAuth: true,
    requiresAdmin: true,
  },
  {
    id: "admin-users",
    zone: "admin",
    path: "/admin/users",
    titleKey: "pages.adminUsers.title",
    descKey: "pages.adminUsers.desc",
    requiresAuth: true,
    requiresAdmin: true,
  },
  {
    id: "admin-dev-hannom",
    zone: "admin",
    path: "/admin/developer/hannom-config",
    titleKey: "admin.developer.breadcrumbHannom",
    descKey: "admin.developer.descHannom",
    requiresAuth: true,
    requiresAdmin: true,
  },
  {
    id: "admin-dev-storage",
    zone: "admin",
    path: "/admin/developer/storage",
    titleKey: "admin.developer.breadcrumbStorage",
    descKey: "admin.developer.descStorage",
    requiresAuth: true,
    requiresAdmin: true,
  },
  {
    id: "admin-dev-crawl",
    zone: "admin",
    path: "/admin/developer/vietnamgiapha-crawl",
    titleKey: "admin.developer.breadcrumbCrawl",
    descKey: "admin.developer.descCrawl",
    requiresAuth: true,
    requiresAdmin: true,
  },
  {
    id: "admin-dev-logs",
    zone: "admin",
    path: "/admin/developer/logs",
    titleKey: "admin.developer.breadcrumbLogs",
    descKey: "admin.developer.descLogs",
    requiresAuth: true,
    requiresAdmin: true,
  },
  {
    id: "admin-dev-docs",
    zone: "admin",
    path: "/admin/developer/docs",
    titleKey: "admin.developer.breadcrumbDocs",
    descKey: "admin.developer.descDocs",
    requiresAuth: true,
    requiresAdmin: true,
  },
];

export const PUBLIC_PAGES = APP_PAGES.filter((page) => page.zone === "public");
export const USER_PAGES = APP_PAGES.filter((page) => page.zone === "user");
export const ADMIN_PAGES = APP_PAGES.filter((page) => page.zone === "admin");

export function getPageTitleKey(pathname: string): string {
  const match = APP_PAGES.find((page) => page.path === pathname);
  if (match) return match.titleKey;
  if (pathname.startsWith("/admin/users")) return "pages.adminUsers.title";
  if (pathname.startsWith("/admin/developer/hannom-config")) return "admin.developer.breadcrumbHannom";
  if (pathname.startsWith("/admin/developer/storage")) return "admin.developer.breadcrumbStorage";
  if (pathname.startsWith("/admin/developer/vietnamgiapha-crawl")) return "admin.developer.breadcrumbCrawl";
  if (pathname.startsWith("/admin/developer/logs")) return "admin.developer.breadcrumbLogs";
  if (pathname.startsWith("/admin/developer/docs")) return "admin.developer.breadcrumbDocs";
  if (pathname.match(/^\/admin\/gia-pha\/[^/]+$/)) return "pages.adminGiaPhaDetail.title";
  if (pathname.startsWith("/admin/gia-pha")) return "pages.adminGiaPha.title";
  if (pathname.startsWith("/user/document-reader")) return "pages.userDocumentReader.title";
  if (pathname.startsWith("/user/family-tree")) return "pages.userFamilyTree.title";
  if (pathname.startsWith("/user/dashboard")) return "pages.userDashboard.title";
  return "common.appName";
}
