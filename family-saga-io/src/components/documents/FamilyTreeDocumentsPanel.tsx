import { useCallback, useEffect, useState } from "react";
import { Button, Empty, Form, Input, Modal, Select, Spin, Table, Tag } from "antd";
import { EditOutlined, PlusOutlined, ReloadOutlined } from "@ant-design/icons";
import { useNavigate } from "react-router-dom";

import { DOCUMENT_TYPE_OPTIONS, getDocumentTypeLabel } from "@/components/documents/constants";
import { ApiError } from "@/lib/apiClient";
import { createTreeDocument, listTreeDocuments } from "@/lib/documentApi";
import type { DocumentType, FamilyTreeSourceDocument } from "@/types/document";

type Props = {
  treeId: string;
};

type CreateFormValues = {
  title: string;
  description?: string;
  type: DocumentType;
};

export function FamilyTreeDocumentsPanel({ treeId }: Props) {
  const navigate = useNavigate();
  const [documents, setDocuments] = useState<FamilyTreeSourceDocument[]>([]);
  const [loading, setLoading] = useState(false);
  const [creating, setCreating] = useState(false);
  const [modalOpen, setModalOpen] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [form] = Form.useForm<CreateFormValues>();

  const loadDocuments = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const response = await listTreeDocuments(treeId);
      setDocuments(response.items);
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Không thể tải danh sách tài liệu.");
    } finally {
      setLoading(false);
    }
  }, [treeId]);

  useEffect(() => {
    void loadDocuments();
  }, [loadDocuments]);

  const handleCreate = async (values: CreateFormValues) => {
    setCreating(true);
    setError(null);
    try {
      const created = await createTreeDocument(treeId, values);
      setModalOpen(false);
      form.resetFields();
      await loadDocuments();
      navigate(`/admin/documents/${created.id}/edit`);
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Không thể tạo tài liệu.");
    } finally {
      setCreating(false);
    }
  };

  return (
    <div className="space-y-4">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div className="text-sm text-muted-foreground">
          Quản lý tài liệu đính kèm cho cây gia phả này.
        </div>
        <div className="flex gap-2">
          <Button icon={<ReloadOutlined />} onClick={() => void loadDocuments()} loading={loading}>
            Tải lại
          </Button>
          <Button type="primary" icon={<PlusOutlined />} onClick={() => setModalOpen(true)}>
            Thêm tài liệu
          </Button>
        </div>
      </div>

      {error && <div className="text-sm text-red-500">{error}</div>}

      {loading ? (
        <div className="py-10 flex justify-center">
          <Spin />
        </div>
      ) : documents.length === 0 ? (
        <Empty description="Chưa có tài liệu nào">
          <Button type="primary" onClick={() => setModalOpen(true)}>
            Tạo tài liệu đầu tiên
          </Button>
        </Empty>
      ) : (
        <Table
          rowKey="id"
          dataSource={documents}
          pagination={false}
          columns={[
            {
              title: "Tiêu đề",
              dataIndex: "title",
              render: (title: string, record) => (
                <div>
                  <div className="font-medium">{title}</div>
                  <div className="text-xs text-muted-foreground">{record.description || "Không có mô tả"}</div>
                </div>
              ),
            },
            {
              title: "Loại",
              dataIndex: "type",
              width: 160,
              render: (type: string) => <Tag>{getDocumentTypeLabel(type)}</Tag>,
            },
            {
              title: "Files",
              dataIndex: "files",
              width: 90,
              render: (files: FamilyTreeSourceDocument["files"]) => files.length,
            },
            {
              title: "",
              key: "actions",
              width: 100,
              align: "right",
              render: (_: unknown, record: FamilyTreeSourceDocument) => (
                <Button
                  type="link"
                  icon={<EditOutlined />}
                  onClick={() => navigate(`/admin/documents/${record.id}/edit`)}
                >
                  Sửa
                </Button>
              ),
            },
          ]}
        />
      )}

      <Modal
        open={modalOpen}
        title="Tạo tài liệu mới"
        onCancel={() => setModalOpen(false)}
        footer={null}
        destroyOnClose
      >
        <Form
          form={form}
          layout="vertical"
          initialValues={{ type: "van_ban" }}
          onFinish={handleCreate}
        >
          <Form.Item
            label="Tiêu đề"
            name="title"
            rules={[{ required: true, message: "Vui lòng nhập tiêu đề" }]}
          >
            <Input />
          </Form.Item>
          <Form.Item label="Mô tả" name="description">
            <Input.TextArea rows={3} />
          </Form.Item>
          <Form.Item
            label="Loại tài liệu"
            name="type"
            rules={[{ required: true, message: "Vui lòng chọn loại" }]}
          >
            <Select options={[...DOCUMENT_TYPE_OPTIONS]} />
          </Form.Item>
          <div className="flex justify-end gap-2">
            <Button onClick={() => setModalOpen(false)}>Hủy</Button>
            <Button type="primary" htmlType="submit" loading={creating}>
              Tạo & chỉnh sửa
            </Button>
          </div>
        </Form>
      </Modal>
    </div>
  );
}
