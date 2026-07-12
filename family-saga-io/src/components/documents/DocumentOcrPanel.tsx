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
import {
  ocrBatchDocument,
  ocrStoredDocumentFile,
  ocrTransliterateDocument,
} from "@/lib/documentApi";
import type {
  FamilyTreeSourceDocument,
  OcrBatchResponse,
  OcrTransliterateResponse,
} from "@/types/document";

type Props = {
  document: FamilyTreeSourceDocument;
};

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
  const [batchRunning, setBatchRunning] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [result, setResult] = useState<OcrTransliterateResponse | null>(null);
  const [batchResult, setBatchResult] = useState<OcrBatchResponse | null>(null);

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
    throw new Error("Vui lòng chọn ảnh có sẵn hoặc upload ảnh mới để OCR.");
  };

  const handleRunOcr = async () => {
    setRunning(true);
    setError(null);
    setBatchResult(null);
    try {
      let response: OcrTransliterateResponse;
      if (pendingUpload) {
        const imageFile = await resolveImageFile();
        response = await ocrTransliterateDocument(document.id, imageFile);
      } else if (selectedFileId != null) {
        response = await ocrStoredDocumentFile(document.id, selectedFileId);
      } else {
        throw new Error("Vui lòng chọn ảnh có sẵn hoặc upload ảnh mới để OCR.");
      }
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

  const handleRunBatchOcr = async () => {
    setBatchRunning(true);
    setError(null);
    setResult(null);
    try {
      const response = await ocrBatchDocument(document.id, { skipExisting: true });
      setBatchResult(response);
      if (response.errors.length > 0) {
        toast.warning(
          `OCR: ${response.processed} trang, ghép ${response.merged_page_count}, ${response.errors.length} lỗi.`,
        );
      } else {
        toast.success(
          `OCR xong: ${response.processed} trang mới, tổng ghép ${response.merged_page_count} trang${response.pipeline_synced ? ", pipeline đã sync" : ""}.`,
        );
      }
    } catch (err) {
      const message =
        err instanceof ApiError || err instanceof Error
          ? err.message
          : "Không thể chạy OCR batch.";
      setError(message);
      toast.error(message);
    } finally {
      setBatchRunning(false);
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
        description="Ảnh đã lưu MinIO sẽ OCR trực tiếp (không cần tải lại). Kết quả lưu vào tài liệu ket_qua_van_ban. Cần token tại Developer → Hán-Nôm Config."
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

      <Space wrap className="mb-4">
        <Button
          type="primary"
          icon={<FileSearchOutlined />}
          loading={running}
          disabled={(!pendingUpload && selectedFileId == null) || batchRunning}
          onClick={() => void handleRunOcr()}
        >
          Chạy OCR một trang
        </Button>
        {imageFiles.length > 1 && (
          <Button
            icon={<FileSearchOutlined />}
            loading={batchRunning}
            disabled={running}
            onClick={() => void handleRunBatchOcr()}
          >
            OCR tất cả &amp; ghép ({imageFiles.length} trang)
          </Button>
        )}
      </Space>

      {(running || batchRunning) && (
        <div className="mb-4 flex items-center gap-2 text-muted-foreground">
          <Spin size="small" />
          <span>
            {batchRunning
              ? "Đang OCR batch từ MinIO (có thể mất vài phút)..."
              : "Đang gọi Kim Hán Nôm API (có thể mất 1–2 phút)..."}
          </span>
        </div>
      )}

      {batchResult && (
        <>
          <Divider />
          <Typography.Title level={5}>Kết quả OCR batch</Typography.Title>
          <Typography.Paragraph type="secondary">
            Đã xử lý {batchResult.processed}, bỏ qua {batchResult.skipped}, ghép{" "}
            {batchResult.merged_page_count} trang, lỗi {batchResult.errors.length}.
            {batchResult.pipeline_synced && " Pipeline đã đồng bộ."}
          </Typography.Paragraph>
          {batchResult.errors.length > 0 && (
            <Alert
              type="warning"
              showIcon
              className="mb-4"
              message="Một số trang lỗi"
              description={batchResult.errors.map((e) => `${e.file_name}: ${e.error}`).join("; ")}
            />
          )}
          {batchResult.combined_transcription_text && (
            <Typography.Paragraph className="!mb-0 whitespace-pre-wrap rounded-lg border border-border bg-muted/40 p-3 text-sm max-h-48 overflow-auto">
              {batchResult.combined_transcription_text}
            </Typography.Paragraph>
          )}
        </>
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
