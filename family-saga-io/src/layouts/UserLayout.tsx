import {
  DashboardOutlined,
  LogoutOutlined,
  SettingOutlined,
  UserOutlined,
} from "@ant-design/icons";
import { Button } from "antd";
import { useMemo } from "react";
import { Link, useLocation, useNavigate } from "react-router-dom";
import { useTranslation } from "react-i18next";

import AppShell from "@/layouts/AppShell";
import { useCoreNavItems } from "@/layouts/useCoreNavItems";
import { CORE_NAV_PATHS, isCoreNavKey } from "@/config/coreNav";
import { getPageTitleKey } from "@/config/pages";
import { useAuth } from "@/contexts/AuthContext";

function resolveUserMenuKey(pathname: string): string {
  // "/user/documents/new" là màn hình tải lên; "/user/documents/:id" là chi
  // tiết 1 bộ gia phả chưa dựng cây — thuộc mục "Gia phả".
  if (pathname.startsWith("/user/documents/new") || pathname.startsWith("/user/document-reader")) {
    return "upload";
  }
  if (pathname.startsWith("/user/gia-pha") || pathname.startsWith("/user/documents")) return "gia-pha";
  if (pathname.startsWith("/user/huong-dan")) return "guide";
  if (pathname.startsWith("/user/profile")) return "profile";
  return "dashboard";
}

const UserLayout = () => {
  const { t } = useTranslation();
  const navigate = useNavigate();
  const location = useLocation();
  const { user, isAdmin, logout } = useAuth();

  const selectedKey = resolveUserMenuKey(location.pathname);
  const pageTitle = t(getPageTitleKey(location.pathname), { defaultValue: "User" });

  const coreNavItems = useCoreNavItems();
  const menuItems = useMemo(
    () => [
      {
        key: "dashboard",
        icon: <DashboardOutlined />,
        label: t("pages.userDashboard.title", { defaultValue: "Tổng quan" }),
      },
      ...coreNavItems,
      {
        key: "profile",
        icon: <UserOutlined />,
        label: t("profile.title", { defaultValue: "Tài khoản" }),
      },
    ],
    [t, coreNavItems],
  );

  return (
    <AppShell
      panelTitle={t("user.panelTitle", { defaultValue: "Tài khoản" })}
      panelSubtitle={user?.full_name}
      menuItems={menuItems}
      selectedKeys={[selectedKey]}
      onMenuClick={({ key }) => {
        if (isCoreNavKey(key)) navigate(CORE_NAV_PATHS.user[key]);
        if (key === "dashboard") navigate("/user/dashboard");
        if (key === "profile") navigate("/user/profile");
      }}
      accountSlot={
        <>
          {isAdmin && (
            <Button block icon={<SettingOutlined />} onClick={() => navigate("/admin/gia-pha")}>
              {t("admin.panelTitle", { defaultValue: "Admin" })}
            </Button>
          )}
          <Button block icon={<LogoutOutlined />} danger onClick={logout}>
            {t("auth.logout", { defaultValue: "Đăng xuất" })}
          </Button>
        </>
      }
      breadcrumbItems={[
        { title: <Link to="/">{t("common.backHome", { defaultValue: "Trang chủ" })}</Link> },
        { title: t("user.zoneTitle", { defaultValue: "Người dùng" }) },
        { title: pageTitle },
      ]}
      pageTitle={pageTitle}
    />
  );
};

export default UserLayout;
