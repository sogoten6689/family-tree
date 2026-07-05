import { Button, Card, Space, Typography } from "antd";
import { useNavigate } from "react-router-dom";
import { useTranslation } from "react-i18next";

import LanguageSwitcher from "@/components/LanguageSwitcher";
import ThemeToggle from "@/components/ThemeToggle";
import { useAuth } from "@/contexts/AuthContext";

const DashboardPage = () => {
  const { t } = useTranslation();
  const navigate = useNavigate();
  const { user, isAdmin, logout } = useAuth();

  return (
    <div className="min-h-screen bg-background">
      <div className="border-b border-border bg-card px-4 py-4">
        <div className="mx-auto flex max-w-5xl items-center justify-between gap-4">
          <Typography.Title level={4} className="!mb-0">
            {t("auth.dashboardTitle", { defaultValue: "Bảng điều khiển" })}
          </Typography.Title>
          <Space>
            <LanguageSwitcher />
            <ThemeToggle />
            <Button onClick={() => navigate("/")}>{t("common.backHome", { defaultValue: "Trang chủ" })}</Button>
            <Button onClick={logout}>{t("auth.logout", { defaultValue: "Đăng xuất" })}</Button>
          </Space>
        </div>
      </div>

      <main className="mx-auto max-w-5xl px-4 py-8">
        <Card className="mb-6">
          <Typography.Title level={4}>
            {t("auth.welcomeUser", {
              defaultValue: "Xin chào, {{name}}",
              name: user?.full_name ?? user?.email,
            })}
          </Typography.Title>
          <Typography.Paragraph type="secondary">
            {t("auth.currentRole", {
              defaultValue: "Quyền hiện tại: {{role}}",
              role: user?.role,
            })}
          </Typography.Paragraph>
        </Card>

        <Space wrap>
          <Button type="primary" onClick={() => navigate("/document-reader")}>
            {t("home.btnOpenDoc", { defaultValue: "Mở Tài Liệu Gốc" })}
          </Button>
          <Button onClick={() => navigate("/family-tree")}>
            {t("home.btnViewSample", { defaultValue: "Xem Gia Phả Mẫu" })}
          </Button>
          {isAdmin && (
            <>
              <Button onClick={() => navigate("/admin/gia-pha")}>
                {t("home.btnManageTree", { defaultValue: "Quản lý gia phả" })}
              </Button>
              <Button onClick={() => navigate("/admin/users")}>
                {t("auth.adminUsersTitle", { defaultValue: "Quản lý thành viên" })}
              </Button>
            </>
          )}
        </Space>
      </main>
    </div>
  );
};

export default DashboardPage;
