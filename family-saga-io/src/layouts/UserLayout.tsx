import {
  BookOutlined,
  BranchesOutlined,
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
import { getPageTitleKey } from "@/config/pages";
import { useAuth } from "@/contexts/AuthContext";

function resolveUserMenuKey(pathname: string): string {
  if (pathname.startsWith("/user/documents")) return "documents";
  if (pathname.startsWith("/user/family-trees") || pathname.startsWith("/user/family-tree")) {
    return "family-trees";
  }
  if (pathname.startsWith("/user/profile")) return "profile";
  if (pathname.startsWith("/user/dashboard")) return "dashboard";
  if (pathname.startsWith("/user/document-reader")) return "documents";
  return "dashboard";
}

const UserLayout = () => {
  const { t } = useTranslation();
  const navigate = useNavigate();
  const location = useLocation();
  const { user, isAdmin, logout } = useAuth();

  const selectedKey = resolveUserMenuKey(location.pathname);
  const pageTitle = t(getPageTitleKey(location.pathname), { defaultValue: "User" });

  const menuItems = useMemo(
    () => [
      {
        key: "dashboard",
        icon: <DashboardOutlined />,
        label: t("pages.userDashboard.title", { defaultValue: "Tổng quan" }),
      },
      {
        key: "documents",
        icon: <BookOutlined />,
        label: t("flow.menu.library", { defaultValue: "Thư viện tài liệu" }),
      },
      {
        key: "family-trees",
        icon: <BranchesOutlined />,
        label: t("flow.menu.myTrees", { defaultValue: "Gia phả của tôi" }),
      },
      {
        key: "profile",
        icon: <UserOutlined />,
        label: t("profile.title", { defaultValue: "Tài khoản" }),
      },
    ],
    [t],
  );

  return (
    <AppShell
      panelTitle={t("user.panelTitle", { defaultValue: "Tài khoản" })}
      panelSubtitle={user?.full_name}
      menuItems={menuItems}
      selectedKeys={[selectedKey]}
      onMenuClick={({ key }) => {
        if (key === "dashboard") navigate("/user/dashboard");
        if (key === "documents") navigate("/user/documents");
        if (key === "family-trees") navigate("/user/family-trees");
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
