import {
  CheckOutlined,
  CloseOutlined,
  DownloadOutlined,
  ImportOutlined,
  PlayCircleOutlined,
  ReloadOutlined,
} from "@ant-design/icons";
import { Alert, AutoComplete, Button, Input, Modal, Popconfirm, Select, Space, Table, Tag, Tooltip, Typography, message } from "antd";
import { useCallback, useEffect, useState } from "react";
import { useTranslation } from "react-i18next";

import {
  engineRunStatus,
  fetchTrainingExport,
  importLlmResults,
  makeVersionCurrent,
  listEnabledTextEngines,
  listScanVersions,
  parseImportFile,
  reviewVersion,
  runTextEngine,
  type LlmImportPayload,
  type LlmImportResult,
  type ReviewStatus,
  type ScanVersion,
} from "@/lib/llmImportApi";

const SOURCE_OPTIONS = [{ value: "chatgpt-web" }, { value: "gemini-web" }];

const REVIEW_COLOR: Record<ReviewStatus, string> = { pending: "gold", approved: "green", rejected: "red" };
const RUN_COLOR = { pending: "default", running: "processing", done: "green", error: "red" } as const;
/** Tự tải lại khi còn version engine đang chờ/chạy (engine chạy nền ở backend). */
const RUN_POLL_MS = 5000;

/**
 * Phiên bản của 1 bộ gia phả + nhập kết quả {cn, sv, vi} do tool LLM chạy
 * NGOÀI web (máy người dùng). Mỗi lần nhập = 1 version mới, không ghi đè
 * version hiện tại. Chủ bộ gia phả/admin nhập; chỉ admin duyệt (duyệt không
 * đổi version hiện tại — chỉ quyết định có vào dữ liệu train không).
 */
export function LlmImportPanel({
  scanId,
  isAdmin,
  onCurrentChanged,
}: {
  scanId: number;
  isAdmin: boolean;
  /** Gọi sau khi đổi phiên bản hiện tại — trang cha tải lại tab Trích xuất / Trang. */
  onCurrentChanged?: () => void;
}) {
  const { t } = useTranslation();
  const [versions, setVersions] = useState<ScanVersion[]>([]);
  const [loading, setLoading] = useState(false);
  const [open, setOpen] = useState(false);
  const [busyVersion, setBusyVersion] = useState<number | null>(null);
  const [engines, setEngines] = useState<string[]>([]);
  const [engine, setEngine] = useState<string | undefined>();
  const [starting, setStarting] = useState(false);

  const load = useCallback(async () => {
    setLoading(true);
    try {
      setVersions(await listScanVersions(scanId));
    } catch (err) {
      message.error(err instanceof Error ? err.message : "Không tải được danh sách phiên bản");
    } finally {
      setLoading(false);
    }
  }, [scanId]);

  useEffect(() => {
    void load();
  }, [load]);

  useEffect(() => {
    if (!isAdmin) return; // chạy engine tốn tiền → chỉ admin (chốt 04/10/2026)
    listEnabledTextEngines()
      .then((names) => {
        setEngines(names);
        setEngine((current) => current ?? names[0]);
      })
      .catch(() => setEngines([]));
  }, [isAdmin]);

  const hasActiveRun = versions.some((v) => {
    const status = engineRunStatus(v);
    return status === "pending" || status === "running";
  });
  useEffect(() => {
    if (!hasActiveRun) return;
    const timer = window.setInterval(() => void load(), RUN_POLL_MS);
    return () => window.clearInterval(timer);
  }, [hasActiveRun, load]);

  const startRun = async () => {
    if (!engine) return;
    setStarting(true);
    try {
      const version = await runTextEngine(scanId, engine);
      message.success(
        t("llmImport.runQueued", { defaultValue: "Đã xếp hàng chạy {{engine}} — phiên bản v{{n}}", engine, n: version.version_number }),
      );
      await load();
    } catch (err) {
      message.error(err instanceof Error ? err.message : "Không chạy được engine");
    } finally {
      setStarting(false);
    }
  };

  const makeCurrent = async (version: ScanVersion) => {
    setBusyVersion(version.version_id);
    try {
      await makeVersionCurrent(scanId, version.version_id);
      message.success(
        t("llmImport.madeCurrent", { defaultValue: "Đã đặt v{{n}} làm phiên bản hiện tại", n: version.version_number }),
      );
      await load();
      onCurrentChanged?.();
    } catch (err) {
      message.error(err instanceof Error ? err.message : "Không đặt được phiên bản hiện tại");
    } finally {
      setBusyVersion(null);
    }
  };

  const review = async (versionId: number, status: ReviewStatus) => {
    setBusyVersion(versionId);
    try {
      await reviewVersion(scanId, versionId, status);
      await load();
    } catch (err) {
      message.error(err instanceof Error ? err.message : "Duyệt thất bại");
    } finally {
      setBusyVersion(null);
    }
  };

  const exportTraining = async () => {
    try {
      const text = await fetchTrainingExport();
      const url = URL.createObjectURL(new Blob([text], { type: "application/x-ndjson" }));
      const link = document.createElement("a");
      link.href = url;
      link.download = "gia_pha_training_pairs.jsonl";
      link.click();
      URL.revokeObjectURL(url);
    } catch (err) {
      message.error(err instanceof Error ? err.message : "Xuất dữ liệu thất bại");
    }
  };

  return (
    <Space direction="vertical" size="middle" className="w-full">
      <Alert
        type="info"
        showIcon
        message={t("llmImport.introTitle", { defaultValue: "Nhập kết quả phiên âm/dịch nghĩa từ tool LLM" })}
        description={t("llmImport.introDesc", {
          defaultValue:
            "Chạy tool trên máy của bạn, rồi tải file JSON/JSONL gồm {page, cn, sv, vi} lên đây. Mỗi lần nhập tạo 1 phiên bản mới, không ghi đè kết quả hiện tại. Admin duyệt trước khi đưa vào dữ liệu train.",
        })}
      />
      <Space wrap>
        <Button type="primary" icon={<ImportOutlined />} onClick={() => setOpen(true)}>
          {t("llmImport.importBtn", { defaultValue: "Nhập kết quả LLM" })}
        </Button>
        <Button icon={<ReloadOutlined />} onClick={() => void load()} loading={loading}>
          {t("familyTree.reload", { defaultValue: "Tải lại" })}
        </Button>
        {isAdmin && (
          <>
            <Select
              className="min-w-[180px]"
              value={engine}
              onChange={setEngine}
              options={engines.map((name) => ({ value: name, label: name }))}
              placeholder={t("llmImport.noEngine", { defaultValue: "Chưa có engine" })}
              disabled={engines.length === 0}
              aria-label={t("llmImport.engine", { defaultValue: "Engine phiên âm/dịch" })}
            />
            <Button
              icon={<PlayCircleOutlined />}
              disabled={!engine}
              loading={starting}
              onClick={() => void startRun()}
            >
              {t("llmImport.runBtn", { defaultValue: "Chạy engine" })}
            </Button>
          </>
        )}
        {isAdmin && (
          <Button icon={<DownloadOutlined />} onClick={() => void exportTraining()}>
            {t("llmImport.exportBtn", { defaultValue: "Xuất dữ liệu train (JSONL)" })}
          </Button>
        )}
      </Space>

      <Table<ScanVersion>
        rowKey="version_id"
        size="small"
        loading={loading}
        dataSource={versions}
        pagination={false}
        columns={[
          {
            title: t("llmImport.colVersion", { defaultValue: "Phiên bản" }),
            render: (_, v) => (
              <Space>
                v{v.version_number}
                {v.is_current && <Tag color="blue">{t("llmImport.current", { defaultValue: "Hiện tại" })}</Tag>}
              </Space>
            ),
          },
          {
            title: t("llmImport.colSource", { defaultValue: "Nguồn" }),
            render: (_, v) => (v.source ? <Typography.Text code>{v.source}</Typography.Text> : "Pipeline"),
          },
          { title: t("llmImport.colNote", { defaultValue: "Ghi chú" }), dataIndex: "note", render: (n) => n || "—" },
          {
            title: t("llmImport.colRun", { defaultValue: "Chạy" }),
            render: (_, v) => {
              const status = engineRunStatus(v);
              if (!status) return "—";
              const tag = <Tag color={RUN_COLOR[status]}>{t(`llmImport.run.${status}`, { defaultValue: status })}</Tag>;
              const errorMessage = v.steps?.find((s) => s.status === "error")?.error_message;
              return errorMessage ? <Tooltip title={errorMessage}>{tag}</Tooltip> : tag;
            },
          },
          {
            title: t("llmImport.colReview", { defaultValue: "Duyệt" }),
            render: (_, v) =>
              v.review_status ? (
                <Tag color={REVIEW_COLOR[v.review_status]}>
                  {t(`llmImport.review.${v.review_status}`, { defaultValue: v.review_status })}
                </Tag>
              ) : (
                "—"
              ),
          },
          {
            title: t("llmImport.colCreated", { defaultValue: "Tạo lúc" }),
            dataIndex: "created_at",
            render: (value: string | null) => (value ? new Date(value).toLocaleString("vi-VN") : "—"),
          },
          ...(isAdmin
            ? [
                {
                  title: "",
                  key: "actions",
                  render: (_: unknown, v: ScanVersion) => {
                    const runStatus = engineRunStatus(v);
                    const canMakeCurrent = !v.is_current && (runStatus === null || runStatus === "done");
                    return (
                      <Space>
                        {canMakeCurrent && (
                          <Popconfirm
                            title={t("llmImport.makeCurrentConfirm", {
                              defaultValue: "Đặt v{{n}} làm phiên bản hiện tại? Tab Trích xuất và Trang sẽ hiện phiên bản này.",
                              n: v.version_number,
                            })}
                            okText={t("llmImport.makeCurrent", { defaultValue: "Đặt làm hiện tại" })}
                            onConfirm={() => void makeCurrent(v)}
                          >
                            <Button size="small" type="primary" ghost loading={busyVersion === v.version_id}>
                              {t("llmImport.makeCurrent", { defaultValue: "Đặt làm hiện tại" })}
                            </Button>
                          </Popconfirm>
                        )}
                        {v.source && (
                          <>
                        <Button
                          size="small"
                          icon={<CheckOutlined />}
                          disabled={v.review_status === "approved"}
                          loading={busyVersion === v.version_id}
                          onClick={() => void review(v.version_id, "approved")}
                        >
                          {t("llmImport.approve", { defaultValue: "Duyệt" })}
                        </Button>
                        <Button
                          size="small"
                          danger
                          icon={<CloseOutlined />}
                          disabled={v.review_status === "rejected"}
                          onClick={() => void review(v.version_id, "rejected")}
                        >
                          {t("llmImport.reject", { defaultValue: "Loại" })}
                        </Button>
                          </>
                        )}
                      </Space>
                    );
                  },
                },
              ]
            : []),
        ]}
      />

      <LlmImportModal
        scanId={scanId}
        open={open}
        onClose={() => setOpen(false)}
        onImported={() => {
          setOpen(false);
          void load();
        }}
      />
    </Space>
  );
}

function LlmImportModal({
  scanId,
  open,
  onClose,
  onImported,
}: {
  scanId: number;
  open: boolean;
  onClose: () => void;
  onImported: () => void;
}) {
  const { t } = useTranslation();
  const [records, setRecords] = useState<unknown[] | null>(null);
  const [fileName, setFileName] = useState<string>("");
  const [fileError, setFileError] = useState<string | null>(null);
  const [source, setSource] = useState("chatgpt-web");
  const [modelNote, setModelNote] = useState("");
  const [preview, setPreview] = useState<LlmImportResult | null>(null);
  const [checking, setChecking] = useState(false);
  const [saving, setSaving] = useState(false);

  useEffect(() => {
    if (!open) {
      setRecords(null);
      setFileName("");
      setFileError(null);
      setPreview(null);
    }
  }, [open]);

  const payload = (): LlmImportPayload => ({
    source: source.trim(),
    model_note: modelNote.trim() || undefined,
    records: (records ?? []) as LlmImportPayload["records"],
  });

  const onFile = async (file: File) => {
    setPreview(null);
    setFileName(file.name);
    try {
      const parsed = parseImportFile(await file.text());
      setRecords(parsed.records);
      setFileError(null);
      if (parsed.source) setSource(parsed.source);
      if (parsed.model_note) setModelNote(parsed.model_note);
    } catch (err) {
      setRecords(null);
      setFileError(err instanceof Error ? err.message : "Không đọc được file");
    }
  };

  const check = async () => {
    setChecking(true);
    try {
      setPreview(await importLlmResults(scanId, payload(), true));
    } catch (err) {
      message.error(err instanceof Error ? err.message : "Kiểm tra thất bại");
    } finally {
      setChecking(false);
    }
  };

  const confirm = async () => {
    setSaving(true);
    try {
      const result = await importLlmResults(scanId, payload(), false);
      message.success(
        t("llmImport.imported", {
          defaultValue: "Đã tạo phiên bản v{{n}} (chờ duyệt)",
          n: result.version?.version_number ?? "?",
        }),
      );
      onImported();
    } catch (err) {
      message.error(err instanceof Error ? err.message : "Nhập thất bại");
    } finally {
      setSaving(false);
    }
  };

  return (
    <Modal
      open={open}
      title={t("llmImport.importBtn", { defaultValue: "Nhập kết quả LLM" })}
      onCancel={onClose}
      okText={t("llmImport.confirm", { defaultValue: "Nhập" })}
      okButtonProps={{ disabled: !preview?.ok, loading: saving }}
      onOk={() => void confirm()}
      destroyOnHidden
    >
      <Space direction="vertical" className="w-full">
        <input
          type="file"
          accept=".json,.jsonl,application/json"
          aria-label={t("llmImport.file", { defaultValue: "File kết quả" })}
          onChange={(event) => {
            const file = event.target.files?.[0];
            if (file) void onFile(file);
          }}
        />
        {fileError && <Alert type="error" showIcon message={fileError} />}
        {records && (
          <Typography.Text type="secondary">
            {fileName}: {records.length} record
          </Typography.Text>
        )}
        <AutoComplete
          options={SOURCE_OPTIONS}
          value={source}
          onChange={(value) => {
            setSource(value);
            setPreview(null);
          }}
          placeholder="chatgpt-web"
          aria-label={t("llmImport.source", { defaultValue: "Nguồn" })}
        />
        <Input
          value={modelNote}
          onChange={(event) => setModelNote(event.target.value)}
          placeholder={t("llmImport.notePlaceholder", { defaultValue: "Ghi chú: model, phiên bản prompt…" })}
        />
        <Button onClick={() => void check()} disabled={!records} loading={checking}>
          {t("llmImport.check", { defaultValue: "Kiểm tra & xem trước" })}
        </Button>
        {preview && (
          <>
            <Typography.Text>
              {t("llmImport.summary", {
                defaultValue: "{{records}} câu trên {{pages}} trang, bỏ {{skipped}} câu [Chú giải].",
                records: preview.records,
                pages: preview.pages,
                skipped: preview.skipped_annotations,
              })}
            </Typography.Text>
            {preview.errors.length > 0 && (
              <Alert
                type="error"
                showIcon
                message={t("llmImport.errorsTitle", { defaultValue: "Lỗi — chưa nhập được" })}
                description={
                  <ul className="list-disc pl-5">
                    {preview.errors.map((e) => (
                      <li key={e}>{e}</li>
                    ))}
                  </ul>
                }
              />
            )}
            {preview.warnings.length > 0 && (
              <Alert
                type="warning"
                showIcon
                message={t("llmImport.warningsTitle", { defaultValue: "Cảnh báo — vẫn nhập được" })}
                description={
                  <ul className="list-disc pl-5">
                    {preview.warnings.map((w) => (
                      <li key={w}>{w}</li>
                    ))}
                  </ul>
                }
              />
            )}
          </>
        )}
      </Space>
    </Modal>
  );
}
