import {
  EditOutlined,
  ExportOutlined,
  FastForwardOutlined,
  LinkOutlined,
  PlayCircleOutlined,
  ReloadOutlined,
  SyncOutlined,
} from "@ant-design/icons";
import {
  Alert,
  Button,
  Descriptions,
  Drawer,
  Image,
  Space,
  Spin,
  Tag,
  Typography,
  message,
} from "antd";
import { useCallback, useEffect, useState } from "react";
import { useTranslation } from "react-i18next";
import { useNavigate } from "react-router-dom";

import { PipelineStepEditForm } from "@/components/pipeline/PipelineStepEditForm";
import {
  PIPELINE_STEP_LABELS,
  formatPipelineTimestamp,
  getPipelineStepDetail,
  pipelineStepStatusColor,
  resyncPipeline,
  runPipelineStep,
  skipPipelineStep,
  skippedReasonLabel,
  sourceTypeLabel,
  updatePipelineStep,
  type PipelineContext,
  type PipelineStep,
  type PipelineStepDetail,
  type PipelineStepId,
} from "@/lib/pipelineApi";

type Props = {
  treeId: string;
  stepId: PipelineStepId | null;
  open: boolean;
  context?: PipelineContext | null;
  onClose: () => void;
  onUpdated: () => Promise<void>;
};

function isImageFile(mimeType: string, filename: string): boolean {
  if (mimeType.startsWith("image/")) return true;
  const lower = filename.toLowerCase();
  return [".jpg", ".jpeg", ".png", ".gif", ".webp", ".bmp"].some((ext) => lower.endsWith(ext));
}

export function PipelineStepDrawer({ treeId, stepId, open, context, onClose, onUpdated }: Props) {
  const { t, i18n } = useTranslation();
  const navigate = useNavigate();
  const lang = i18n.language.startsWith("en") ? "en" : "vi";

  const [detail, setDetail] = useState<PipelineStepDetail | null>(null);
  const [loading, setLoading] = useState(false);
  const [actionLoading, setActionLoading] = useState(false);
  const [editOpen, setEditOpen] = useState(false);
  const [saving, setSaving] = useState(false);

  const loadDetail = useCallback(async () => {
    if (!stepId) return;
    setLoading(true);
    try {
      const response = await getPipelineStepDetail(treeId, stepId);
      setDetail(response);
    } catch (err) {
      message.error(err instanceof Error ? err.message : t("pipeline.detailLoadError", { defaultValue: "Không tải được chi tiết step" }));
      setDetail(null);
    } finally {
      setLoading(false);
    }
  }, [stepId, t, treeId]);

  useEffect(() => {
    if (open && stepId) {
      void loadDetail();
    } else {
      setDetail(null);
      setEditOpen(false);
    }
  }, [loadDetail, open, stepId]);

  if (!stepId) return null;

  const resolvedContext = detail?.context ?? context;
  const step = detail as PipelineStep | null;
  const canAct = step && (step.status === "pending" || step.status === "error");

  const goTab = (tab: string) => {
    navigate(`/admin/gia-pha/${encodeURIComponent(treeId)}?tab=${tab}`);
    onClose();
  };

  const goDocument = (documentId: number) => {
    navigate(`/admin/documents/${documentId}/edit`);
    onClose();
  };

  const handleRun = async () => {
    setActionLoading(true);
    try {
      await runPipelineStep(treeId, stepId);
      message.success(t("pipeline.runSuccess", { defaultValue: "Đã chạy bước pipeline." }));
      await loadDetail();
      await onUpdated();
    } catch (err) {
      message.error(err instanceof Error ? err.message : t("pipeline.runError", { defaultValue: "Không chạy được bước" }));
    } finally {
      setActionLoading(false);
    }
  };

  const handleSkip = async () => {
    setActionLoading(true);
    try {
      await skipPipelineStep(treeId, stepId);
      message.info(t("pipeline.skipSuccess", { defaultValue: "Đã bỏ qua bước." }));
      await loadDetail();
      await onUpdated();
    } catch (err) {
      message.error(err instanceof Error ? err.message : t("pipeline.skipError", { defaultValue: "Không bỏ qua được bước" }));
    } finally {
      setActionLoading(false);
    }
  };

  const handleResyncStep = async () => {
    setActionLoading(true);
    try {
      await resyncPipeline(treeId, stepId);
      message.success(t("pipeline.resyncStepSuccess", { defaultValue: "Đã đồng bộ lại bước này." }));
      await loadDetail();
      await onUpdated();
    } catch (err) {
      message.error(err instanceof Error ? err.message : t("pipeline.resyncError", { defaultValue: "Không đồng bộ được" }));
    } finally {
      setActionLoading(false);
    }
  };

  const handleSaveEdit = async (payload: Parameters<typeof updatePipelineStep>[2]) => {
    setSaving(true);
    try {
      await updatePipelineStep(treeId, stepId, payload);
      message.success(t("pipeline.updateSuccess", { defaultValue: "Đã cập nhật bước pipeline." }));
      setEditOpen(false);
      await loadDetail();
      await onUpdated();
    } catch (err) {
      message.error(err instanceof Error ? err.message : t("pipeline.updateError", { defaultValue: "Không cập nhật được" }));
    } finally {
      setSaving(false);
    }
  };

  const renderCtas = () => {
    const docId = detail?.artifact.document_id ?? step?.document_id;
    switch (stepId) {
      case "name":
        return (
          <Button size="small" onClick={() => goTab("visual")}>
            {t("pipeline.cta.viewTree", { defaultValue: "Xem cây gia phả" })}
          </Button>
        );
      case "hannom_image":
        return (
          <Button size="small" onClick={() => goTab("documents")}>
            {t("pipeline.cta.uploadImages", { defaultValue: "Kho tư liệu — upload ảnh" })}
          </Button>
        );
      case "ocr":
      case "han_chars":
      case "quoc_ngu":
        return docId ? (
          <Button size="small" type="primary" onClick={() => goDocument(docId)}>
            {t("pipeline.cta.openDocument", { defaultValue: "Mở tài liệu & Phiên âm" })}
          </Button>
        ) : (
          <Button size="small" onClick={() => goTab("documents")}>
            {t("pipeline.cta.addDocument", { defaultValue: "Thêm tài liệu" })}
          </Button>
        );
      case "distilled":
        return (
          <Typography.Text type="secondary" className="text-xs">
            {t("pipeline.cta.distilledPending", { defaultValue: "Bước cô đọng chưa triển khai tự động." })}
          </Typography.Text>
        );
      case "output":
        return (
          <Button size="small" type="primary" onClick={() => goTab("visual")}>
            {t("pipeline.cta.viewVisual", { defaultValue: "Xem sơ đồ (Visual)" })}
          </Button>
        );
      default:
        return null;
    }
  };

  const imageFiles =
    (detail?.artifact?.files ?? []).filter((file) => isImageFile(file.mime_type, file.filename));
  const textFiles =
    (detail?.artifact?.files ?? []).filter((file) => !isImageFile(file.mime_type, file.filename));

  return (
    <>
      <Drawer
        open={open}
        onClose={onClose}
        width={Math.min(640, window.innerWidth - 24)}
        title={
          <Space wrap>
            <span>{PIPELINE_STEP_LABELS[stepId][lang]}</span>
            {step && <Tag color={pipelineStepStatusColor(step.status)}>{step.status}</Tag>}
            {step?.manual_override && (
              <Tag color="purple">{t("pipeline.manualOverride", { defaultValue: "Chỉnh tay" })}</Tag>
            )}
          </Space>
        }
        extra={
          <Space wrap>
            <Button icon={<ReloadOutlined />} onClick={() => void loadDetail()} disabled={loading}>
              {t("common.refresh", { defaultValue: "Làm mới" })}
            </Button>
            <Button icon={<EditOutlined />} onClick={() => setEditOpen(true)} disabled={!step}>
              {t("pipeline.edit", { defaultValue: "Sửa" })}
            </Button>
          </Space>
        }
      >
        {loading && (
          <div className="flex justify-center py-12">
            <Spin />
          </div>
        )}

        {!loading && !detail && stepId && (
          <Alert
            type="error"
            showIcon
            message={t("pipeline.detailLoadError", { defaultValue: "Không tải được chi tiết step" })}
          />
        )}

        {!loading && detail && (
          <Space direction="vertical" size="middle" className="w-full">
            {resolvedContext && (
              <Alert
                type="info"
                showIcon
                message={
                  <Space wrap>
                    <span>
                      {t("pipeline.sourceType", { defaultValue: "Nguồn" })}:{" "}
                      <strong>{sourceTypeLabel(resolvedContext.source_type, lang)}</strong>
                    </span>
                    {resolvedContext.external_url && (
                      <a href={resolvedContext.external_url} target="_blank" rel="noreferrer">
                        <LinkOutlined /> {t("pipeline.openSource", { defaultValue: "Mở nguồn" })}
                      </a>
                    )}
                  </Space>
                }
              />
            )}

            <Descriptions bordered size="small" column={1}>
              <Descriptions.Item label={t("pipeline.fields.inputRef", { defaultValue: "Input ref" })}>
                {detail.input_ref || "—"}
              </Descriptions.Item>
              <Descriptions.Item label={t("pipeline.fields.outputRef", { defaultValue: "Output ref" })}>
                {detail.output_ref || "—"}
              </Descriptions.Item>
              <Descriptions.Item label={t("pipeline.fields.documentId", { defaultValue: "Document ID" })}>
                {detail.document_id || "—"}
              </Descriptions.Item>
              <Descriptions.Item label={t("pipeline.fields.contentHash", { defaultValue: "Content hash" })}>
                <Typography.Text code className="text-xs break-all">
                  {detail.content_hash || "—"}
                </Typography.Text>
              </Descriptions.Item>
              <Descriptions.Item label={t("pipeline.fields.skippedReason", { defaultValue: "Lý do bỏ qua" })}>
                {skippedReasonLabel(detail.skipped_reason, lang)}
              </Descriptions.Item>
              <Descriptions.Item label={t("pipeline.timestamps.started", { defaultValue: "Bắt đầu" })}>
                {formatPipelineTimestamp(detail.started_at)}
              </Descriptions.Item>
              <Descriptions.Item label={t("pipeline.timestamps.finished", { defaultValue: "Kết thúc" })}>
                {formatPipelineTimestamp(detail.finished_at)}
              </Descriptions.Item>
              <Descriptions.Item label={t("pipeline.timestamps.updated", { defaultValue: "Cập nhật" })}>
                {formatPipelineTimestamp(detail.updated_at)}
              </Descriptions.Item>
              {detail.error_message && (
                <Descriptions.Item label={t("pipeline.fields.errorMessage", { defaultValue: "Lỗi" })}>
                  <Typography.Text type="danger">{detail.error_message}</Typography.Text>
                </Descriptions.Item>
              )}
              {detail.admin_note && (
                <Descriptions.Item label={t("pipeline.fields.adminNote", { defaultValue: "Ghi chú admin" })}>
                  {detail.admin_note}
                </Descriptions.Item>
              )}
            </Descriptions>

            <div>
              <Typography.Title level={5} className="!mb-2">
                {t("pipeline.artifact", { defaultValue: "Artifact" })}
              </Typography.Title>

              {detail.artifact.kind === "none" && (
                <Typography.Text type="secondary">
                  {detail.artifact.message || t("pipeline.noArtifact", { defaultValue: "Chưa có artifact." })}
                </Typography.Text>
              )}

              {detail.artifact.kind === "text" && detail.artifact.preview_text && (
                <Typography.Paragraph className="whitespace-pre-wrap rounded border p-3 bg-[var(--ant-color-fill-alter)]">
                  {detail.artifact.preview_text}
                </Typography.Paragraph>
              )}

              {detail.artifact.kind === "family_tree" && (
                <Space direction="vertical">
                  <Typography.Text>
                    {t("pipeline.nodeCount", {
                      defaultValue: "{{count}} node",
                      count: detail.artifact.node_count ?? resolvedContext?.node_count ?? 0,
                    })}
                  </Typography.Text>
                  {detail.artifact.preview_text && (
                    <Typography.Text type="secondary">{detail.artifact.preview_text}</Typography.Text>
                  )}
                </Space>
              )}

              {detail.artifact.kind === "document" && (
                <Space direction="vertical" className="w-full">
                  <Typography.Text strong>{detail.artifact.title}</Typography.Text>
                  {detail.artifact.type && <Tag>{detail.artifact.type}</Tag>}
                  {detail.artifact.preview_text && (
                    <Typography.Paragraph className="whitespace-pre-wrap rounded border p-3 bg-[var(--ant-color-fill-alter)]">
                      {detail.artifact.preview_text}
                    </Typography.Paragraph>
                  )}
                </Space>
              )}

              {imageFiles.length > 0 && (
                <Image.PreviewGroup>
                  <Space wrap className="mt-2">
                    {imageFiles.map((file) => (
                      <Image
                        key={file.id}
                        width={96}
                        height={96}
                        className="object-cover rounded border"
                        src={file.url ?? undefined}
                        alt={file.filename}
                        fallback="data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mNk+M9QDwADhgGAWjR9awAAAABJRU5ErkJggg=="
                      />
                    ))}
                  </Space>
                </Image.PreviewGroup>
              )}

              {textFiles.length > 0 && (
                <Space direction="vertical" className="mt-2 w-full">
                  {textFiles.map((file) => (
                    <Space key={file.id} wrap>
                      <Typography.Text>{file.filename}</Typography.Text>
                      {file.url && (
                        <a href={file.url} target="_blank" rel="noreferrer">
                          <ExportOutlined /> {t("pipeline.viewFull", { defaultValue: "Xem / tải file" })}
                        </a>
                      )}
                    </Space>
                  ))}
                </Space>
              )}
            </div>

            <Space wrap>{renderCtas()}</Space>

            <Space wrap>
              {canAct && (
                <>
                  <Button
                    type="primary"
                    icon={<PlayCircleOutlined />}
                    loading={actionLoading}
                    onClick={() => void handleRun()}
                  >
                    {step?.status === "error"
                      ? t("pipeline.retryStep", { defaultValue: "Thử lại" })
                      : t("pipeline.runStep", { defaultValue: "Chạy" })}
                  </Button>
                  <Button icon={<FastForwardOutlined />} loading={actionLoading} onClick={() => void handleSkip()}>
                    {t("pipeline.skipStep", { defaultValue: "Bỏ qua" })}
                  </Button>
                </>
              )}
              <Button icon={<SyncOutlined />} loading={actionLoading} onClick={() => void handleResyncStep()}>
                {t("pipeline.resyncStep", { defaultValue: "Đồng bộ lại bước này" })}
              </Button>
            </Space>
          </Space>
        )}
      </Drawer>

      <PipelineStepEditForm
        open={editOpen}
        treeId={treeId}
        stepId={stepId}
        step={detail}
        saving={saving}
        onCancel={() => setEditOpen(false)}
        onSubmit={handleSaveEdit}
      />
    </>
  );
}
