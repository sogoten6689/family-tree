import { Alert, Button, Card, Form, Input, Typography } from "antd";
import { useState } from "react";
import { Link, useLocation, useNavigate } from "react-router-dom";
import { useTranslation } from "react-i18next";

import LanguageSwitcher from "@/components/LanguageSwitcher";
import ThemeToggle from "@/components/ThemeToggle";
import { useAuth } from "@/contexts/AuthContext";
import { ApiError } from "@/lib/apiClient";

type LoginFormValues = {
  email: string;
  password: string;
};

const LoginPage = () => {
  const { t } = useTranslation();
  const navigate = useNavigate();
  const location = useLocation();
  const { login } = useAuth();
  const [form] = Form.useForm<LoginFormValues>();
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);

  const redirectTo =
    (location.state as { from?: string } | null)?.from ?? "/user/dashboard";

  const handleSubmit = async (values: LoginFormValues) => {
    setLoading(true);
    setError(null);
    try {
      await login(values.email, values.password);
      navigate(redirectTo, { replace: true });
    } catch (err) {
      setError(
        err instanceof ApiError
          ? err.message
          : t("auth.loginFailed", { defaultValue: "Email hoặc mật khẩu không đúng." }),
      );
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="min-h-screen bg-background flex flex-col">
      <div className="flex justify-end gap-3 p-4">
        <LanguageSwitcher />
        <ThemeToggle />
      </div>
      <div className="flex flex-1 items-center justify-center px-4 py-8">
        <Card className="w-full max-w-md shadow-sm">
          <Typography.Title level={3} className="!mb-1">
            {t("auth.loginTitle", { defaultValue: "Đăng nhập" })}
          </Typography.Title>
          <Typography.Paragraph type="secondary" className="!mb-6">
            {t("auth.loginSubtitle", {
              defaultValue: "Truy cập hệ thống quản lý gia phả của bạn.",
            })}
          </Typography.Paragraph>

          {error && <Alert type="error" message={error} showIcon className="mb-4" />}

          <Form form={form} layout="vertical" onFinish={handleSubmit}>
            <Form.Item
              label={t("auth.email", { defaultValue: "Email" })}
              name="email"
              rules={[
                { required: true, message: t("auth.emailRequired", { defaultValue: "Vui lòng nhập email" }) },
                { type: "email", message: t("auth.emailInvalid", { defaultValue: "Email không hợp lệ" }) },
              ]}
            >
              <Input autoComplete="email" />
            </Form.Item>
            <Form.Item
              label={t("auth.password", { defaultValue: "Mật khẩu" })}
              name="password"
              rules={[
                { required: true, message: t("auth.passwordRequired", { defaultValue: "Vui lòng nhập mật khẩu" }) },
              ]}
            >
              <Input.Password autoComplete="current-password" />
            </Form.Item>
            <Button type="primary" htmlType="submit" block loading={loading}>
              {t("auth.loginBtn", { defaultValue: "Đăng nhập" })}
            </Button>
          </Form>

          <Typography.Paragraph className="!mt-4 !mb-0 text-center">
            {t("auth.noAccount", { defaultValue: "Chưa có tài khoản?" })}{" "}
            <Link to="/register">{t("auth.registerLink", { defaultValue: "Đăng ký" })}</Link>
            <Link to="/">{t("auth.homeLink", { defaultValue: "Trang chủ" })}</Link>

          </Typography.Paragraph>
        </Card>
      </div>
    </div>
  );
};

export default LoginPage;
