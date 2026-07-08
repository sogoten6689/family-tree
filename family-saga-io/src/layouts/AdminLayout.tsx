import {
  BranchesOutlined,
  CodeOutlined,
  DashboardOutlined,
  DatabaseOutlined,
  FileTextOutlined,
  HomeOutlined,
  LogoutOutlined,
  TeamOutlined,
  UnorderedListOutlined,
} from "@ant-design/icons";
import { Breadcrumb, Button, Card, Layout, Menu, Space, Typography } from "antd";
import type { MenuProps } from "antd";
import { useEffect, useMemo, useState } from "react";
import { Link, Outlet, useLocation, useNavigate } from "react-router-dom";
import { useTranslation } from "react-i18next";
import { useTheme } from "next-themes";

import LanguageSwitcher from "@/components/LanguageSwitcher";
import ThemeToggle from "@/components/ThemeToggle";
import {
  DEVELOPER_NAV_ITEMS,
  getAdminMenuSelectedKey,
  getDeveloperNavItem,
  isDeveloperPath,
} from "@/config/developerRoutes";
import { getPageTitleKey } from "@/config/pages";
import { useAuth } from "@/contexts/AuthContext";

const { Header, Sider, Content } = Layout;

const DEVELOPER_ICON_MAP: Record<string, React.ReactNode> = {
  "developer-hannom": <CodeOutlined />,
  "developer-storage": <DatabaseOutlined />,
  "developer-logs": <UnorderedListOutlined />,
  "developer-docs": <FileTextOutlined />,
};

const AdminLayout = () => {
  const { t } = useTranslation();
  const navigate = useNavigate();
  const location = useLocation();
  const { user, logout, isAdmin } = useAuth();
  const { resolvedTheme } = useTheme();
  const isDark = resolvedTheme === "dark";
  const [menuOpenKeys, setMenuOpenKeys] = useState<string[]>([]);

  useEffect(() => {
    if (isDeveloperPath(location.pathname)) {
      setMenuOpenKeys(["developer"]);
    }
  }, [location.pathname]);

  const selectedKey = getAdminMenuSelectedKey(location.pathname);
  const developerItem = getDeveloperNavItem(location.pathname);
  const pageTitle = developerItem
    ? t(developerItem.breadcrumbKey, { defaultValue: developerItem.breadcrumbDefault })
    : t(getPageTitleKey(location.pathname), {
        defaultValue: t("admin.panelTitle", { defaultValue: "Admin" }),
      });

  const developerChildren = useMemo(
    () =>
      DEVELOPER_NAV_ITEMS.map((item) => ({
        key: item.key,
        icon: DEVELOPER_ICON_MAP[item.key],
        label: t(item.labelKey, { defaultValue: item.labelDefault }),
      })),
    [t],
  );

  const menuItems = useMemo(() => {
    const items: MenuProps["items"] = [
      {
        key: "dashboard",
        icon: <DashboardOutlined />,
        label: t("adminDashboard.title", { defaultValue: "Dashboard" }),
      },
      {
        key: "gia-pha",
        icon: <BranchesOutlined />,
        label: t("admin.menuFamilyTrees", { defaultValue: "Quản lý gia phả" }),
      },
      {
        key: "history",
        icon: <UnorderedListOutlined />,
        label: t("adminHistory.title", { defaultValue: "Lịch sử scan" }),
      },
      {
        key: "users",
        icon: <TeamOutlined />,
        label: t("admin.menuUsers", { defaultValue: "Quản lý thành viên" }),
      },
    ];

    if (isAdmin) {
      items.push({
        key: "developer",
        icon: <CodeOutlined />,
        label: t("admin.developer.menu", { defaultValue: "Developer" }),
        children: developerChildren,
      });
    }

    return items;
  }, [t, isAdmin, developerChildren]);

  const openKeys = menuOpenKeys;

  const breadcrumbItems = useMemo(() => {
    const items: { title: React.ReactNode }[] = [
      { title: <Link to="/">{t("common.backHome", { defaultValue: "Trang chủ" })}</Link> },
      { title: t("admin.zoneTitle", { defaultValue: "Quản trị" }) },
    ];

    if (isDeveloperPath(location.pathname)) {
      items.push({
        title: t("admin.developer.menu", { defaultValue: "Developer" }),
      });
      if (developerItem) {
        items.push({
          title: t(developerItem.breadcrumbKey, { defaultValue: developerItem.breadcrumbDefault }),
        });
      }
    } else {
      items.push({ title: pageTitle });
    }

    return items;
  }, [t, location.pathname, developerItem, pageTitle]);

  const handleMenuClick: MenuProps["onClick"] = ({ key }) => {
    if (key === "dashboard") {
      navigate("/admin/dashboard");
      return;
    }
    if (key === "history") {
      navigate("/admin/history");
      return;
    }
    if (key === "users") {
      navigate("/admin/users");
      return;
    }
    if (key === "gia-pha") {
      navigate("/admin/gia-pha");
      return;
    }

    const devRoute = DEVELOPER_NAV_ITEMS.find((item) => item.key === key);
    if (devRoute) {
      navigate(devRoute.path);
    }
  };

  return (
    <Layout className="min-h-screen">
      <Sider width={250} breakpoint="lg" theme={isDark ? "dark" : "light"} className="border-r border-border">
        <div className="px-5 py-6">
          <Typography.Title level={5} className="!mb-1">
            {t("admin.panelTitle", { defaultValue: "Admin" })}
          </Typography.Title>
          <Typography.Text type="secondary" className="text-xs">
            {t("admin.panelSubtitle", { defaultValue: "Quản trị hệ thống" })}
          </Typography.Text>
        </div>

        <Menu
          mode="inline"
          theme={isDark ? "dark" : "light"}
          selectedKeys={[selectedKey]}
          openKeys={openKeys}
          onOpenChange={setMenuOpenKeys}
          items={menuItems}
          className="!border-none !bg-transparent"
          onClick={handleMenuClick}
        />

        <div className="px-4 absolute bottom-4 left-0 right-0 space-y-2">
          <Card size="small" className="!bg-[#1677ff] !text-white !border-none">
            <Typography.Text className="!text-white text-xs block mb-2">
              {t("guide.needHelp", { defaultValue: "Cần hỗ trợ?" })}
            </Typography.Text>
            <Button block size="small" onClick={() => navigate("/huong-dan")}>
              {t("guide.openGuide", { defaultValue: "Xem hướng dẫn" })}
            </Button>
          </Card>
          <Button block icon={<HomeOutlined />} onClick={() => navigate("/")}>
            {t("common.backHome", { defaultValue: "Trang chủ" })}
          </Button>
        </div>
      </Sider>

      <Layout>
        <Header className="!px-6 flex items-center justify-between border-b border-border" style={{ height: 64 }}>
          <div>
            <Breadcrumb items={breadcrumbItems} />
            <Typography.Title level={4} className="!mb-0 !mt-1">
              {pageTitle}
            </Typography.Title>
          </div>
          <Space wrap>
            <Typography.Text type="secondary">
              {user?.full_name} · {user?.role}
            </Typography.Text>
            <LanguageSwitcher />
            <ThemeToggle />
            <Button icon={<LogoutOutlined />} onClick={logout}>
              {t("auth.logout", { defaultValue: "Đăng xuất" })}
            </Button>
          </Space>
        </Header>

        <Content className="p-6 min-h-[calc(100vh-64px)]">
          <Outlet />
        </Content>
      </Layout>
    </Layout>
  );
};

export default AdminLayout;
