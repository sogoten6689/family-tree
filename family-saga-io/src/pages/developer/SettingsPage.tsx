import { DeleteOutlined, KeyOutlined, PlusOutlined, SaveOutlined } from "@ant-design/icons";
import { Alert, Button, Card, Empty, Form, Input, Popconfirm, Space, Table, Tag, Typography, message } from "antd";
import { useCallback, useEffect, useState } from "react";

import { GeminiUsageCard } from "@/components/settings/GeminiUsageCard";
import { OcrEnginesCard, TextEnginesCard } from "@/components/settings/OcrEnginesCard";
import { deleteSetting, listSettings, upsertSetting, type SettingItem } from "@/lib/settingsApi";

const SettingsPage = () => {
  const [items, setItems] = useState<SettingItem[]>([]);
  const [loading, setLoading] = useState(false);
  const [drafts, setDrafts] = useState<Record<string, string>>({});
  const [savingKey, setSavingKey] = useState<string | null>(null);
  const [deletingKey, setDeletingKey] = useState<string | null>(null);
  const [newKeyForm] = Form.useForm<{ key: string; value: string }>();

  const refresh = useCallback(async () => {
    setLoading(true);
    try {
      const rows = await listSettings();
      setItems(rows);
    } catch (error) {
      message.error(error instanceof Error ? error.message : "Không tải được danh sách config");
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    void refresh();
  }, [refresh]);

  const handleSave = async (key: string) => {
    const value = (drafts[key] ?? "").trim();
    if (!value) {
      message.warning("Nhập giá trị trước khi lưu");
      return;
    }
    setSavingKey(key);
    try {
      await upsertSetting(key, value);
      message.success(`Đã lưu "${key}" (mã hoá trong DB)`);
      setDrafts((prev) => ({ ...prev, [key]: "" }));
      await refresh();
    } catch (error) {
      message.error(error instanceof Error ? error.message : "Lưu thất bại");
    } finally {
      setSavingKey(null);
    }
  };

  const handleDelete = async (key: string) => {
    setDeletingKey(key);
    try {
      await deleteSetting(key);
      message.success(`Đã xoá "${key}"`);
      await refresh();
    } catch (error) {
      message.error(error instanceof Error ? error.message : "Xoá thất bại");
    } finally {
      setDeletingKey(null);
    }
  };

  const handleAddNew = async (values: { key: string; value: string }) => {
    const key = values.key.trim();
    const value = values.value.trim();
    if (!key || !value) return;
    setSavingKey(key);
    try {
      await upsertSetting(key, value);
      message.success(`Đã lưu "${key}"`);
      newKeyForm.resetFields();
      await refresh();
    } catch (error) {
      message.error(error instanceof Error ? error.message : "Lưu thất bại");
    } finally {
      setSavingKey(null);
    }
  };

  const columns = [
    {
      title: "Key",
      dataIndex: "key",
      render: (key: string) => (
        <Typography.Text code>
          <KeyOutlined /> {key}
        </Typography.Text>
      ),
    },
    {
      title: "Trạng thái",
      dataIndex: "configured",
      width: 140,
      render: (configured: boolean) => (
        <Tag color={configured ? "green" : "default"}>{configured ? "Đã cấu hình" : "Chưa cấu hình"}</Tag>
      ),
    },
    {
      title: "Giá trị hiện tại",
      dataIndex: "masked_value",
      render: (masked: string | null) =>
        masked ? <Typography.Text type="secondary">{masked}</Typography.Text> : <Typography.Text type="secondary">—</Typography.Text>,
    },
    {
      title: "Cập nhật lúc",
      dataIndex: "updated_at",
      width: 200,
      render: (value: string | null) => value ?? "—",
    },
    {
      title: "Đổi giá trị",
      key: "action",
      width: 360,
      render: (_: unknown, record: SettingItem) => (
        <Space.Compact className="w-full">
          <Input.Password
            placeholder={record.configured ? "Nhập giá trị mới để thay thế" : "Nhập giá trị"}
            value={drafts[record.key] ?? ""}
            onChange={(e) => setDrafts((prev) => ({ ...prev, [record.key]: e.target.value }))}
            onPressEnter={() => void handleSave(record.key)}
          />
          <Button
            type="primary"
            icon={<SaveOutlined />}
            loading={savingKey === record.key}
            onClick={() => void handleSave(record.key)}
          />
          {record.configured && (
            <Popconfirm
              title={`Xoá config "${record.key}"?`}
              okText="Xoá"
              cancelText="Huỷ"
              onConfirm={() => void handleDelete(record.key)}
            >
              <Button danger icon={<DeleteOutlined />} loading={deletingKey === record.key} />
            </Popconfirm>
          )}
        </Space.Compact>
      ),
    },
  ];

  return (
    <Space direction="vertical" size="large" className="w-full">
      <Alert
        type="info"
        showIcon
        message="Cấu hình key-value hệ thống"
        description="Lưu API key/secret vào MySQL (mã hoá), dùng lấy ra ngay khi backend cần — không phải sửa .env + restart server. Ví dụ: GOOGLE_API_KEY cho Gemini (trích xuất quan hệ nhân vật → cây gia phả)."
      />

      <OcrEnginesCard onSaved={() => void refresh()} />

      <TextEnginesCard onSaved={() => void refresh()} />

      <GeminiUsageCard />

      <Card title="Danh sách config">
        <Table scroll={{ x: "max-content" }}
          rowKey="key"
          loading={loading}
          columns={columns}
          dataSource={items}
          pagination={false}
          locale={{ emptyText: <Empty description="Chưa có config nào" /> }}
        />
      </Card>

      <Card title="Thêm key mới">
        <Form form={newKeyForm} layout="inline" onFinish={handleAddNew}>
          <Form.Item name="key" rules={[{ required: true, message: "Nhập tên key" }]}>
            <Input placeholder="TEN_KEY_VIET_HOA" style={{ width: 240 }} />
          </Form.Item>
          <Form.Item name="value" rules={[{ required: true, message: "Nhập giá trị" }]}>
            <Input.Password placeholder="Giá trị" style={{ width: 280 }} />
          </Form.Item>
          <Form.Item>
            <Button type="primary" htmlType="submit" icon={<PlusOutlined />}>
              Thêm
            </Button>
          </Form.Item>
        </Form>
      </Card>
    </Space>
  );
};

export default SettingsPage;
