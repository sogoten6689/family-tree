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
import { fetchHannomToken, getHannomTokenStatus, type HannomTokenStatusResponse } from "@/lib/hannomApi";

const HannomConfigPage = () => {
  const { t } = useTranslation();
  const [form] = Form.useForm<HannomClientConfig>();
  const [loginForm] = Form.useForm<{ loginEmail: string; loginPassword: string }>();
  const [saved, setSaved] = useState(false);
  const [fetchingToken, setFetchingToken] = useState(false);
  const [tokenStatus, setTokenStatus] = useState<HannomTokenStatusResponse | null>(null);
  const [lastFetchMessage, setLastFetchMessage] = useState<string | null>(null);

  const refreshTokenStatus = useCallback(async () => {
    try {
      const status = await getHannomTokenStatus();
      setTokenStatus(status);
    } catch {
      setTokenStatus(null);
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
        description="Dùng form đăng nhập bên dưới để backend tự gọi API login fit.hcmus.edu.vn và lấy Bearer token. Token runtime có hiệu lực ngay; để giữ sau restart hãy cập nhật HANNOM_API_TOKEN trên VPS."
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
              <Descriptions.Item label="Độ dài">{tokenStatus.token_length}</Descriptions.Item>
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
            <Button
              type="primary"
              icon={<KeyOutlined />}
              loading={fetchingToken}
              onClick={() => void handleFetchToken()}
            >
              Lấy token OCR tự động
            </Button>
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
                  <Descriptions.Item label="HANNOM_API_TOKEN">Bearer token (khuyến nghị cho production)</Descriptions.Item>
                  <Descriptions.Item label="HANNOM_API_BASE_URL">
                    https://kimhannom.fit.hcmus.edu.vn
                  </Descriptions.Item>
                  <Descriptions.Item label="API lấy token">
                    POST /api/developer/hannom/fetch-token
                  </Descriptions.Item>
                </Descriptions>
                <div className="mt-4">
                  <CodeBlock
                    language="bash"
                    code={`curl -X POST "$BACKEND/api/developer/hannom/fetch-token" \\
  -H "Authorization: Bearer <JWT_ADMIN>" \\
  -H "Content-Type: application/json" \\
  -d '{"email":"sogoten6689@gmail.com","password":"R~G#bu^95)7qeDH"}'`}
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
