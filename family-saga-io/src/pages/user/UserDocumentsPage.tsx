import { useEffect, useState } from "react";
import { Button, Card, Space, Table, Tag, Typography, message } from "antd";
import { EyeOutlined } from "@ant-design/icons";
import { useNavigate } from "react-router-dom";
import { useTranslation } from "react-i18next";

import { listUserDocuments, type UserScan } from "@/lib/userWorkspaceApi";

const ocrColor: Record<string, string> = {
  pending: "default",
  processing: "processing",
  completed: "success",
  failed: "error",
  skipped: "warning",
};

const treeColor: Record<string, string> = {
  none: "default",
  draft: "processing",
  created: "success",
};

const UserDocumentsPage = () => {
  const { t } = useTranslation();
  const navigate = useNavigate();
  const [items, setItems] = useState<UserScan[]>([]);
  const [loading, setLoading] = useState(true);

  const load = async () => {
    setLoading(true);
    try {
      const data = await listUserDocuments();
      setItems(data.items);
    } catch (err) {
      message.error(err instanceof Error ? err.message : "Không tải được danh sách tài liệu");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    void load();
  }, []);

  return (
    <Card>
      <Space className="w-full justify-between mb-4">
        <Typography.Title level={4} className="!mb-0">
          {t("userDocuments.title", { defaultValue: "Tài liệu đã scan" })}
        </Typography.Title>
        <Button type="primary" onClick={() => navigate("/user/document-reader")}>
          {t("userDocuments.uploadNew", { defaultValue: "Upload mới" })}
        </Button>
      </Space>

      <Table
        rowKey="id"
        loading={loading}
        dataSource={items}
        pagination={{ pageSize: 10 }}
        columns={[
          {
            title: "STT",
            width: 70,
            render: (_, __, index) => index + 1,
          },
          {
            title: t("userDocuments.name", { defaultValue: "Tên tài liệu" }),
            dataIndex: "title",
          },
          {
            title: t("userDocuments.fileType", { defaultValue: "Loại file" }),
            dataIndex: "file_type",
          },
          {
            title: t("userDocuments.pages", { defaultValue: "Số trang" }),
            dataIndex: "page_count",
          },
          {
            title: t("userDocuments.uploadedAt", { defaultValue: "Ngày upload" }),
            dataIndex: "uploaded_at",
            render: (value: string) => new Date(value).toLocaleString("vi-VN"),
          },
          {
            title: t("userDocuments.ocrStatus", { defaultValue: "Trạng thái OCR" }),
            dataIndex: "ocr_status",
            render: (value: string) => <Tag color={ocrColor[value] ?? "default"}>{value}</Tag>,
          },
          {
            title: t("userDocuments.treeStatus", { defaultValue: "Trạng thái gia phả" }),
            dataIndex: "tree_status",
            render: (value: string) => <Tag color={treeColor[value] ?? "default"}>{value}</Tag>,
          },
          {
            title: t("auth.actions", { defaultValue: "Thao tác" }),
            render: (_, record) => (
              <Button icon={<EyeOutlined />} onClick={() => navigate(`/user/documents/${record.id}`)}>
                {t("userDocuments.viewDetail", { defaultValue: "Chi tiết" })}
              </Button>
            ),
          },
        ]}
      />
    </Card>
  );
};

export default UserDocumentsPage;
