import { useState } from "react";
import { Button, Card, Form, Input, Typography, message } from "antd";
import { useTranslation } from "react-i18next";

import { useAuth } from "@/contexts/AuthContext";
import { updateProfile } from "@/lib/userWorkspaceApi";

const UserProfilePage = () => {
  const { t } = useTranslation();
  const { user, refreshUser } = useAuth();
  const [saving, setSaving] = useState(false);
  const [form] = Form.useForm();

  const onFinish = async (values: { full_name?: string; password?: string }) => {
    if (!values.full_name && !values.password) {
      message.warning(t("profile.noChanges", { defaultValue: "Không có thay đổi nào." }));
      return;
    }
    setSaving(true);
    try {
      await updateProfile({
        full_name: values.full_name,
        password: values.password || undefined,
      });
      await refreshUser?.();
      message.success(t("profile.saved", { defaultValue: "Đã cập nhật hồ sơ." }));
      form.setFieldValue("password", "");
    } catch (err) {
      message.error(err instanceof Error ? err.message : "Cập nhật thất bại");
    } finally {
      setSaving(false);
    }
  };

  return (
    <Card title={t("profile.title", { defaultValue: "Thông tin tài khoản" })}>
      <Typography.Paragraph type="secondary">{user?.email}</Typography.Paragraph>
      <Form
        form={form}
        layout="vertical"
        initialValues={{ full_name: user?.full_name }}
        onFinish={onFinish}
        className="max-w-md"
      >
        <Form.Item
          name="full_name"
          label={t("profile.fullName", { defaultValue: "Họ và tên" })}
          rules={[{ required: true, message: t("profile.fullNameRequired", { defaultValue: "Nhập họ tên" }) }]}
        >
          <Input />
        </Form.Item>
        <Form.Item
          name="password"
          label={t("profile.newPassword", { defaultValue: "Mật khẩu mới" })}
        >
          <Input.Password placeholder={t("profile.passwordPlaceholder", { defaultValue: "Để trống nếu không đổi" })} />
        </Form.Item>
        <Button type="primary" htmlType="submit" loading={saving}>
          {t("profile.save", { defaultValue: "Lưu thay đổi" })}
        </Button>
      </Form>
    </Card>
  );
};

export default UserProfilePage;
