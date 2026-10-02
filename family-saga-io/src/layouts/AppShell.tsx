import { useState, type ReactNode } from "react";
import { Breadcrumb, Button, Layout, Menu, Space, Typography } from "antd";
import type { BreadcrumbProps, MenuProps } from "antd";
import { MenuFoldOutlined, MenuUnfoldOutlined } from "@ant-design/icons";
import { Outlet } from "react-router-dom";

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
  const [collapsed, setCollapsed] = useState(false);

  return (
    <Layout className="min-h-screen">
      {/* Fixed to the viewport (not stretched to Content's height) so the
       * account slot stays pinned to the visible bottom of the screen
       * instead of sliding far below the fold on tall pages. */}
      <Sider
        width={250}
        breakpoint="lg"
        collapsedWidth={0}
        collapsed={collapsed}
        onCollapse={setCollapsed}
        onBreakpoint={setCollapsed}
        trigger={null}
        theme="dark"
        className="app-sidebar !fixed !inset-y-0 !left-0 z-10 flex h-screen flex-col overflow-y-auto border-r border-border !bg-[hsl(var(--sidebar-background))]"
      >
        <div className="px-5 py-6">
          <Typography.Title level={5} className="!mb-1 !text-[hsl(var(--sidebar-foreground))]">
            {panelTitle}
          </Typography.Title>
          {panelSubtitle != null && (
            <Typography.Text className="text-xs !text-[hsl(var(--sidebar-foreground)/0.75)]">
              {panelSubtitle}
            </Typography.Text>
          )}
        </div>

        <Menu
          mode="inline"
          theme="dark"
          selectedKeys={selectedKeys}
          openKeys={openKeys}
          onOpenChange={onOpenChange}
          items={menuItems}
          className="!border-none !bg-transparent"
          onClick={onMenuClick}
        />

        <div className="mt-auto space-y-2 px-4 pb-4 pt-4">{accountSlot}</div>
      </Sider>

      <Layout
        style={{ marginLeft: collapsed ? 0 : 250 }}
        className="transition-[margin] duration-200"
      >
        <Header
          className="!px-6 flex items-center justify-between border-b border-border !bg-card"
          style={{ height: 64, position: "sticky", top: 0, zIndex: 10 }}
        >
          <div className="flex items-center gap-3">
            <Button
              type="text"
              aria-label={collapsed ? "Mở rộng menu" : "Thu gọn menu"}
              icon={collapsed ? <MenuUnfoldOutlined /> : <MenuFoldOutlined />}
              onClick={() => setCollapsed((value) => !value)}
            />
            <div>
              <Breadcrumb items={breadcrumbItems} />
              <Typography.Title level={4} className="!mb-0 !mt-1">
                {pageTitle}
              </Typography.Title>
            </div>
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
