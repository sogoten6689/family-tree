import { useEffect, useState } from "react";
import { Alert, Button, Modal, Spin, Tag, Tooltip, Typography } from "antd";
import { useTranslation } from "react-i18next";

import { listPageEngines, runPageEngine, type PageEngineRunResult, type PageEngineStatus } from "@/lib/userWorkspaceApi";

type PageEnginesPanelProps = {
  scanId: number;
  pageNumber: number;
  /** Version sửa tay đang xem (undefined = version hiện tại). */
  versionId?: number;
  /** Tăng để tải lại (sau khi OCR lại / đổi version). */
  refreshKey?: number;
  onRan: (result: PageEngineRunResult) => void;
};

/**
 * OCR theo từng engine của 1 trang: engine nào đã có kết quả (xanh), engine nào chưa có (xám).
 * Engine chưa có mà server chạy được thì có nút "Chạy" (TỐN TIỀN, hỏi xác nhận); không chạy được
 * thì nói rõ vì sao. Kết quả chỉ thêm vào danh sách OCR theo engine, không đổi chữ chính.
 */
export function PageEnginesPanel({ scanId, pageNumber, versionId, refreshKey = 0, onRan }: PageEnginesPanelProps) {
  const { t } = useTranslation();
  const [engines, setEngines] = useState<PageEngineStatus[] | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;
    setEngines(null);
    setError(null);
    listPageEngines(scanId, pageNumber, versionId)
      .then((data) => !cancelled && setEngines(data))
      .catch((err) => !cancelled && setError(err instanceof Error ? err.message : "Không tải được danh sách engine"));
    return () => {
      cancelled = true;
    };
  }, [scanId, pageNumber, versionId, refreshKey]);

  const run = (engine: PageEngineStatus) => {
    Modal.confirm({
      title: t("pageEngines.confirmTitle", { defaultValue: "Chạy {{label}} cho trang {{n}}?", label: engine.label, n: pageNumber }),
      content: t("pageEngines.confirmBody", {
        defaultValue:
          "Việc này gọi dịch vụ OCR bên ngoài và TỐN TIỀN mỗi lần chạy. Kết quả chỉ thêm vào danh sách OCR theo engine (bản sửa tay), chữ chính của trang không đổi.",
      }),
      okText: t("pageEngines.confirmOk", { defaultValue: "Chạy (tốn tiền)" }),
      cancelText: t("pageViewer.cancel", { defaultValue: "Huỷ" }),
      onOk: async () => {
        setBusy(engine.name);
        setError(null);
        try {
          onRan(await runPageEngine(scanId, pageNumber, engine.name, { versionId }));
        } catch (err) {
          setError(err instanceof Error ? err.message : "Không chạy được engine");
        } finally {
          setBusy(null);
        }
      },
    });
  };

  if (engines === null && !error) return <Spin size="small" />;
  const have = engines?.filter((e) => e.present).length ?? 0;

  return (
    <div data-testid="page-engines" className="space-y-2">
      <Typography.Text type="secondary" className="text-xs">
        {t("pageEngines.summary", {
          defaultValue: "OCR theo engine: {{have}}/{{total}} engine có kết quả cho trang này",
          have,
          total: engines?.length ?? 0,
        })}
      </Typography.Text>
      {error && <Alert type="warning" showIcon closable message={error} onClose={() => setError(null)} />}
      <div className="flex flex-wrap gap-2">
        {engines?.map((engine) =>
          engine.present ? (
            <Tag key={engine.name} color="green">
              {engine.label} ✓
            </Tag>
          ) : (
            <span key={engine.name} className="inline-flex items-center gap-1">
              <Tag>{engine.label} — {t("pageEngines.missing", { defaultValue: "chưa có" })}</Tag>
              {engine.runnable && engine.ready ? (
                <Button size="small" loading={busy === engine.name} onClick={() => run(engine)}>
                  {t("pageEngines.run", { defaultValue: "Chạy" })}
                </Button>
              ) : (
                <Tooltip title={engine.reason || t("pageEngines.cannotRun", { defaultValue: "Server chưa chạy được engine này." })}>
                  <Button size="small" disabled>
                    {t("pageEngines.run", { defaultValue: "Chạy" })}
                  </Button>
                </Tooltip>
              )}
            </span>
          ),
        )}
      </div>
    </div>
  );
}
