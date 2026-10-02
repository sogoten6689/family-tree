import {
  CodeOutlined,
  DashboardOutlined,
  DatabaseOutlined,
  HomeOutlined,
  LoginOutlined,
  LogoutOutlined,
  SettingOutlined,
  TeamOutlined,
  UnorderedListOutlined,
  UserAddOutlined,
  UserOutlined,
} from "@ant-design/icons";
import { Button, Card, Spin, Typography } from "antd";
import type { MenuProps } from "antd";
import { useEffect, useMemo, useState } from "react";
import { Link, useLocation, useNavigate } from "react-router-dom";
import { useTranslation } from "react-i18next";

import AppShell from "@/layouts/AppShell";
import { useCoreNavItems } from "@/layouts/useCoreNavItems";
import { CORE_NAV_PATHS, isCoreNavKey, resolveMenuKey, roleHomePath, type NavRole } from "@/config/coreNav";
import { DEVELOPER_NAV_ITEMS, getDeveloperNavItem, isDeveloperPath } from "@/config/developerRoutes";
import { getPageTitleKey } from "@/config/pages";
import { useAuth } from "@/contexts/AuthContext";

const DEVELOPER_ICON_MAP: Record<string, React.ReactNode> = {
  "developer-hannom": <CodeOutlined />,
  "developer-settings": <SettingOutlined />,
  "developer-storage": <DatabaseOutlined />,
  "developer-logs": <UnorderedListOutlined />,
};

/**
 * Layout duy nhất cho Guest/User/Admin: menu + ô tài khoản do VAI TRÒ người
 * đang đăng nhập quyết định, không do tiền tố URL. Trước đây mỗi vùng URL
 * (/, /user, /admin) có layout riêng nên Admin mở trang dùng chung (tải lên,
 * hướng dẫn, chi tiết bản ghi…) bị mất menu Admin, User/Admin mở link công
 * khai bị rơi về menu Guest. Quyền truy cập vẫn kiểm tra theo route
 * (ProtectedRoute/AdminRoute trong App.tsx).
 */
const RoleLayout = () => {
  const { t } = useTranslation();
  const navigate = useNavigate();
  const location = useLocation();
  const { user, isAuthenticated, isAdmin, isLoading, logout } = useAuth();
  const [menuOpenKeys, setMenuOpenKeys] = useState<string[]>([]);

  const role: NavRole = isAdmin ? "admin" : isAuthenticated ? "user" : "guest";

  useEffect(() => {
    setMenuOpenKeys(isDeveloperPath(location.pathname) ? ["developer"] : []);
  }, [location.pathname]);

  const coreNavItems = useCoreNavItems();
  const developerItem = getDeveloperNavItem(location.pathname);

  const menuItems = useMemo(() => {
    if (role === "guest") return coreNavItems;
    const items: MenuProps["items"] = [
      {
        key: "dashboard",
        icon: <DashboardOutlined />,
        label:
          role === "admin"
            ? t("adminDashboard.title", { defaultValue: "Tổng quan" })
            : t("pages.userDashboard.title", { defaultValue: "Tổng quan" }),
      },
      ...coreNavItems,
      { key: "profile", icon: <UserOutlined />, label: t("profile.title", { defaultValue: "Tài khoản" }) },
    ];
    if (role === "admin") {
      items.push(
        { key: "history", icon: <UnorderedListOutlined />, label: t("adminHistory.title", { defaultValue: "Lịch sử" }) },
        { key: "users", icon: <TeamOutlined />, label: t("admin.menuUsers", { defaultValue: "Thành viên" }) },
        {
          key: "developer",
          icon: <CodeOutlined />,
          label: t("admin.developer.menu", { defaultValue: "Công cụ nghiên cứu" }),
          children: DEVELOPER_NAV_ITEMS.map((item) => ({
            key: item.key,
            icon: DEVELOPER_ICON_MAP[item.key],
            label: t(item.labelKey, { defaultValue: item.labelDefault }),
          })),
        },
      );
    }
    return items;
  }, [role, coreNavItems, t]);

  const handleMenuClick: MenuProps["onClick"] = ({ key }) => {
    if (isCoreNavKey(key)) return navigate(CORE_NAV_PATHS[role][key]);
    if (key === "dashboard") return navigate(roleHomePath(role));
    if (key === "profile") return navigate("/user/profile");
    if (key === "history") return navigate("/admin/history");
    if (key === "users") return navigate("/admin/users");
    const devRoute = DEVELOPER_NAV_ITEMS.find((item) => item.key === key);
    if (devRoute) navigate(devRoute.path);
  };

  const pageTitle = developerItem
    ? t(developerItem.breadcrumbKey, { defaultValue: developerItem.breadcrumbDefault })
    : location.pathname === "/"
      ? t("docReader.pageTitle", { defaultValue: "Phòng đọc tư liệu gia phả" })
      : t(getPageTitleKey(location.pathname), { defaultValue: t("common.appName") });

  const breadcrumbItems = useMemo(() => {
    const items: { title: React.ReactNode }[] = [
      { title: <Link to={roleHomePath(role)}>{t("common.backHome", { defaultValue: "Trang chủ" })}</Link> },
    ];
    if (role === "admin") items.push({ title: t("admin.zoneTitle", { defaultValue: "Quản trị" }) });
    if (role === "user") items.push({ title: t("user.zoneTitle", { defaultValue: "Người dùng" }) });
    if (developerItem) items.push({ title: t("admin.developer.menu", { defaultValue: "Developer" }) });
    items.push({ title: pageTitle });
    return items;
  }, [role, t, developerItem, pageTitle]);

  if (isLoading) {
    // Chưa biết vai trò — không hiện tạm menu Guest rồi đổi (nhấp nháy).
    return (
      <div className="flex min-h-screen items-center justify-center">
        <Spin size="large" />
      </div>
    );
  }

  const panel = {
    guest: {
      title: t("common.appName"),
      subtitle: t("guide.zone.public", { defaultValue: "Khách" }),
    },
    user: { title: t("user.panelTitle", { defaultValue: "Tài khoản" }), subtitle: user?.full_name },
    admin: {
      title: t("admin.panelTitle", { defaultValue: "Admin" }),
      subtitle: t("admin.panelSubtitle", { defaultValue: "Quản trị hệ thống" }),
    },
  }[role];

  const accountSlot =
    role === "guest" ? (
      <>
        <Button block type="primary" icon={<LoginOutlined />} onClick={() => navigate("/login")}>
          {t("auth.loginBtn", { defaultValue: "Đăng nhập" })}
        </Button>
        <Button block icon={<UserAddOutlined />} onClick={() => navigate("/register")}>
          {t("auth.registerBtn", { defaultValue: "Đăng ký" })}
        </Button>
      </>
    ) : (
      <>
        {role === "admin" && (
          <>
            <Card size="small" className="!bg-primary !text-primary-foreground !border-none">
              <Typography.Text className="!text-primary-foreground text-xs block mb-2">
                {t("guide.needHelp", { defaultValue: "Cần hỗ trợ?" })}
              </Typography.Text>
              <Button block size="small" onClick={() => navigate(CORE_NAV_PATHS.admin.guide)}>
                {t("guide.openGuide", { defaultValue: "Hướng dẫn" })}
              </Button>
            </Card>
            <Button block icon={<HomeOutlined />} onClick={() => navigate(roleHomePath(role))}>
              {t("common.backHome", { defaultValue: "Trang chủ" })}
            </Button>
          </>
        )}
        <Button block icon={<LogoutOutlined />} danger onClick={logout}>
          {t("auth.logout", { defaultValue: "Đăng xuất" })}
        </Button>
      </>
    );

  return (
    <AppShell
      panelTitle={panel.title}
      panelSubtitle={panel.subtitle}
      menuItems={menuItems}
      selectedKeys={[resolveMenuKey(location.pathname)]}
      openKeys={menuOpenKeys}
      onOpenChange={setMenuOpenKeys}
      onMenuClick={handleMenuClick}
      accountSlot={accountSlot}
      headerExtra={
        role === "admin" ? (
          <Typography.Text type="secondary">
            {user?.full_name} · {user?.role}
          </Typography.Text>
        ) : undefined
      }
      breadcrumbItems={breadcrumbItems}
      pageTitle={pageTitle}
    />
  );
};

export default RoleLayout;
