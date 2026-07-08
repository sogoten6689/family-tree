import { useState } from "react";
import {
  BranchesOutlined,
  HomeOutlined,
  InfoCircleOutlined,
  LoginOutlined,
  MenuOutlined,
  ReadOutlined,
  StarOutlined,
  UserAddOutlined,
} from "@ant-design/icons";
import { Button, Drawer, Layout, Menu, Space, Typography } from "antd";
import type { MenuProps } from "antd";
import { Outlet, useLocation, useNavigate } from "react-router-dom";
import { useTranslation } from "react-i18next";
import { useTheme } from "next-themes";

import LanguageSwitcher from "@/components/LanguageSwitcher";
import ThemeToggle from "@/components/ThemeToggle";
import { useAuth } from "@/contexts/AuthContext";
import { useIsMobile } from "@/hooks/use-mobile";

const { Header, Content } = Layout;

const PublicLayout = () => {
  const { t } = useTranslation();
  const navigate = useNavigate();
  const location = useLocation();
  const { isAuthenticated } = useAuth();
  const isMobile = useIsMobile();
  const { resolvedTheme } = useTheme();
  const isDark = resolvedTheme === "dark";
  const [menuOpen, setMenuOpen] = useState(false);

  const selectedKey =
    location.pathname === "/huong-dan"
      ? "guide"
      : location.hash === "#features"
        ? "features"
        : location.hash === "#about"
          ? "about"
          : "home";

  const scrollToSection = (sectionId: string) => {
    if (location.pathname !== "/") {
      navigate(`/#${sectionId}`);
      setTimeout(() => document.getElementById(sectionId)?.scrollIntoView({ behavior: "smooth" }), 150);
    } else {
      document.getElementById(sectionId)?.scrollIntoView({ behavior: "smooth" });
      window.history.replaceState(null, "", `/#${sectionId}`);
    }
  };

  const handleNav: MenuProps["onClick"] = ({ key }) => {
    setMenuOpen(false);
    if (key === "home") {
      navigate("/");
      return;
    }
    if (key === "guide") {
      navigate("/huong-dan");
      return;
    }
    if (key === "sample-trees") {
      navigate("/gia-pha");
      return;
    }
    if (key === "features") {
      scrollToSection("features");
      return;
    }
    if (key === "about") {
      scrollToSection("about");
    }
  };

  const navItems: MenuProps["items"] = [
    { key: "home", icon: <HomeOutlined />, label: t("pages.home.title", { defaultValue: "Trang chủ" }) },
    { key: "sample-trees", icon: <BranchesOutlined />, label: t("nav.sampleTrees", { defaultValue: "Gia phả mẫu" }) },
    { key: "guide", icon: <ReadOutlined />, label: t("nav.guide", { defaultValue: "Hướng dẫn" }) },
    { key: "features", icon: <StarOutlined />, label: t("nav.features", { defaultValue: "Tính năng" }) },
    { key: "about", icon: <InfoCircleOutlined />, label: t("nav.about", { defaultValue: "Về chúng tôi" }) },
  ];

  const authButtons = isAuthenticated ? (
    <Button type="primary" onClick={() => navigate("/user/dashboard")}>
      {t("auth.dashboardTitle", { defaultValue: "Tổng quan" })}
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
  );

  return (
    <Layout className="min-h-screen">
      <Header
        className="!px-4 md:!px-6 flex items-center justify-between shadow-sm sticky top-0 z-50 border-b border-border"
        style={{ height: 64 }}
      >
        <Space size="middle" className="min-w-0">
          <Typography.Title
            level={4}
            className="!mb-0 cursor-pointer truncate max-w-[160px] sm:max-w-none"
            onClick={() => navigate("/")}
          >
            {t("common.appName")}
          </Typography.Title>
          {!isMobile && (
            <Menu
              mode="horizontal"
              theme={isDark ? "dark" : "light"}
              selectedKeys={[selectedKey]}
              className="!border-none min-w-[360px]"
              style={{ background: "transparent" }}
              items={navItems}
              onClick={handleNav}
            />
          )}
        </Space>

        <Space wrap size="small">
          {!isMobile && (
            <>
              <LanguageSwitcher />
              <ThemeToggle />
              {authButtons}
            </>
          )}
          {isMobile && (
            <Button icon={<MenuOutlined />} onClick={() => setMenuOpen(true)} aria-label="Menu" />
          )}
        </Space>
      </Header>

      <Drawer
        title={t("common.appName")}
        placement="right"
        open={menuOpen}
        onClose={() => setMenuOpen(false)}
        width={280}
      >
        <Menu mode="vertical" theme={isDark ? "dark" : "light"} selectedKeys={[selectedKey]} items={navItems} onClick={handleNav} />
        <Space direction="vertical" className="mt-6 w-full">
          <LanguageSwitcher />
          <ThemeToggle />
          {isAuthenticated ? (
            <Button block type="primary" onClick={() => { setMenuOpen(false); navigate("/user/dashboard"); }}>
              {t("auth.dashboardTitle", { defaultValue: "Tổng quan" })}
            </Button>
          ) : (
            <>
              <Button
                block
                icon={<LoginOutlined />}
                onClick={() => { setMenuOpen(false); navigate("/login"); }}
              >
                {t("auth.loginBtn", { defaultValue: "Đăng nhập" })}
              </Button>
              <Button
                block
                type="primary"
                icon={<UserAddOutlined />}
                onClick={() => { setMenuOpen(false); navigate("/register"); }}
              >
                {t("auth.registerBtn", { defaultValue: "Đăng ký" })}
              </Button>
            </>
          )}
        </Space>
      </Drawer>

      <Content>
        <Outlet />
      </Content>
    </Layout>
  );
};

export default PublicLayout;
