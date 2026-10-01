import { LoginOutlined, UserAddOutlined } from "@ant-design/icons";
import { Button } from "antd";
import { Link, useLocation, useNavigate } from "react-router-dom";
import { useTranslation } from "react-i18next";

import AppShell from "@/layouts/AppShell";
import { useCoreNavItems } from "@/layouts/useCoreNavItems";
import { CORE_NAV_PATHS, isCoreNavKey } from "@/config/coreNav";

/** Không dùng ProtectedRoute — layout này phục vụ khách ẩn danh, dùng chung
 * AppShell với AdminLayout/UserLayout (sidebar + Outlet) nhưng không có
 * thông tin tài khoản, thay bằng nút Đăng nhập/Đăng ký ở account slot. */
function resolveGuestMenuKey(pathname: string): string {
  if (pathname.startsWith("/gia-pha")) return "gia-pha";
  if (pathname.startsWith("/huong-dan")) return "guide";
  return "upload";
}

const GuestLayout = () => {
  const { t } = useTranslation();
  const navigate = useNavigate();
  const location = useLocation();

  const selectedKey = resolveGuestMenuKey(location.pathname);

  const pageTitle =
    selectedKey === "gia-pha"
      ? t("coreNav.giaPha", { defaultValue: "Gia phả" })
      : selectedKey === "guide"
        ? t("nav.guide", { defaultValue: "Hướng dẫn" })
        : t("docReader.pageTitle", { defaultValue: "Phòng đọc tư liệu gia phả" });

  const menuItems = useCoreNavItems();

  return (
    <AppShell
      panelTitle={t("common.appName")}
      panelSubtitle={t("guide.zone.public", { defaultValue: "Khách" })}
      menuItems={menuItems}
      selectedKeys={[selectedKey]}
      onMenuClick={({ key }) => {
        if (isCoreNavKey(key)) navigate(CORE_NAV_PATHS.guest[key]);
      }}
      accountSlot={
        <>
          <Button block type="primary" icon={<LoginOutlined />} onClick={() => navigate("/login")}>
            {t("auth.loginBtn", { defaultValue: "Đăng nhập" })}
          </Button>
          <Button block icon={<UserAddOutlined />} onClick={() => navigate("/register")}>
            {t("auth.registerBtn", { defaultValue: "Đăng ký" })}
          </Button>
        </>
      }
      breadcrumbItems={[
        { title: <Link to="/">{t("common.backHome", { defaultValue: "Trang chủ" })}</Link> },
        { title: pageTitle },
      ]}
      pageTitle={pageTitle}
    />
  );
};

export default GuestLayout;
