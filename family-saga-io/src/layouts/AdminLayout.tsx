import {
  BranchesOutlined,
  HomeOutlined,
  LogoutOutlined,
  TeamOutlined,
} from "@ant-design/icons";
import { Breadcrumb, Button, Card, Layout, Menu, Space, Typography } from "antd";
import { useMemo } from "react";
import { Link, Outlet, useLocation, useNavigate } from "react-router-dom";
import { useTranslation } from "react-i18next";

import LanguageSwitcher from "@/components/LanguageSwitcher";
import ThemeToggle from "@/components/ThemeToggle";
import { getPageTitleKey } from "@/config/pages";
import { useAuth } from "@/contexts/AuthContext";

const { Header, Sider, Content } = Layout;

const AdminLayout = () => {
  const { t } = useTranslation();
  const navigate = useNavigate();
  const location = useLocation();
  const { user, logout } = useAuth();

  const selectedKey = location.pathname.startsWith("/admin/users") ? "users" : "gia-pha";
  const pageTitle = t(getPageTitleKey(location.pathname), {
    defaultValue: t("admin.panelTitle", { defaultValue: "Admin" }),
  });

  const menuItems = useMemo(
    () => [
      {
        key: "gia-pha",
        icon: <BranchesOutlined />,
        label: t("admin.menuFamilyTrees", { defaultValue: "Quản lý gia phả" }),
      },
      {
        key: "users",
        icon: <TeamOutlined />,
        label: t("admin.menuUsers", { defaultValue: "Quản lý thành viên" }),
      },
    ],
    [t],
  );

  return (
    <Layout className="min-h-screen">
      <Sider width={250} breakpoint="lg" theme="light" className="!bg-[#f8f9fa] border-r border-[#e9ecef]">
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
          selectedKeys={[selectedKey]}
          items={menuItems}
          className="!border-none !bg-transparent"
          onClick={({ key }) => {
            if (key === "users") navigate("/admin/users");
            else navigate("/admin/gia-pha");
          }}
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
        <Header className="!bg-white !px-6 flex items-center justify-between border-b border-[#e9ecef]" style={{ height: 64 }}>
          <div>
            <Breadcrumb
              items={[
                { title: <Link to="/">{t("common.backHome", { defaultValue: "Trang chủ" })}</Link> },
                { title: t("admin.zoneTitle", { defaultValue: "Quản trị" }) },
                { title: pageTitle },
              ]}
            />
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

        <Content className="p-6 bg-[#f0f2f5] min-h-[calc(100vh-64px)]">
          <Outlet />
        </Content>
      </Layout>
    </Layout>
  );
};

export default AdminLayout;
