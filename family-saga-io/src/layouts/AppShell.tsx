import { useEffect, useState, type ReactNode } from "react";
import { Breadcrumb, Button, Drawer, Layout, Menu, Space, Typography } from "antd";
import type { BreadcrumbProps, MenuProps } from "antd";
import { MenuFoldOutlined, MenuUnfoldOutlined } from "@ant-design/icons";
import { Outlet } from "react-router-dom";

import LanguageSwitcher from "@/components/LanguageSwitcher";
import ThemeToggle from "@/components/ThemeToggle";
import { useNarrowScreen } from "@/hooks/useNarrowScreen";

const { Header, Sider, Content } = Layout;

const SIDEBAR_WIDTH = 250;

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
  const [drawerOpen, setDrawerOpen] = useState(false);
  const isMobile = useNarrowScreen();

  // Chuyển từ điện thoại sang máy tính (xoay màn hình, đổi cỡ cửa sổ): đóng ngăn kéo.
  useEffect(() => {
    if (!isMobile) setDrawerOpen(false);
  }, [isMobile]);

  const handleMenuClick: MenuProps["onClick"] = (info) => {
    onMenuClick?.(info);
    if (isMobile) setDrawerOpen(false); // chọn mục xong thì đóng ngăn kéo
  };

  const sidebarContent = (
    <>
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
        onClick={handleMenuClick}
      />

      <div className="mt-auto space-y-2 px-4 pb-4 pt-4">{accountSlot}</div>
    </>
  );

  return (
    <Layout className="min-h-screen">
      {isMobile ? (
        // Điện thoại: menu là ngăn kéo trượt từ trái, không chiếm chỗ của nội dung.
        <Drawer
          open={drawerOpen}
          onClose={() => setDrawerOpen(false)}
          placement="left"
          width={Math.min(SIDEBAR_WIDTH + 30, 320)}
          closable={false}
          styles={{ body: { padding: 0 } }}
          rootClassName="app-sidebar-drawer"
        >
          <div className="app-sidebar flex min-h-full flex-col overflow-y-auto bg-[hsl(var(--sidebar-background))]">
            {sidebarContent}
          </div>
        </Drawer>
      ) : (
        /* Fixed to the viewport (not stretched to Content's height) so the
         * account slot stays pinned to the visible bottom of the screen
         * instead of sliding far below the fold on tall pages. */
        <Sider
          width={SIDEBAR_WIDTH}
          collapsedWidth={0}
          collapsed={collapsed}
          onCollapse={setCollapsed}
          trigger={null}
          theme="dark"
          className="app-sidebar !fixed !inset-y-0 !left-0 z-10 flex h-screen flex-col overflow-y-auto border-r border-border !bg-[hsl(var(--sidebar-background))]"
        >
          {sidebarContent}
        </Sider>
      )}

      <Layout
        style={{ marginLeft: isMobile || collapsed ? 0 : SIDEBAR_WIDTH }}
        className="transition-[margin] duration-200"
      >
        <Header
          className="!px-3 sm:!px-6 flex items-center justify-between gap-2 border-b border-border !bg-[hsl(var(--header))]"
          style={{ height: isMobile ? 56 : 64, position: "sticky", top: 0, zIndex: 10 }}
        >
          <div className="flex min-w-0 items-center gap-2 sm:gap-3">
            <Button
              type="text"
              aria-label={isMobile ? "Mở menu" : collapsed ? "Mở rộng menu" : "Thu gọn menu"}
              icon={(isMobile ? true : collapsed) ? <MenuUnfoldOutlined /> : <MenuFoldOutlined />}
              onClick={() => (isMobile ? setDrawerOpen(true) : setCollapsed((value) => !value))}
            />
            <div className="min-w-0">
              {/* Breadcrumb chỉ hiện từ màn hình vừa trở lên: trên điện thoại chỉ giữ tiêu đề trang. */}
              {!isMobile && <Breadcrumb items={breadcrumbItems} />}
              <Typography.Title level={isMobile ? 5 : 4} className="!mb-0 !mt-1 truncate">
                {pageTitle}
              </Typography.Title>
            </div>
          </div>
          <Space size={isMobile ? 4 : 8} className="shrink-0">
            {!isMobile && headerExtra}
            <LanguageSwitcher />
            <ThemeToggle />
          </Space>
        </Header>

        <Content className="p-3 sm:p-6 min-h-[calc(100vh-56px)] sm:min-h-[calc(100vh-64px)]">
          <Outlet />
        </Content>
      </Layout>
    </Layout>
  );
};

export default AppShell;
