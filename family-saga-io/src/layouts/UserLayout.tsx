import {
  BookOutlined,
  BranchesOutlined,
  DashboardOutlined,
  LogoutOutlined,
  SettingOutlined,
  UserOutlined,
} from "@ant-design/icons";
import { Breadcrumb, Button, Card, Layout, Menu, Space, Typography } from "antd";
import { useMemo } from "react";
import { Link, Outlet, useLocation, useNavigate } from "react-router-dom";
import { useTranslation } from "react-i18next";
import { useTheme } from "next-themes";

import LanguageSwitcher from "@/components/LanguageSwitcher";
import ThemeToggle from "@/components/ThemeToggle";
import { getPageTitleKey } from "@/config/pages";
import { useAuth } from "@/contexts/AuthContext";

const { Header, Sider, Content } = Layout;

const menuKeyByPath: Record<string, string> = {
  "/user/dashboard": "dashboard",
  "/user/document-reader": "document-reader",
  "/user/documents": "documents",
  "/user/family-trees": "family-trees",
  "/user/family-tree": "family-tree",
  "/user/profile": "profile",
};

const UserLayout = () => {
  const { t } = useTranslation();
  const navigate = useNavigate();
  const location = useLocation();
  const { user, isAdmin, logout } = useAuth();
  const { resolvedTheme } = useTheme();
  const isDark = resolvedTheme === "dark";

  const selectedKey = menuKeyByPath[location.pathname] ?? "dashboard";
  const pageTitle = t(getPageTitleKey(location.pathname), { defaultValue: "User" });

  const menuItems = useMemo(
    () => [
      {
        key: "dashboard",
        icon: <DashboardOutlined />,
        label: t("pages.userDashboard.title", { defaultValue: "Tổng quan" }),
      },
      {
        key: "document-reader",
        icon: <BookOutlined />,
        label: t("pages.userDocumentReader.title", { defaultValue: "Đọc tài liệu" }),
      },
      {
        key: "documents",
        icon: <BookOutlined />,
        label: t("userDocuments.title", { defaultValue: "Tài liệu" }),
      },
      {
        key: "family-trees",
        icon: <BranchesOutlined />,
        label: t("userFamilyTrees.title", { defaultValue: "Gia phả" }),
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
    <Layout className="min-h-screen">
      <Sider width={250} breakpoint="lg" theme={isDark ? "dark" : "light"} className="border-r border-border">
        <div className="px-5 py-6">
          <Typography.Title level={5} className="!mb-1">
            {t("user.panelTitle", { defaultValue: "Tài khoản" })}
          </Typography.Title>
          <Typography.Text type="secondary" className="text-xs">
            {user?.full_name}
          </Typography.Text>
        </div>
        <Menu
          mode="inline"
          theme={isDark ? "dark" : "light"}
          selectedKeys={[selectedKey]}
          items={menuItems}
          className="!border-none !bg-transparent"
          onClick={({ key }) => {
            if (key === "dashboard") navigate("/user/dashboard");
            if (key === "document-reader") navigate("/user/document-reader");
            if (key === "documents") navigate("/user/documents");
            if (key === "family-trees") navigate("/user/family-trees");
            if (key === "profile") navigate("/user/profile");
          }}
        />
        <div className="px-4 pb-4 mt-auto absolute bottom-4 left-0 right-0 space-y-2">
          {isAdmin && (
            <Button block icon={<SettingOutlined />} onClick={() => navigate("/admin/gia-pha")}>
              {t("admin.panelTitle", { defaultValue: "Admin" })}
            </Button>
          )}
          <Button block icon={<LogoutOutlined />} danger onClick={logout}>
            {t("auth.logout", { defaultValue: "Đăng xuất" })}
          </Button>
        </div>
      </Sider>

      <Layout>
        <Header className="!px-6 flex items-center justify-between border-b border-border" style={{ height: 64 }}>
          <div>
            <Breadcrumb
              items={[
                { title: <Link to="/">{t("common.backHome", { defaultValue: "Trang chủ" })}</Link> },
                { title: t("user.zoneTitle", { defaultValue: "Người dùng" }) },
                { title: pageTitle },
              ]}
            />
            <Typography.Title level={4} className="!mb-0 !mt-1">
              {pageTitle}
            </Typography.Title>
          </div>
          <Space>
            <LanguageSwitcher />
            <ThemeToggle />
          </Space>
        </Header>

        <Content className="p-6 min-h-[calc(100vh-64px)]">
          <Outlet />
        </Content>
      </Layout>
    </Layout>
  );
};

export default UserLayout;
