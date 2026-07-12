import {
  CheckCircleOutlined,
  CloseCircleOutlined,
  EyeOutlined,
  FastForwardOutlined,
  PlayCircleOutlined,
  ReloadOutlined,
  SyncOutlined,
} from "@ant-design/icons";
import { useCallback, useEffect, useMemo, useState } from "react";
import { useNavigate } from "react-router-dom";
import { Alert, Button, Card, Space, Steps, Tag, Typography, message } from "antd";
import { useTranslation } from "react-i18next";

import { PipelineStepDrawer } from "@/components/pipeline/PipelineStepDrawer";
import {
  PIPELINE_STEP_LABELS,
  getFamilyTreePipeline,
  pipelineStepStatusColor,
  resyncPipeline,
  runAllPipelineSteps,
  runPipelineStep,
  skipPipelineStep,
  skippedReasonLabel,
  sourceTypeLabel,
  type PipelineContext,
  type PipelineStep,
  type PipelineStepId,
} from "@/lib/pipelineApi";

type Props = {
  treeId: string;
};

const ORDERED_STEPS: PipelineStepId[] = [
  "name",
  "hannom_image",
  "ocr",
  "han_chars",
  "quoc_ngu",
  "distilled",
  "output",
];

export function GenealogyPipelineSteps({ treeId }: Props) {
  const { t, i18n } = useTranslation();
  const navigate = useNavigate();
  const [steps, setSteps] = useState<PipelineStep[]>([]);
  const [context, setContext] = useState<PipelineContext | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [runningStep, setRunningStep] = useState<PipelineStepId | null>(null);
  const [runningAll, setRunningAll] = useState(false);
  const [resyncing, setResyncing] = useState(false);
  const [detailStepId, setDetailStepId] = useState<PipelineStepId | null>(null);

  const loadPipeline = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const response = await getFamilyTreePipeline(treeId);
      setSteps(response.steps);
      setContext(response.context);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Không tải được pipeline");
      setSteps([]);
      setContext(null);
    } finally {
      setLoading(false);
    }
  }, [treeId]);

  useEffect(() => {
    void loadPipeline();
  }, [loadPipeline]);

  const stepMap = useMemo(() => {
    const map = new Map<PipelineStepId, PipelineStep>();
    for (const step of steps) {
      map.set(step.step_id, step);
    }
    return map;
  }, [steps]);

  const handleRunStep = async (stepId: PipelineStepId) => {
    setRunningStep(stepId);
    try {
      await runPipelineStep(treeId, stepId);
      message.success(t("pipeline.runSuccess", { defaultValue: "Đã chạy bước pipeline." }));
      await loadPipeline();
    } catch (err) {
      message.error(err instanceof Error ? err.message : "Không chạy được bước");
    } finally {
      setRunningStep(null);
    }
  };

  const handleSkipStep = async (stepId: PipelineStepId) => {
    setRunningStep(stepId);
    try {
      await skipPipelineStep(treeId, stepId);
      message.info(t("pipeline.skipSuccess", { defaultValue: "Đã bỏ qua bước." }));
      await loadPipeline();
    } catch (err) {
      message.error(err instanceof Error ? err.message : "Không bỏ qua được bước");
    } finally {
      setRunningStep(null);
    }
  };

  const handleRunAll = async () => {
    setRunningAll(true);
    try {
      const result = await runAllPipelineSteps(treeId);
      message.success(
        t("pipeline.runAllSuccess", {
          defaultValue: "Chạy xong: {{ran}} bước, bỏ qua {{skipped}}.",
          ran: result.ran.length,
          skipped: result.skipped.length,
        }),
      );
      await loadPipeline();
    } catch (err) {
      message.error(err instanceof Error ? err.message : "Không chạy được toàn bộ pipeline");
    } finally {
      setRunningAll(false);
    }
  };

  const handleResyncAll = async () => {
    setResyncing(true);
    try {
      const response = await resyncPipeline(treeId);
      setSteps(response.steps);
      setContext(response.context);
      message.success(t("pipeline.resyncSuccess", { defaultValue: "Đã đồng bộ lại pipeline từ cây." }));
    } catch (err) {
      message.error(err instanceof Error ? err.message : t("pipeline.resyncError", { defaultValue: "Không đồng bộ được" }));
    } finally {
      setResyncing(false);
    }
  };

  const currentIndex = useMemo(() => {
    for (let index = 0; index < ORDERED_STEPS.length; index += 1) {
      const step = stepMap.get(ORDERED_STEPS[index]);
      if (!step || (step.status !== "done" && step.status !== "skipped")) {
        return index;
      }
    }
    return ORDERED_STEPS.length;
  }, [stepMap]);

  const lang = i18n.language.startsWith("en") ? "en" : "vi";
  const isVgp = treeId.startsWith("vgp-") || context?.source_type === "vgp";

  const canRunOutput = useMemo(() => {
    const distilled = stepMap.get("distilled");
    if (isVgp) return true;
    if (!distilled) return true;
    return distilled.status === "done" || distilled.status === "skipped";
  }, [isVgp, stepMap]);

  return (
    <>
      <Card
        title={t("pipeline.title", { defaultValue: "Pipeline số hóa gia phả" })}
        loading={loading}
        extra={
          <Space wrap>
            <Button icon={<ReloadOutlined />} onClick={() => void loadPipeline()} disabled={loading}>
              {t("common.refresh", { defaultValue: "Làm mới" })}
            </Button>
            <Button icon={<SyncOutlined />} loading={resyncing} onClick={() => void handleResyncAll()}>
              {t("pipeline.resyncAll", { defaultValue: "Đồng bộ lại từ cây" })}
            </Button>
            <Button
              type="primary"
              icon={<PlayCircleOutlined />}
              loading={runningAll}
              onClick={() => void handleRunAll()}
            >
              {t("pipeline.runAll", { defaultValue: "Chạy tất cả" })}
            </Button>
          </Space>
        }
      >
        {error && (
          <Alert type="error" showIcon message={error} className="mb-4" closable onClose={() => setError(null)} />
        )}

        {context && (
          <Alert
            className="mb-4"
            type="info"
            showIcon
            message={
              <Space wrap>
                <span>
                  {t("pipeline.sourceType", { defaultValue: "Nguồn" })}:{" "}
                  <strong>{sourceTypeLabel(context.source_type, lang)}</strong>
                </span>
                {context.tree_name && (
                  <span>
                    {t("pipeline.treeName", { defaultValue: "Tên" })}: <strong>{context.tree_name}</strong>
                  </span>
                )}
                {context.node_count > 0 && (
                  <span>
                    {t("pipeline.nodeCount", { defaultValue: "{{count}} node", count: context.node_count })}
                  </span>
                )}
                {context.external_url && (
                  <a href={context.external_url} target="_blank" rel="noreferrer">
                    {t("pipeline.openSource", { defaultValue: "Mở nguồn" })}
                  </a>
                )}
              </Space>
            }
          />
        )}

        <Typography.Paragraph type="secondary" className="!mb-4">
          {t("pipeline.desc", {
            defaultValue:
              "7 bước số hóa: tên → ảnh Hán-Nôm → OCR → ký tự Hán → quốc ngữ → cô đọng → cây/văn bản. Mỗi bước có thể bỏ qua.",
          })}
        </Typography.Paragraph>

        <Steps
          direction="vertical"
          current={currentIndex}
          items={ORDERED_STEPS.map((stepId) => {
            const step = stepMap.get(stepId);
            const status = step?.status ?? "pending";
            const label = PIPELINE_STEP_LABELS[stepId][lang];
            const canAct = status === "pending" || status === "error";
            const runDisabled = stepId === "output" && !canRunOutput;
            const imageDocId = stepMap.get("hannom_image")?.document_id;

            return {
              title: (
                <Space wrap>
                  <span>{label}</span>
                  <Tag color={pipelineStepStatusColor(status)}>{status}</Tag>
                  {step?.manual_override && (
                    <Tag color="purple">{t("pipeline.manualOverride", { defaultValue: "Chỉnh tay" })}</Tag>
                  )}
                </Space>
              ),
              description: (
                <Space direction="vertical" size="small" className="w-full">
                  {step?.output_ref && (
                    <Typography.Text type="secondary" className="text-xs">
                      {t("pipeline.outputRef", { defaultValue: "Kết quả" })}: {step.output_ref}
                    </Typography.Text>
                  )}
                  {step?.skipped_reason && (
                    <Typography.Text type="secondary" className="text-xs">
                      {t("pipeline.skipReason", { defaultValue: "Lý do bỏ qua" })}:{" "}
                      {skippedReasonLabel(step.skipped_reason, lang)}
                    </Typography.Text>
                  )}
                  {step?.error_message && (
                    <Typography.Text type="danger" className="text-xs">
                      {step.error_message}
                    </Typography.Text>
                  )}
                  {stepId === "ocr" && (status === "pending" || status === "error") && imageDocId && (
                    <Alert
                      type="warning"
                      showIcon
                      className="!py-2"
                      message="OCR từng trang để tránh timeout"
                      description={
                        <Button
                          size="small"
                          type="link"
                          className="!p-0"
                          onClick={() => navigate(`/admin/documents/${imageDocId}/edit`)}
                        >
                          Mở document ảnh #{imageDocId} → OCR từng trang → Ghép trang
                        </Button>
                      }
                    />
                  )}
                  <Space wrap>
                    <Button size="small" icon={<EyeOutlined />} onClick={() => setDetailStepId(stepId)}>
                      {t("pipeline.detail", { defaultValue: "Chi tiết" })}
                    </Button>
                    {canAct && (
                      <>
                        <Button
                          size="small"
                          type="primary"
                          icon={<PlayCircleOutlined />}
                          loading={runningStep === stepId}
                          disabled={runDisabled}
                          onClick={() => void handleRunStep(stepId)}
                        >
                          {status === "error"
                            ? t("pipeline.retryStep", { defaultValue: "Thử lại" })
                            : t("pipeline.runStep", { defaultValue: "Chạy" })}
                        </Button>
                        <Button
                          size="small"
                          icon={<FastForwardOutlined />}
                          loading={runningStep === stepId}
                          onClick={() => void handleSkipStep(stepId)}
                        >
                          {t("pipeline.skipStep", { defaultValue: "Bỏ qua" })}
                        </Button>
                      </>
                    )}
                  </Space>
                  {runDisabled && (
                    <Typography.Text type="secondary" className="text-xs">
                      {t("pipeline.outputBlocked", {
                        defaultValue: "Chạy bước Cô đọng trước hoặc bỏ qua bước đó.",
                      })}
                    </Typography.Text>
                  )}
                  {status === "done" && <CheckCircleOutlined className="text-[var(--ant-color-success)]" />}
                  {status === "error" && <CloseCircleOutlined className="text-[var(--ant-color-error)]" />}
                </Space>
              ),
              status:
                status === "done"
                  ? "finish"
                  : status === "error"
                    ? "error"
                    : status === "running"
                      ? "process"
                      : status === "skipped"
                        ? "finish"
                        : "wait",
            };
          })}
        />
      </Card>

      <PipelineStepDrawer
        treeId={treeId}
        stepId={detailStepId}
        open={detailStepId !== null}
        context={context}
        onClose={() => setDetailStepId(null)}
        onUpdated={loadPipeline}
      />
    </>
  );
}
