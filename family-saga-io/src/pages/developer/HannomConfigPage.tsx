import { KeyOutlined, ReloadOutlined, SaveOutlined } from "@ant-design/icons";
import {
  Alert,
  Button,
  Card,
  Descriptions,
  Form,
  Input,
  InputNumber,
  Select,
  Space,
  Tabs,
  Tag,
  Typography,
  message,
} from "antd";
import { useCallback, useEffect, useState } from "react";
import { useTranslation } from "react-i18next";

import CodeBlock from "@/components/developer/CodeBlock";
import { ApiError } from "@/lib/apiClient";
import {
  type HannomClientConfig,
  appendDeveloperLog,
  loadHannomConfig,
  saveHannomConfig,
} from "@/lib/developerSettings";
import {
  fetchHannomToken,
  getHannomCredentials,
  getHannomTokenStatus,
  saveHannomCredentials,
  type HannomCredentialsStatusResponse,
  type HannomTokenStatusResponse,
} from "@/lib/hannomApi";

const HannomConfigPage = () => {
  const { t } = useTranslation();
  const [form] = Form.useForm<HannomClientConfig>();
  const [loginForm] = Form.useForm<{ loginEmail: string; loginPassword: string }>();
  const [saved, setSaved] = useState(false);
  const [fetchingToken, setFetchingToken] = useState(false);
  const [savingCredentials, setSavingCredentials] = useState(false);
  const [tokenStatus, setTokenStatus] = useState<HannomTokenStatusResponse | null>(null);
  const [dbCredentials, setDbCredentials] = useState<HannomCredentialsStatusResponse | null>(null);
  const [lastFetchMessage, setLastFetchMessage] = useState<string | null>(null);

  const refreshTokenStatus = useCallback(async () => {
    try {
      const [status, creds] = await Promise.all([getHannomTokenStatus(), getHannomCredentials()]);
      setTokenStatus(status);
      setDbCredentials(creds);
    } catch {
      setTokenStatus(null);
      setDbCredentials(null);
    }
  }, []);

  useEffect(() => {
    const config = loadHannomConfig();
    form.setFieldsValue(config);
    loginForm.setFieldsValue({ loginEmail: config.loginEmail, loginPassword: "" });
    void refreshTokenStatus();
  }, [form, loginForm, refreshTokenStatus]);

  const handleSave = (values: HannomClientConfig) => {
    saveHannomConfig(values);
    setSaved(true);
    setTimeout(() => setSaved(false), 2000);
  };

  const handleSaveCredentials = async () => {
    const values = await loginForm.validateFields();
    setSavingCredentials(true);
    setLastFetchMessage(null);
    try {
      const result = await saveHannomCredentials({
        username: values.loginEmail,
        password: values.loginPassword,
      });
      setDbCredentials(result);
      message.success("Đã lưu tài khoản + token lên server (DB, mã hóa). Tự refresh khi hết hạn.");
      await refreshTokenStatus();
    } catch (error) {
      const detail = error instanceof Error ? error.message : "Lưu credential thất bại";
      message.error(detail);
    } finally {
      setSavingCredentials(false);
    }
  };

  const handleFetchToken = async () => {
    const values = await loginForm.validateFields();
    setFetchingToken(true);
    setLastFetchMessage(null);
    try {
      const result = await fetchHannomToken({
        email: values.loginEmail,
        password: values.loginPassword,
      });
      form.setFieldValue("apiToken", result.token);
      saveHannomConfig({
        ...loadHannomConfig(),
        ...form.getFieldsValue(),
        loginEmail: values.loginEmail,
        apiToken: result.token,
      });
      setLastFetchMessage(result.message);
      message.success(`Đã lấy token (${result.source}) qua ${result.login_path}`);
      appendDeveloperLog({
        method: "POST",
        path: "/api/developer/hannom/fetch-token",
        status: 200,
        message: `Token OK · ${result.token_preview} · ${result.login_path}`,
      });
      await refreshTokenStatus();
    } catch (error) {
      const status = error instanceof ApiError ? error.status : 500;
      const detail = error instanceof Error ? error.message : "Lấy token thất bại";
      message.error(detail);
      appendDeveloperLog({
        method: "POST",
        path: "/api/developer/hannom/fetch-token",
        status,
        message: detail,
      });
    } finally {
      setFetchingToken(false);
    }
  };

  return (
    <Space direction="vertical" size="large" className="w-full">
      <Alert
        type="info"
        showIcon
        message="Token OCR Kim Hán Nôm"
        description="Backend lưu username/password/token trên MySQL (mã hóa), tự đăng nhập lại khi JWT hết hạn. Ưu tiên dùng「Lưu lên server (DB)」trên VPS production."
      />

      <Card
        title="Đăng nhập & lấy token tự động"
        extra={
          <Button icon={<ReloadOutlined />} onClick={() => void refreshTokenStatus()}>
            Trạng thái token
          </Button>
        }
      >
        <Space direction="vertical" size="middle" className="w-full">
          {tokenStatus && (
            <Descriptions bordered size="small" column={2}>
              <Descriptions.Item label="Đã cấu hình">
                <Tag color={tokenStatus.configured ? "green" : "red"}>
                  {tokenStatus.configured ? "Có" : "Chưa"}
                </Tag>
              </Descriptions.Item>
              <Descriptions.Item label="Nguồn">{tokenStatus.source}</Descriptions.Item>
              <Descriptions.Item label="Preview">{tokenStatus.preview ?? "—"}</Descriptions.Item>
              <Descriptions.Item label="Hết hạn">{tokenStatus.expires_at ?? "—"}</Descriptions.Item>
              <Descriptions.Item label="Độ dài">{tokenStatus.token_length}</Descriptions.Item>
            </Descriptions>
          )}

          {dbCredentials && (
            <Descriptions bordered size="small" column={2} title="Credential trên server (DB)">
              <Descriptions.Item label="Username">{dbCredentials.username ?? "—"}</Descriptions.Item>
              <Descriptions.Item label="Có password">
                <Tag color={dbCredentials.has_password ? "green" : "default"}>
                  {dbCredentials.has_password ? "Có" : "Chưa"}
                </Tag>
              </Descriptions.Item>
              <Descriptions.Item label="Token preview">{dbCredentials.token_preview ?? "—"}</Descriptions.Item>
              <Descriptions.Item label="Hết hạn">{dbCredentials.token_expires_at ?? "—"}</Descriptions.Item>
              {dbCredentials.last_error && (
                <Descriptions.Item label="Lỗi gần nhất" span={2}>
                  <Typography.Text type="danger">{dbCredentials.last_error}</Typography.Text>
                </Descriptions.Item>
              )}
            </Descriptions>
          )}

          <Form form={loginForm} layout="vertical">
            <Form.Item
              name="loginEmail"
              label="Email / Tên đăng nhập Kim Hán Nôm"
              rules={[{ required: true, message: "Nhập email hoặc tên đăng nhập" }]}
            >
              <Input placeholder="email@example.com" autoComplete="username" />
            </Form.Item>
            <Form.Item
              name="loginPassword"
              label="Mật khẩu"
              rules={[{ required: true, message: "Nhập mật khẩu Kim Hán Nôm" }]}
            >
              <Input.Password placeholder="Mật khẩu tài khoản kimhannom.fit.hcmus.edu.vn" autoComplete="current-password" />
            </Form.Item>
            <Space wrap>
              <Button
                type="primary"
                icon={<SaveOutlined />}
                loading={savingCredentials}
                onClick={() => void handleSaveCredentials()}
              >
                Lưu lên server (DB)
              </Button>
              <Button
                icon={<KeyOutlined />}
                loading={fetchingToken}
                onClick={() => void handleFetchToken()}
              >
                Lấy token (runtime)
              </Button>
            </Space>
          </Form>

          {lastFetchMessage && <Alert type="success" showIcon message={lastFetchMessage} />}
        </Space>
      </Card>

      <Tabs
        items={[
          {
            key: "config",
            label: "Cấu hình API",
            children: (
              <Card title="Kim Hán Nôm API (fit.hcmus.edu.vn)">
                <Form form={form} layout="vertical" onFinish={handleSave}>
                  <Form.Item
                    name="apiToken"
                    label="Bearer Token (HANNOM_API_TOKEN)"
                    extra="Điền thủ công hoặc dùng nút Lấy token ở trên."
                  >
                    <Input.Password placeholder="Bearer token" />
                  </Form.Item>

                  <Space wrap className="w-full">
                    <Form.Item name="ocrId" label="ocr_id" tooltip="1: dọc thông thường">
                      <InputNumber min={1} max={10} />
                    </Form.Item>
                    <Form.Item
                      name="ocrLangType"
                      label="lang_type (OCR)"
                      tooltip="0: chưa biết, 1: Hán, 2: Nôm"
                    >
                      <InputNumber min={0} max={2} />
                    </Form.Item>
                    <Form.Item name="fontType" label="font_type">
                      <InputNumber min={0} max={5} />
                    </Form.Item>
                    <Form.Item name="transliterationLangType" label="lang_type (phiên âm)">
                      <InputNumber min={0} max={2} />
                    </Form.Item>
                    <Form.Item name="rateLimitPerMinute" label="Rate limit (req/phút)">
                      <InputNumber min={1} max={60} />
                    </Form.Item>
                  </Space>

                  <Form.Item name="modelPriority" label="Ưu tiên mô hình">
                    <Select
                      options={[
                        { value: "balanced", label: "Cân bằng (balanced)" },
                        { value: "accuracy", label: "Độ chính xác (accuracy)" },
                        { value: "speed", label: "Tốc độ (speed)" },
                      ]}
                    />
                  </Form.Item>

                  <Button type="primary" htmlType="submit" icon={<SaveOutlined />}>
                    {saved
                      ? t("common.saved", { defaultValue: "Đã lưu" })
                      : t("common.save", { defaultValue: "Lưu cấu hình" })}
                  </Button>
                </Form>
              </Card>
            ),
          },
          {
            key: "env",
            label: "Biến môi trường Server",
            children: (
              <Card title="Backend (.env / docker-compose)">
                <Descriptions bordered column={1} size="small">
                  <Descriptions.Item label="HANNOM_EMAIL / HANNOM_PASSWORD">
                    Tài khoản đăng nhập (tùy chọn, dùng khi gọi fetch-token không gửi body)
                  </Descriptions.Item>
                  <Descriptions.Item label="PUT /api/developer/hannom/credentials">
                    Lưu username/password → login → token (DB, mã hóa, auto refresh)
                  </Descriptions.Item>
                  <Descriptions.Item label="POST /api/developer/hannom/fetch-token">
                    Lấy token runtime (+ lưu DB nếu có MySQL)
                  </Descriptions.Item>
                  <Descriptions.Item label="HANNOM_API_TOKEN">Override env (ưu tiên hơn DB)</Descriptions.Item>
                </Descriptions>
                <div className="mt-4">
                  <CodeBlock
                    language="bash"
                    code={`curl -X PUT "$BACKEND/api/developer/hannom/credentials" \\
  -H "Authorization: Bearer <JWT_ADMIN>" \\
  -H "Content-Type: application/json" \\
  -d '{"username":"email@example.com","password":"<PASSWORD>"}'`}
                  />
                </div>
                <Typography.Paragraph type="secondary" className="mt-4 !mb-0">
                  Sau khi cập nhật trên VPS: <Typography.Text code>docker compose up -d --build backend</Typography.Text>
                </Typography.Paragraph>
              </Card>
            ),
          },
        ]}
      />
    </Space>
  );
};

export default HannomConfigPage;
