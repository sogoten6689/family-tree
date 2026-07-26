import { useCallback, useEffect, useMemo, useState } from "react";
import {
  Alert,
  Button,
  Card,
  Divider,
  Select,
  Space,
  Spin,
  Table,
  Tag,
  Typography,
  Upload,
} from "antd";
import type { UploadProps } from "antd";
import {
  CloudUploadOutlined,
  CopyOutlined,
  FileSearchOutlined,
  LinkOutlined,
  MergeCellsOutlined,
  ReloadOutlined,
} from "@ant-design/icons";
import { useNavigate } from "react-router-dom";
import { useTranslation } from "react-i18next";
import { toast } from "sonner";

import { FlowNextBanner } from "@/components/flow/FlowNextBanner";

import { OCR_ELIGIBLE_DOCUMENT_TYPES } from "@/components/documents/constants";
import { ApiError } from "@/lib/apiClient";
import {
  getOcrPageStatus,
  mergeOcrPages,
  ocrStoredDocumentFile,
  ocrTransliterateDocument,
} from "@/lib/documentApi";
import type {
  FamilyTreeSourceDocument,
  OcrPageStatusResponse,
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
  const { t } = useTranslation();
  const navigate = useNavigate();
  const [selectedFileId, setSelectedFileId] = useState<number | null>(null);
  const [pendingUpload, setPendingUpload] = useState<File | null>(null);
  const [runningFileId, setRunningFileId] = useState<number | null>(null);
  const [merging, setMerging] = useState(false);
  const [statusLoading, setStatusLoading] = useState(true);
  const [pageStatus, setPageStatus] = useState<OcrPageStatusResponse | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [result, setResult] = useState<OcrTransliterateResponse | null>(null);
  const [mergedPreview, setMergedPreview] = useState<string | null>(null);

  const imageFiles = useMemo(
    () => document.files.filter((file) => file.file_type.startsWith("image/")),
    [document.files],
  );

  const loadPageStatus = useCallback(async () => {
    setStatusLoading(true);
    try {
      const status = await getOcrPageStatus(document.id);
      setPageStatus(status);
    } catch {
      setPageStatus(null);
    } finally {
      setStatusLoading(false);
    }
  }, [document.id]);

  useEffect(() => {
    void loadPageStatus();
  }, [loadPageStatus, document.files.length]);

  useEffect(() => {
    if (imageFiles.length > 0 && selectedFileId == null && !pendingUpload) {
      setSelectedFileId(imageFiles[0].id);
    }
  }, [imageFiles, selectedFileId, pendingUpload]);

  const eligible = OCR_ELIGIBLE_DOCUMENT_TYPES.includes(document.type);

  if (!eligible) {
    return null;
  }

  const handleOcrOnePage = async (fileId: number) => {
    setRunningFileId(fileId);
    setError(null);
    try {
      const response = await ocrStoredDocumentFile(document.id, fileId);
      setResult(response);
      await loadPageStatus();
      toast.success(
        `OCR trang xong. Đã ghép ${response.merged_page_count ?? 0} trang${response.pipeline_synced ? ", pipeline sync" : ""}.`,
      );
    } catch (err) {
      const message =
        err instanceof ApiError || err instanceof Error ? err.message : "Không thể chạy OCR.";
      setError(message);
      toast.error(message);
    } finally {
      setRunningFileId(null);
    }
  };

  const handleRunOcrSelected = async () => {
    if (pendingUpload) {
      setRunningFileId(-1);
      setError(null);
      try {
        const response = await ocrTransliterateDocument(document.id, pendingUpload);
        setResult(response);
        await loadPageStatus();
        toast.success("OCR và phiên âm thành công.");
      } catch (err) {
        const message =
          err instanceof ApiError || err instanceof Error ? err.message : "Không thể chạy OCR.";
        setError(message);
        toast.error(message);
      } finally {
        setRunningFileId(null);
      }
      return;
    }
    if (selectedFileId != null) {
      await handleOcrOnePage(selectedFileId);
    }
  };

  const handleMergePages = async () => {
    setMerging(true);
    setError(null);
    try {
      const response = await mergeOcrPages(document.id, { syncPipeline: true });
      setMergedPreview(response.combined_transcription_text || null);
      await loadPageStatus();
      toast.success(
        `Đã ghép ${response.merged_page_count} trang${response.pipeline_synced ? " và đồng bộ pipeline" : ""}.`,
      );
    } catch (err) {
      const message =
        err instanceof ApiError || err instanceof Error ? err.message : "Không thể ghép trang.";
      setError(message);
      toast.error(message);
    } finally {
      setMerging(false);
    }
  };

  const handleRunNextPending = async () => {
    const next = pageStatus?.pages.find((page) => !page.ocr_done);
    if (!next) {
      toast.info("Tất cả trang đã OCR.");
      return;
    }
    await handleOcrOnePage(next.file_id);
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

  const doneCount = pageStatus?.ocr_done_count ?? 0;
  const totalCount = pageStatus?.total_pages ?? imageFiles.length;
  const mergedCount = pageStatus?.merged_page_count ?? 0;
  const extractHref = document.family_tree_id
    ? `/admin/gia-pha/${document.family_tree_id}?tab=pipeline`
    : "/user/documents/new";
  const showExtractBanner = mergedCount > 0 || !!mergedPreview;

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
        message="OCR từng trang (tránh timeout)"
        description="Mỗi trang ~1–2 phút. OCR xong từng trang → bấm「Ghép các trang」→ pipeline step OCR sẽ DONE. Cần HANNOM_API_TOKEN."
      />

      {error && <Alert type="error" showIcon message={error} className="mb-4" closable onClose={() => setError(null)} />}

      {showExtractBanner && (
        <FlowNextBanner
          message={t("flow.ocrMergeDone", {
            defaultValue: "Bước ② OCR hoàn tất — đã ghép phiên âm các trang.",
          })}
          nextLabel={t("flow.nextExtract", { defaultValue: "Trích xuất quan hệ" })}
          nextHref={extractHref}
        />
      )}

      <Space wrap className="mb-4">
        <Tag color={doneCount === totalCount && totalCount > 0 ? "success" : "processing"}>
          OCR: {doneCount}/{totalCount} trang
        </Tag>
        {pageStatus && pageStatus.merged_page_count > 0 && (
          <Tag color="blue">Đã ghép: {pageStatus.merged_page_count} trang</Tag>
        )}
        <Button size="small" icon={<ReloadOutlined />} loading={statusLoading} onClick={() => void loadPageStatus()}>
          Làm mới
        </Button>
        <Button
          type="primary"
          icon={<MergeCellsOutlined />}
          loading={merging}
          disabled={doneCount === 0 || runningFileId != null}
          onClick={() => void handleMergePages()}
        >
          Ghép các trang đã OCR
        </Button>
        <Button
          icon={<FileSearchOutlined />}
          loading={runningFileId != null}
          disabled={merging || doneCount === totalCount}
          onClick={() => void handleRunNextPending()}
        >
          OCR trang tiếp theo
        </Button>
      </Space>

      <Table
        size="small"
        className="mb-4"
        loading={statusLoading}
        pagination={{ pageSize: 10, showSizeChanger: totalCount > 20 }}
        rowKey="file_id"
        dataSource={pageStatus?.pages ?? imageFiles.map((file, index) => ({
          file_id: file.id,
          file_name: file.file_name,
          position: file.position ?? index,
          ocr_done: false,
        }))}
        columns={[
          {
            title: "Trang",
            dataIndex: "file_name",
            render: (name: string) => <Typography.Text code>{name}</Typography.Text>,
          },
          {
            title: "Trạng thái",
            dataIndex: "ocr_done",
            width: 120,
            render: (done: boolean) =>
              done ? <Tag color="success">Đã OCR</Tag> : <Tag>Chưa OCR</Tag>,
          },
          {
            title: "",
            width: 140,
            render: (_: unknown, row: { file_id: number; ocr_done: boolean }) => (
              <Button
                size="small"
                type={row.ocr_done ? "default" : "primary"}
                loading={runningFileId === row.file_id}
                disabled={runningFileId != null && runningFileId !== row.file_id}
                onClick={() => void handleOcrOnePage(row.file_id)}
              >
                {row.ocr_done ? "OCR lại" : "OCR"}
              </Button>
            ),
          },
        ]}
      />

      <Divider plain>Hoặc chọn / upload ảnh</Divider>

      {imageFiles.length > 0 && (
        <Select
          allowClear
          placeholder="Chọn ảnh"
          className="w-full mb-4"
          value={pendingUpload ? undefined : selectedFileId}
          disabled={!!pendingUpload || runningFileId != null}
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
      )}

      <Upload.Dragger {...uploadProps} disabled={runningFileId != null} className="!bg-muted/30 dark:!bg-muted/20 mb-4">
        <p className="ant-upload-drag-icon">
          <CloudUploadOutlined />
        </p>
        <Typography.Text>Upload ảnh mới (chỉ dùng OCR, không lưu vào document)</Typography.Text>
      </Upload.Dragger>

      <Button
        type="default"
        icon={<FileSearchOutlined />}
        loading={runningFileId != null}
        disabled={(!pendingUpload && selectedFileId == null) || merging}
        onClick={() => void handleRunOcrSelected()}
      >
        Chạy OCR trang đã chọn
      </Button>

      {runningFileId != null && (
        <div className="mt-4 flex items-center gap-2 text-muted-foreground">
          <Spin size="small" />
          <span>Đang gọi Kim Hán Nôm API (1–2 phút/trang)...</span>
        </div>
      )}

      {mergedPreview && (
        <>
          <Divider />
          <Typography.Title level={5}>Text ghép (combined_transcription.txt)</Typography.Title>
          <Typography.Paragraph className="!mb-0 whitespace-pre-wrap rounded-lg border border-border bg-muted/40 p-3 text-sm max-h-48 overflow-auto">
            {mergedPreview}
          </Typography.Paragraph>
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
          </Space>

          <div className="space-y-4">
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
