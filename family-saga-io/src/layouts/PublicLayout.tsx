import { HomeOutlined, LoginOutlined, ReadOutlined, UserAddOutlined } from "@ant-design/icons";
import { Button, Layout, Menu, Space, Typography } from "antd";
import { Outlet, useLocation, useNavigate } from "react-router-dom";
import { useTranslation } from "react-i18next";

import LanguageSwitcher from "@/components/LanguageSwitcher";
import ThemeToggle from "@/components/ThemeToggle";
import { useAuth } from "@/contexts/AuthContext";

const { Header, Content } = Layout;

const PublicLayout = () => {
  const { t } = useTranslation();
  const navigate = useNavigate();
  const location = useLocation();
  const { isAuthenticated } = useAuth();

  const selectedKey = location.pathname === "/huong-dan" ? "guide" : "home";

  return (
    <Layout className="min-h-screen bg-[#f8f9fa]">
      <Header className="!bg-white !px-6 flex items-center justify-between shadow-sm" style={{ height: 64 }}>
        <Space size="large">
          <Typography.Title
            level={4}
            className="!mb-0 cursor-pointer"
            onClick={() => navigate("/")}
          >
            {t("common.appName")}
          </Typography.Title>
          <Menu
            mode="horizontal"
            selectedKeys={[selectedKey]}
            className="!border-none !bg-transparent min-w-[240px]"
            items={[
              { key: "home", icon: <HomeOutlined />, label: t("pages.home.title", { defaultValue: "Trang chủ" }) },
              { key: "guide", icon: <ReadOutlined />, label: t("pages.guide.title", { defaultValue: "Hướng dẫn" }) },
            ]}
            onClick={({ key }) => navigate(key === "guide" ? "/huong-dan" : "/")}
          />
        </Space>
        <Space wrap>
          <LanguageSwitcher />
          <ThemeToggle />
          {isAuthenticated ? (
            <Button type="primary" onClick={() => navigate("/user/dashboard")}>
              {t("auth.dashboardTitle", { defaultValue: "Bảng điều khiển" })}
            </Button>
          ) : (
            <>
              <Button icon={<LoginOutlined />} onClick={() => navigate("/login")}>
                {t("auth.loginBtn", { defaultValue: "Đăng nhập" })}
              </Button>
              <Button type="primary" icon={<UserAddOutlined />} onClick={() => navigate("/register")}>
                {t("auth.registerBtn", { defaultValue: "Đăng ký" })}
              </Button>
            </>
          )}
        </Space>
      </Header>

      <Content>
        <Outlet />
      </Content>
    </Layout>
  );
};

export default PublicLayout;
