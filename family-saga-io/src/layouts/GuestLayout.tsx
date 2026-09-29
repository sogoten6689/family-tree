import {
  BranchesOutlined,
  InboxOutlined,
  LoginOutlined,
  ReadOutlined,
  UserAddOutlined,
} from "@ant-design/icons";
import { Button } from "antd";
import type { MenuProps } from "antd";
import { useMemo } from "react";
import { Link, useLocation, useNavigate } from "react-router-dom";
import { useTranslation } from "react-i18next";

import AppShell from "@/layouts/AppShell";

/** Không dùng ProtectedRoute — layout này phục vụ khách ẩn danh, dùng chung
 * AppShell với AdminLayout/UserLayout (sidebar + Outlet) nhưng không có
 * thông tin tài khoản, thay bằng nút Đăng nhập/Đăng ký ở account slot. */
function resolveGuestMenuKey(pathname: string): string {
  if (pathname.startsWith("/gia-pha")) return "sample-trees";
  if (pathname.startsWith("/huong-dan")) return "guide";
  return "upload";
}

const GuestLayout = () => {
  const { t } = useTranslation();
  const navigate = useNavigate();
  const location = useLocation();

  const selectedKey = resolveGuestMenuKey(location.pathname);

  const pageTitle =
    selectedKey === "sample-trees"
      ? t("publicFamilyTrees.title", { defaultValue: "Gia phả mẫu" })
      : selectedKey === "guide"
        ? t("nav.guide", { defaultValue: "Hướng dẫn" })
        : t("docReader.pageTitle", { defaultValue: "Phòng đọc tư liệu gia phả" });

  const menuItems: MenuProps["items"] = useMemo(
    () => [
      {
        key: "upload",
        icon: <InboxOutlined />,
        label: t("flow.menu.uploadAnalyze", { defaultValue: "Tải lên & Phân tích" }),
      },
      {
        key: "sample-trees",
        icon: <BranchesOutlined />,
        label: t("nav.sampleTrees", { defaultValue: "Gia phả mẫu" }),
      },
      {
        key: "guide",
        icon: <ReadOutlined />,
        label: t("nav.guide", { defaultValue: "Hướng dẫn" }),
      },
    ],
    [t],
  );

  return (
    <AppShell
      panelTitle={t("common.appName")}
      panelSubtitle={t("guide.zone.public", { defaultValue: "Khách" })}
      menuItems={menuItems}
      selectedKeys={[selectedKey]}
      onMenuClick={({ key }) => {
        if (key === "upload") navigate("/");
        if (key === "sample-trees") navigate("/gia-pha");
        if (key === "guide") navigate("/huong-dan");
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
