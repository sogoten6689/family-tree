import {
  BranchesOutlined,
  InboxOutlined,
  LoginOutlined,
  ReadOutlined,
  UserAddOutlined,
} from "@ant-design/icons";
import { Breadcrumb, Button, Layout, Menu, Space, Typography } from "antd";
import type { MenuProps } from "antd";
import { useMemo } from "react";
import { Link, Outlet, useLocation, useNavigate } from "react-router-dom";
import { useTranslation } from "react-i18next";
import { useTheme } from "next-themes";

import LanguageSwitcher from "@/components/LanguageSwitcher";
import ThemeToggle from "@/components/ThemeToggle";

const { Header, Sider, Content } = Layout;

/** Không dùng ProtectedRoute — layout này phục vụ khách ẩn danh, giống cấu
 * trúc AdminLayout/UserLayout (sidebar + Outlet) nhưng không có thông tin
 * tài khoản, thay bằng nút Đăng nhập/Đăng ký ở đúng vị trí slot user-menu. */
function resolveGuestMenuKey(pathname: string): string {
  if (pathname.startsWith("/gia-pha")) return "sample-trees";
  if (pathname.startsWith("/huong-dan")) return "guide";
  return "upload";
}

const GuestLayout = () => {
  const { t } = useTranslation();
  const navigate = useNavigate();
  const location = useLocation();
  const { resolvedTheme, systemTheme } = useTheme();
  const isDark = (resolvedTheme ?? systemTheme) === "dark";

  const selectedKey = resolveGuestMenuKey(location.pathname);

  const pageTitle =
    selectedKey === "sample-trees"
      ? t("publicFamilyTrees.title", { defaultValue: "Gia phả mẫu" })
      : selectedKey === "guide"
        ? t("nav.guide", { defaultValue: "Hướng dẫn" })
        : t("docReader.pageTitle", { defaultValue: "Phòng đọc tư liệu gia phả" });

  const menuItems: MenuProps["items"] = useMemo(
    () => [
      {
        key: "upload",
        icon: <InboxOutlined />,
        label: t("flow.menu.uploadAnalyze", { defaultValue: "Tải lên & Phân tích" }),
      },
      {
        key: "sample-trees",
        icon: <BranchesOutlined />,
        label: t("nav.sampleTrees", { defaultValue: "Gia phả mẫu" }),
      },
      {
        key: "guide",
        icon: <ReadOutlined />,
        label: t("nav.guide", { defaultValue: "Hướng dẫn" }),
      },
    ],
    [t],
  );

  return (
    <Layout className="min-h-screen">
      <Sider
        width={250}
        breakpoint="lg"
        theme={isDark ? "dark" : "light"}
        className="border-r border-border !bg-[hsl(var(--sidebar-background))]"
        style={{ position: "sticky", top: 0, height: "100vh", overflow: "auto" }}
      >
        <div className="px-5 py-6">
          <Typography.Title level={5} className="!mb-1">
            {t("common.appName")}
          </Typography.Title>
          <Typography.Text type="secondary" className="text-xs">
            {t("guide.zone.public", { defaultValue: "Khách" })}
          </Typography.Text>
        </div>

        <Menu
          mode="inline"
          theme={isDark ? "dark" : "light"}
          selectedKeys={[selectedKey]}
          items={menuItems}
          className="!border-none !bg-transparent"
          onClick={({ key }) => {
            if (key === "upload") navigate("/");
            if (key === "sample-trees") navigate("/gia-pha");
            if (key === "guide") navigate("/huong-dan");
          }}
        />

        <div className="px-4 pb-4 mt-auto absolute bottom-4 left-0 right-0 space-y-2">
          <Button block type="primary" icon={<LoginOutlined />} onClick={() => navigate("/login")}>
            {t("auth.loginBtn", { defaultValue: "Đăng nhập" })}
          </Button>
          <Button block icon={<UserAddOutlined />} onClick={() => navigate("/register")}>
            {t("auth.registerBtn", { defaultValue: "Đăng ký" })}
          </Button>
        </div>
      </Sider>

      <Layout>
        <Header
          className="!px-6 flex items-center justify-between border-b border-border !bg-card"
          style={{ height: 64, position: "sticky", top: 0, zIndex: 10 }}
        >
          <div>
            <Breadcrumb
              items={[
                { title: <Link to="/">{t("common.backHome", { defaultValue: "Trang chủ" })}</Link> },
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

export default GuestLayout;
