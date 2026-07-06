import { HomeOutlined, LoginOutlined } from "@ant-design/icons";
import { Button, Result, Space } from "antd";
import { useTranslation } from "react-i18next";
import { useNavigate } from "react-router-dom";

import LanguageSwitcher from "@/components/LanguageSwitcher";
import ThemeToggle from "@/components/ThemeToggle";
import { useAuth } from "@/contexts/AuthContext";

const ForbiddenPage = () => {
  const { t } = useTranslation();
  const navigate = useNavigate();
  const { isAuthenticated } = useAuth();

  return (
    <div className="relative flex min-h-screen items-center justify-center bg-[#f0f2f5] p-6">
      <div className="absolute top-4 right-4 flex items-center gap-2">
        <LanguageSwitcher />
        <ThemeToggle />
      </div>
      <Result
        status="403"
        title="403"
        subTitle={t("errors.forbidden", {
          defaultValue: "Bạn không có quyền truy cập khu vực này.",
        })}
        extra={
          <Space wrap>
            <Button type="primary" icon={<HomeOutlined />} onClick={() => navigate("/")}>
              {t("common.backHome", { defaultValue: "Trang chủ" })}
            </Button>
            {!isAuthenticated && (
              <Button icon={<LoginOutlined />} onClick={() => navigate("/login")}>
                {t("auth.login", { defaultValue: "Đăng nhập" })}
              </Button>
            )}
            {isAuthenticated && (
              <Button onClick={() => navigate("/user/dashboard")}>
                {t("pages.userDashboard.title", { defaultValue: "Dashboard" })}
              </Button>
            )}
          </Space>
        }
      />
    </div>
  );
};

export default ForbiddenPage;
