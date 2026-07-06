import { useEffect, useMemo, useState } from "react";
import {
  Alert,
  Button,
  Card,
  Divider,
  Select,
  Space,
  Spin,
  Typography,
  Upload,
} from "antd";
import type { UploadProps } from "antd";
import {
  CloudUploadOutlined,
  CopyOutlined,
  FileSearchOutlined,
  LinkOutlined,
} from "@ant-design/icons";
import { useNavigate } from "react-router-dom";
import { toast } from "sonner";

import { OCR_ELIGIBLE_DOCUMENT_TYPES } from "@/components/documents/constants";
import { ApiError } from "@/lib/apiClient";
import { ocrTransliterateDocument } from "@/lib/documentApi";
import type { DocumentFile, FamilyTreeSourceDocument, OcrTransliterateResponse } from "@/types/document";

type Props = {
  document: FamilyTreeSourceDocument;
};

async function fetchImageFile(docFile: DocumentFile): Promise<File> {
  if (!docFile.download_url) {
    throw new Error(`File "${docFile.file_name}" chưa có URL tải. Vui lòng tải lại trang.`);
  }

  const response = await fetch(docFile.download_url);
  if (!response.ok) {
    throw new Error(`Không tải được file "${docFile.file_name}" (${response.status}).`);
  }

  const blob = await response.blob();
  return new File([blob], docFile.file_name, {
    type: blob.type || docFile.file_type || "image/jpeg",
  });
}

const copyText = async (text: string, label: string) => {
  try {
    await navigator.clipboard.writeText(text);
    toast.success(`Đã copy ${label}.`);
  } catch {
    toast.error("Không thể copy vào clipboard.");
  }
};

export function DocumentOcrPanel({ document }: Props) {
  const navigate = useNavigate();
  const [selectedFileId, setSelectedFileId] = useState<number | null>(null);
  const [pendingUpload, setPendingUpload] = useState<File | null>(null);
  const [running, setRunning] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [result, setResult] = useState<OcrTransliterateResponse | null>(null);

  const imageFiles = useMemo(
    () => document.files.filter((file) => file.file_type.startsWith("image/")),
    [document.files],
  );

  useEffect(() => {
    if (imageFiles.length > 0 && selectedFileId == null && !pendingUpload) {
      setSelectedFileId(imageFiles[0].id);
    }
  }, [imageFiles, selectedFileId, pendingUpload]);

  const eligible = OCR_ELIGIBLE_DOCUMENT_TYPES.includes(document.type);

  if (!eligible) {
    return null;
  }

  const resolveImageFile = async (): Promise<File> => {
    if (pendingUpload) return pendingUpload;

    if (selectedFileId != null) {
      const docFile = imageFiles.find((file) => file.id === selectedFileId);
      if (!docFile) {
        throw new Error("File đã chọn không còn tồn tại.");
      }
      return fetchImageFile(docFile);
    }

    throw new Error("Vui lòng chọn ảnh có sẵn hoặc upload ảnh mới để OCR.");
  };

  const handleRunOcr = async () => {
    setRunning(true);
    setError(null);
    try {
      const imageFile = await resolveImageFile();
      const response = await ocrTransliterateDocument(document.id, imageFile);
      setResult(response);
      toast.success("OCR và phiên âm thành công. Kết quả đã được lưu.");
    } catch (err) {
      const message =
        err instanceof ApiError || err instanceof Error
          ? err.message
          : "Không thể chạy OCR.";
      setError(message);
      toast.error(message);
    } finally {
      setRunning(false);
    }
  };

  const uploadProps: UploadProps = {
    accept: "image/*",
    maxCount: 1,
    showUploadList: true,
    beforeUpload: (file) => {
      setPendingUpload(file);
      setSelectedFileId(null);
      setError(null);
      return false;
    },
    onRemove: () => {
      setPendingUpload(null);
    },
  };

  return (
    <Card
      title={
        <Space>
          <FileSearchOutlined />
          OCR Hán-Nôm &amp; Phiên âm
        </Space>
      }
    >
      <Alert
        type="info"
        showIcon
        className="mb-4"
        message="Kim Hán Nôm API"
        description="Hệ thống sẽ OCR chữ Hán/Nôm từ ảnh, phiên âm sang Quốc ngữ và lưu file .txt vào tài liệu kết quả (ket_qua_van_ban). Cần cấu hình token tại Developer → Hán-Nôm Config."
      />

      {error && <Alert type="error" showIcon message={error} className="mb-4" closable onClose={() => setError(null)} />}

      <Typography.Text strong className="block mb-2">
        Chọn ảnh đã upload
      </Typography.Text>
      {imageFiles.length > 0 ? (
        <Select
          allowClear
          placeholder="Chọn ảnh trong tài liệu"
          className="w-full mb-4"
          value={pendingUpload ? undefined : selectedFileId}
          disabled={!!pendingUpload || running}
          options={imageFiles.map((file) => ({
            value: file.id,
            label: `${file.file_name} (${Math.round(file.size / 1024)} KB)`,
          }))}
          onChange={(value) => {
            setSelectedFileId(value ?? null);
            setPendingUpload(null);
            setError(null);
          }}
        />
      ) : (
        <Typography.Paragraph type="secondary" className="!mb-4">
          Chưa có ảnh nào. Upload ảnh scan ở mục bên dưới hoặc thêm file ở card &quot;Thêm file mới&quot;.
        </Typography.Paragraph>
      )}

      <Typography.Text strong className="block mb-2">
        Hoặc upload ảnh mới (chỉ dùng cho OCR)
      </Typography.Text>
      <Upload.Dragger {...uploadProps} disabled={running} className="!bg-muted/30 dark:!bg-muted/20 mb-4">
        <p className="ant-upload-drag-icon">
          <CloudUploadOutlined />
        </p>
        <Typography.Text>Kéo thả ảnh scan Hán-Nôm hoặc bấm để chọn</Typography.Text>
      </Upload.Dragger>

      <Button
        type="primary"
        icon={<FileSearchOutlined />}
        loading={running}
        disabled={!pendingUpload && selectedFileId == null}
        onClick={() => void handleRunOcr()}
      >
        Chạy OCR và lưu kết quả
      </Button>

      {running && (
        <div className="mt-4 flex items-center gap-2 text-muted-foreground">
          <Spin size="small" />
          <span>Đang gọi Kim Hán Nôm API (có thể mất 1–2 phút)...</span>
        </div>
      )}

      {result && (
        <>
          <Divider />
          <Space wrap className="mb-4">
            <Typography.Title level={5} className="!mb-0">
              Kết quả vừa lưu
            </Typography.Title>
            <Button
              size="small"
              icon={<LinkOutlined />}
              onClick={() => navigate(`/admin/documents/${result.result_document_id}/edit`)}
            >
              Mở tài liệu kết quả
            </Button>
            {result.saved_file.download_url && (
              <Button size="small" href={result.saved_file.download_url} target="_blank" rel="noreferrer">
                Tải file .txt
              </Button>
            )}
          </Space>

          <div className="space-y-4">
            <div>
              <div className="flex items-center justify-between gap-2 mb-2">
                <Typography.Text strong>Chữ Hán/Nôm (OCR)</Typography.Text>
                <Button
                  size="small"
                  icon={<CopyOutlined />}
                  onClick={() => void copyText(result.ocr_text, "OCR")}
                >
                  Copy
                </Button>
              </div>
              <Typography.Paragraph className="!mb-0 whitespace-pre-wrap rounded-lg border border-border bg-muted/40 p-3 text-sm max-h-48 overflow-auto">
                {result.ocr_text || "—"}
              </Typography.Paragraph>
            </div>

            <div>
              <div className="flex items-center justify-between gap-2 mb-2">
                <Typography.Text strong>Phiên âm Quốc ngữ</Typography.Text>
                <Button
                  size="small"
                  icon={<CopyOutlined />}
                  onClick={() => void copyText(result.transcription_text, "phiên âm")}
                >
                  Copy
                </Button>
              </div>
              <Typography.Paragraph className="!mb-0 whitespace-pre-wrap rounded-lg border border-border bg-muted/40 p-3 text-sm max-h-48 overflow-auto">
                {result.transcription_text || "—"}
              </Typography.Paragraph>
            </div>
          </div>
        </>
      )}
    </Card>
  );
}
