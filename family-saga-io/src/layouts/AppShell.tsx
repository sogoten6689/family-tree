import type { ReactNode } from "react";
import { Breadcrumb, Layout, Menu, Space, Typography } from "antd";
import type { BreadcrumbProps, MenuProps } from "antd";
import { Outlet } from "react-router-dom";
import { useTheme } from "next-themes";

import LanguageSwitcher from "@/components/LanguageSwitcher";
import ThemeToggle from "@/components/ThemeToggle";

const { Header, Sider, Content } = Layout;

export interface AppShellProps {
  panelTitle: ReactNode;
  panelSubtitle?: ReactNode;
  menuItems: MenuProps["items"];
  selectedKeys: string[];
  openKeys?: string[];
  onOpenChange?: (keys: string[]) => void;
  onMenuClick: MenuProps["onClick"];
  /** Bottom-of-sidebar content — differs per account type by design. */
  accountSlot: ReactNode;
  breadcrumbItems: BreadcrumbProps["items"];
  pageTitle: ReactNode;
  /** Extra header content before Language/Theme — used by Admin (name · role + logout). */
  headerExtra?: ReactNode;
}

/**
 * Shared Sider + Header + Content shell used by Guest/User/Admin layouts.
 * Only presentational — each caller owns its own menu resolution, routing
 * and auth logic, and passes the differences in through props.
 */
const AppShell = ({
  panelTitle,
  panelSubtitle,
  menuItems,
  selectedKeys,
  openKeys,
  onOpenChange,
  onMenuClick,
  accountSlot,
  breadcrumbItems,
  pageTitle,
  headerExtra,
}: AppShellProps) => {
  const { resolvedTheme, systemTheme } = useTheme();
  const isDark = (resolvedTheme ?? systemTheme) === "dark";

  return (
    <Layout className="min-h-screen">
      <Sider
        width={250}
        breakpoint="lg"
        theme={isDark ? "dark" : "light"}
        className="border-r border-border !bg-[hsl(var(--sidebar-background))]"
      >
        <div className="px-5 py-6">
          <Typography.Title level={5} className="!mb-1">
            {panelTitle}
          </Typography.Title>
          {panelSubtitle != null && (
            <Typography.Text type="secondary" className="text-xs">
              {panelSubtitle}
            </Typography.Text>
          )}
        </div>

        <Menu
          mode="inline"
          theme={isDark ? "dark" : "light"}
          selectedKeys={selectedKeys}
          openKeys={openKeys}
          onOpenChange={onOpenChange}
          items={menuItems}
          className="!border-none !bg-transparent"
          onClick={onMenuClick}
        />

        <div className="px-4 pb-4 mt-auto absolute bottom-4 left-0 right-0 space-y-2">
          {accountSlot}
        </div>
      </Sider>

      <Layout>
        <Header
          className="!px-6 flex items-center justify-between border-b border-border !bg-card"
          style={{ height: 64 }}
        >
          <div>
            <Breadcrumb items={breadcrumbItems} />
            <Typography.Title level={4} className="!mb-0 !mt-1">
              {pageTitle}
            </Typography.Title>
          </div>
          <Space wrap>
            {headerExtra}
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

export default AppShell;
