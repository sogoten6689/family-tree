import { useEffect, useState } from "react";
import { Button, Card, Space, Table, Tag, Typography } from "antd";
import { EyeOutlined, PlusOutlined } from "@ant-design/icons";
import { useNavigate } from "react-router-dom";
import { useTranslation } from "react-i18next";

import { PageState } from "@/components/ui/PageState";
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
  const [error, setError] = useState<string | null>(null);

  const load = async () => {
    setLoading(true);
    setError(null);
    try {
      const data = await listUserDocuments();
      setItems(data.items);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Không tải được danh sách tài liệu");
      setItems([]);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    void load();
  }, []);

  const emptyAction = (
    <Button type="primary" icon={<PlusOutlined />} onClick={() => navigate("/user/document-reader")}>
      {t("userDocuments.uploadNew", { defaultValue: "Upload mới" })}
    </Button>
  );

  return (
    <Card>
      <Space className="w-full justify-between mb-4 flex-wrap">
        <Typography.Title level={4} className="!mb-0">
          {t("userDocuments.title", { defaultValue: "Tài liệu đã scan" })}
        </Typography.Title>
        <Button type="primary" onClick={() => navigate("/user/document-reader")}>
          {t("userDocuments.uploadNew", { defaultValue: "Upload mới" })}
        </Button>
      </Space>

      <PageState
        loading={loading}
        error={error}
        onRetry={load}
        empty={!loading && !error && items.length === 0}
        emptyDescription={t("userDocuments.empty", { defaultValue: "Chưa có tài liệu nào. Hãy upload tài liệu gia phả đầu tiên." })}
        emptyAction={emptyAction}
      >
        <Table
          rowKey="id"
          dataSource={items}
          pagination={{ pageSize: 10, showSizeChanger: false }}
          scroll={{ x: 800 }}
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
      </PageState>
    </Card>
  );
};

export default UserDocumentsPage;
