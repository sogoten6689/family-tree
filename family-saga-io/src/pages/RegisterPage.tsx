import { Alert, Button, Card, Form, Input, Typography } from "antd";
import { useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import { useTranslation } from "react-i18next";

import LanguageSwitcher from "@/components/LanguageSwitcher";
import ThemeToggle from "@/components/ThemeToggle";
import { useAuth } from "@/contexts/AuthContext";
import { ApiError } from "@/lib/apiClient";

type RegisterFormValues = {
  full_name: string;
  email: string;
  password: string;
};

const RegisterPage = () => {
  const { t } = useTranslation();
  const navigate = useNavigate();
  const { register } = useAuth();
  const [form] = Form.useForm<RegisterFormValues>();
  const [error, setError] = useState<string | null>(null);
  const [success, setSuccess] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);

  const handleSubmit = async (values: RegisterFormValues) => {
    setLoading(true);
    setError(null);
    setSuccess(null);
    try {
      await register(values);
      setSuccess(
        t("auth.registerSuccess", {
          defaultValue: "Đăng ký thành công. Vui lòng đăng nhập.",
        }),
      );
      window.setTimeout(() => navigate("/login"), 800);
    } catch (err) {
      setError(
        err instanceof ApiError
          ? err.message
          : t("auth.registerFailed", { defaultValue: "Không thể đăng ký. Vui lòng thử lại." }),
      );
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="min-h-screen auth-page-shell flex flex-col">
      <div className="flex justify-end gap-3 p-4">
        <LanguageSwitcher />
        <ThemeToggle />
      </div>
      <div className="flex flex-1 items-center justify-center px-4 py-8">
        <Card className="w-full max-w-md shadow-sm">
          <Typography.Title level={3} className="!mb-1">
            {t("auth.registerTitle", { defaultValue: "Đăng ký" })}
          </Typography.Title>
          <Typography.Paragraph type="secondary" className="!mb-6">
            {t("auth.registerSubtitle", {
              defaultValue: "Tạo tài khoản mới với quyền mặc định là user.",
            })}
          </Typography.Paragraph>

          {error && <Alert type="error" message={error} showIcon className="mb-4" />}
          {success && <Alert type="success" message={success} showIcon className="mb-4" />}

          <Form form={form} layout="vertical" onFinish={handleSubmit}>
            <Form.Item
              label={t("auth.fullName", { defaultValue: "Họ và tên" })}
              name="full_name"
              rules={[
                {
                  required: true,
                  message: t("auth.fullNameRequired", { defaultValue: "Vui lòng nhập họ tên" }),
                },
              ]}
            >
              <Input />
            </Form.Item>
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
                { min: 8, message: t("auth.passwordMin", { defaultValue: "Mật khẩu tối thiểu 8 ký tự" }) },
              ]}
            >
              <Input.Password autoComplete="new-password" />
            </Form.Item>
            <Button type="primary" htmlType="submit" block loading={loading}>
              {t("auth.registerBtn", { defaultValue: "Đăng ký" })}
            </Button>
          </Form>

          <Typography.Paragraph className="!mt-4 !mb-2 text-center text-muted-foreground">
            {t("auth.haveAccount", { defaultValue: "Đã có tài khoản?" })}{" "}
            <Link to="/login" className="text-primary hover:underline">
              {t("auth.loginLink", { defaultValue: "Đăng nhập" })}
            </Link>
          </Typography.Paragraph>
          <Typography.Paragraph className="!mb-0 text-center">
            <Link to="/" className="text-muted-foreground hover:text-foreground hover:underline">
              {t("auth.homeLink", { defaultValue: "Trang chủ" })}
            </Link>
          </Typography.Paragraph>
        </Card>
      </div>
    </div>
  );
};

export default RegisterPage;
