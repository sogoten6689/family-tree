import { useEffect, useState } from "react";
import { Alert, Button, List, Modal, Space, Spin, Table, Typography } from "antd";
import { EyeOutlined, PlusOutlined, UndoOutlined } from "@ant-design/icons";
import { useNavigate } from "react-router-dom";
import { useTranslation } from "react-i18next";

import { OcrStatusTag, TreeStatusTag } from "@/components/flow/StatusTags";
import { PageState } from "@/components/ui/PageState";
import { useAuth } from "@/contexts/AuthContext";
import {
  listDeletedDocuments,
  listUserDocuments,
  restoreUserDocument,
  type DeletedScan,
  type UserScan,
} from "@/lib/userWorkspaceApi";

const UserDocumentsPage = () => {
  const { t } = useTranslation();
  const navigate = useNavigate();
  const [items, setItems] = useState<UserScan[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const { isAdmin } = useAuth();
  const [trashOpen, setTrashOpen] = useState(false);
  const [trash, setTrash] = useState<DeletedScan[] | null>(null);
  const [trashError, setTrashError] = useState<string | null>(null);
  const [trashBusy, setTrashBusy] = useState<number | null>(null);

  const openTrash = () => {
    setTrashOpen(true);
    setTrash(null);
    setTrashError(null);
    listDeletedDocuments()
      .then((data) => setTrash(data.items))
      .catch((err) => setTrashError(err instanceof Error ? err.message : "Không tải được tài liệu đã xoá"));
  };

  const restore = async (item: DeletedScan) => {
    setTrashBusy(item.id);
    setTrashError(null);
    try {
      await restoreUserDocument(item.id);
      setTrash((prev) => (prev ?? []).filter((d) => d.id !== item.id));
      void load();
    } catch (err) {
      setTrashError(err instanceof Error ? err.message : "Không khôi phục được tài liệu");
    } finally {
      setTrashBusy(null);
    }
  };

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
    <Button type="primary" icon={<PlusOutlined />} onClick={() => navigate("/user/documents/new")}>
      {t("userDocuments.uploadNew", { defaultValue: "Upload mới" })}
    </Button>
  );

  return (
    <div>
      <Space className="w-full justify-between mb-4 flex-wrap">
        <Typography.Title level={4} className="!mb-0">
          {t("userDocuments.title", { defaultValue: "Tài liệu đã scan" })}
        </Typography.Title>
        <Space>
          {isAdmin && (
            <Button icon={<UndoOutlined />} onClick={openTrash}>
              {t("userDocuments.trash", { defaultValue: "Đã xoá" })}
            </Button>
          )}
          <Button type="primary" icon={<PlusOutlined />} onClick={() => navigate("/user/documents/new")}>
            {t("userDocuments.uploadNew", { defaultValue: "Upload mới" })}
          </Button>
        </Space>
      </Space>
      <Modal
        open={trashOpen}
        title={t("userDocuments.trashTitle", { defaultValue: "Tài liệu đã xoá" })}
        footer={null}
        onCancel={() => setTrashOpen(false)}
        destroyOnHidden
      >
        {trashError && <Alert type="error" showIcon message={trashError} className="mb-3" />}
        {trash === null && !trashError ? (
          <Spin className="flex justify-center py-6" />
        ) : (
          <List
            dataSource={trash ?? []}
            locale={{ emptyText: t("userDocuments.trashEmpty", { defaultValue: "Không có tài liệu nào đã xoá." }) }}
            renderItem={(item) => (
              <List.Item
                actions={[
                  <Button
                    key="restore"
                    size="small"
                    type="primary"
                    loading={trashBusy === item.id}
                    onClick={() => void restore(item)}
                  >
                    {t("pageViewer.restore", { defaultValue: "Khôi phục" })}
                  </Button>,
                ]}
              >
                <List.Item.Meta
                  title={item.title}
                  description={[item.ma_dinh_danh, `${item.page_count} trang`].filter(Boolean).join(" · ")}
                />
              </List.Item>
            )}
          />
        )}
      </Modal>

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
              title: t("userDocuments.ocrStatusLabel", { defaultValue: "Trạng thái OCR" }),
              dataIndex: "ocr_status",
              render: (value: UserScan["ocr_status"]) => <OcrStatusTag status={value} />,
            },
            {
              title: t("userDocuments.treeStatusLabel", { defaultValue: "Trạng thái gia phả" }),
              dataIndex: "tree_status",
              render: (value: UserScan["tree_status"]) => <TreeStatusTag status={value} />,
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
    </div>
  );
};

export default UserDocumentsPage;
