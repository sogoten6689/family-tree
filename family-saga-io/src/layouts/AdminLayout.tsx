import {
  BranchesOutlined,
  CloudDownloadOutlined,
  CodeOutlined,
  DashboardOutlined,
  DatabaseOutlined,
  FileTextOutlined,
  HomeOutlined,
  LogoutOutlined,
  TeamOutlined,
  UnorderedListOutlined,
} from "@ant-design/icons";
import { Button, Card, Typography } from "antd";
import type { MenuProps } from "antd";
import { useEffect, useMemo, useState } from "react";
import { Link, useLocation, useNavigate } from "react-router-dom";
import { useTranslation } from "react-i18next";

import AppShell from "@/layouts/AppShell";
import {
  DEVELOPER_NAV_ITEMS,
  getAdminMenuSelectedKey,
  getDeveloperNavItem,
  isDeveloperPath,
} from "@/config/developerRoutes";
import { getPageTitleKey } from "@/config/pages";
import { useAuth } from "@/contexts/AuthContext";

const DEVELOPER_ICON_MAP: Record<string, React.ReactNode> = {
  "developer-hannom": <CodeOutlined />,
  "developer-storage": <DatabaseOutlined />,
  "developer-crawl": <CloudDownloadOutlined />,
  "developer-logs": <UnorderedListOutlined />,
  "developer-docs": <FileTextOutlined />,
};

const AdminLayout = () => {
  const { t } = useTranslation();
  const navigate = useNavigate();
  const location = useLocation();
  const { user, logout, isAdmin } = useAuth();
  const [menuOpenKeys, setMenuOpenKeys] = useState<string[]>([]);

  useEffect(() => {
    if (isDeveloperPath(location.pathname)) {
      setMenuOpenKeys(["developer"]);
    } else {
      setMenuOpenKeys([]);
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
        label: t("adminDashboard.title", { defaultValue: "Tổng quan" }),
      },
      {
        key: "gia-pha",
        icon: <BranchesOutlined />,
        label: t("flow.menu.treesAndDocs", { defaultValue: "Gia phả & tài liệu" }),
      },
      {
        key: "history",
        icon: <UnorderedListOutlined />,
        label: t("adminHistory.title", { defaultValue: "Lịch sử" }),
      },
      {
        key: "users",
        icon: <TeamOutlined />,
        label: t("admin.menuUsers", { defaultValue: "Thành viên" }),
      },
    ];

    if (isAdmin) {
      items.push({
        key: "developer",
        icon: <CodeOutlined />,
        label: t("admin.developer.menu", { defaultValue: "Công cụ nghiên cứu" }),
        children: developerChildren,
      });
    }

    return items;
  }, [t, isAdmin, developerChildren]);

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
    <AppShell
      panelTitle={t("admin.panelTitle", { defaultValue: "Admin" })}
      panelSubtitle={t("admin.panelSubtitle", { defaultValue: "Quản trị hệ thống" })}
      menuItems={menuItems}
      selectedKeys={[selectedKey]}
      openKeys={menuOpenKeys}
      onOpenChange={setMenuOpenKeys}
      onMenuClick={handleMenuClick}
      accountSlot={
        <>
          <Card size="small" className="!bg-primary !text-primary-foreground !border-none">
            <Typography.Text className="!text-primary-foreground text-xs block mb-2">
              {t("guide.needHelp", { defaultValue: "Cần hỗ trợ?" })}
            </Typography.Text>
            <Button block size="small" onClick={() => navigate("/huong-dan")}>
              {t("guide.openGuide", { defaultValue: "Hướng dẫn" })}
            </Button>
          </Card>
          <Button block icon={<HomeOutlined />} onClick={() => navigate("/")}>
            {t("common.backHome", { defaultValue: "Trang chủ" })}
          </Button>
        </>
      }
      headerExtra={
        <>
          <Typography.Text type="secondary">
            {user?.full_name} · {user?.role}
          </Typography.Text>
          <Button icon={<LogoutOutlined />} onClick={logout}>
            {t("auth.logout", { defaultValue: "Đăng xuất" })}
          </Button>
        </>
      }
      breadcrumbItems={breadcrumbItems}
      pageTitle={pageTitle}
    />
  );
};

export default AdminLayout;
