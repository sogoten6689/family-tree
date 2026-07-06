import { useEffect, useMemo, useState } from "react";
import { Alert, Button, Card, Form, Input, Select, Spin } from "antd";
import { toast } from "sonner";

import { DocumentFileDropzone } from "@/components/documents/DocumentFileDropzone";
import { DocumentFileList } from "@/components/documents/DocumentFileList";
import { DocumentOcrPanel } from "@/components/documents/DocumentOcrPanel";
import { DOCUMENT_TYPE_OPTIONS, sortDocumentFiles } from "@/components/documents/constants";
import { ApiError } from "@/lib/apiClient";
import {
  deleteDocumentFile,
  reorderDocumentFiles,
  updateDocument,
  uploadDocumentFiles,
} from "@/lib/documentApi";
import type { DocumentFile, DocumentType, FamilyTreeSourceDocument } from "@/types/document";

type FormValues = {
  title: string;
  description?: string;
  type: DocumentType;
};

type Props = {
  document: FamilyTreeSourceDocument;
  onUpdated: (document: FamilyTreeSourceDocument) => void;
  onCancel: () => void;
};

export function EditDocumentForm({ document, onUpdated, onCancel }: Props) {
  const [form] = Form.useForm<FormValues>();
  const [files, setFiles] = useState<DocumentFile[]>(() => sortDocumentFiles(document.files));
  const [saving, setSaving] = useState(false);
  const [uploading, setUploading] = useState(false);
  const [reordering, setReordering] = useState(false);
  const [deletingFileId, setDeletingFileId] = useState<number | null>(null);
  const [error, setError] = useState<string | null>(null);

  const initialValues = useMemo<FormValues>(
    () => ({
      title: document.title,
      description: document.description ?? undefined,
      type: document.type,
    }),
    [document],
  );

  useEffect(() => {
    form.setFieldsValue(initialValues);
    setFiles(sortDocumentFiles(document.files));
  }, [document, form, initialValues]);

  const handleSave = async (values: FormValues) => {
    setSaving(true);
    setError(null);
    try {
      const updated = await updateDocument(document.id, {
        title: values.title,
        description: values.description ?? null,
        type: values.type,
      });
      onUpdated(updated);
      toast.success("Đã lưu thay đổi tài liệu.");
    } catch (err) {
      const message = err instanceof ApiError ? err.message : "Không thể lưu tài liệu.";
      setError(message);
      toast.error(message);
    } finally {
      setSaving(false);
    }
  };

  const handleUpload = async (selectedFiles: File[]) => {
    setUploading(true);
    setError(null);
    try {
      const response = await uploadDocumentFiles(document.id, selectedFiles);
      const merged = sortDocumentFiles([...files, ...response.uploaded]);
      setFiles(merged);
      onUpdated({ ...document, files: merged });
      toast.success(`Đã upload ${response.uploaded.length} file.`);
    } catch (err) {
      const message = err instanceof ApiError ? err.message : "Upload thất bại.";
      setError(message);
      toast.error(message);
    } finally {
      setUploading(false);
    }
  };

  const handleReorder = async (nextFiles: DocumentFile[]) => {
    setFiles(nextFiles);
    setReordering(true);
    setError(null);
    try {
      const updated = await reorderDocumentFiles(document.id, {
        files: nextFiles.map((item, index) => ({ id: item.id, position: index })),
      });
      const sorted = sortDocumentFiles(updated.files);
      setFiles(sorted);
      onUpdated(updated);
      toast.success("Đã cập nhật thứ tự file.");
    } catch (err) {
      setFiles(sortDocumentFiles(document.files));
      const message = err instanceof ApiError ? err.message : "Không thể sắp xếp lại file.";
      setError(message);
      toast.error(message);
    } finally {
      setReordering(false);
    }
  };

  const handleDeleteFile = async (fileId: number) => {
    setDeletingFileId(fileId);
    setError(null);
    try {
      const updated = await deleteDocumentFile(document.id, fileId);
      const sorted = sortDocumentFiles(updated.files);
      setFiles(sorted);
      onUpdated(updated);
      toast.success("Đã xóa file.");
    } catch (err) {
      const message = err instanceof ApiError ? err.message : "Không thể xóa file.";
      setError(message);
      toast.error(message);
    } finally {
      setDeletingFileId(null);
    }
  };

  return (
    <div className="space-y-6">
      {error && <Alert type="error" showIcon message={error} />}

      <Card title="Thông tin tài liệu">
        <Form
          form={form}
          layout="vertical"
          initialValues={initialValues}
          onFinish={handleSave}
        >
          <Form.Item
            label="Tiêu đề"
            name="title"
            rules={[{ required: true, message: "Vui lòng nhập tiêu đề" }]}
          >
            <Input placeholder="Nhập tiêu đề tài liệu" />
          </Form.Item>

          <Form.Item label="Mô tả" name="description">
            <Input.TextArea rows={4} placeholder="Mô tả ngắn về tài liệu" />
          </Form.Item>

          <Form.Item
            label="Loại tài liệu"
            name="type"
            rules={[{ required: true, message: "Vui lòng chọn loại tài liệu" }]}
          >
            <Select options={[...DOCUMENT_TYPE_OPTIONS]} />
          </Form.Item>

          <div className="flex flex-wrap gap-3">
            <Button type="primary" htmlType="submit" loading={saving}>
              Lưu thay đổi
            </Button>
            <Button onClick={onCancel} disabled={saving || uploading || reordering}>
              Hủy
            </Button>
          </div>
        </Form>
      </Card>

      <Card title="Danh sách file">
        <DocumentFileList
          files={files}
          reordering={reordering}
          deletingFileId={deletingFileId}
          onReorder={handleReorder}
          onDelete={handleDeleteFile}
        />
      </Card>

      <DocumentOcrPanel document={{ ...document, files }} />

      <Card title="Thêm file mới">
        {uploading ? (
          <div className="py-8 flex justify-center">
            <Spin tip="Đang upload..." />
          </div>
        ) : (
          <DocumentFileDropzone uploading={uploading} onUpload={handleUpload} />
        )}
      </Card>
    </div>
  );
}
