import { Alert, Card, List, Space, Switch, Tag, Tooltip, Typography, message } from "antd";
import { useCallback, useEffect, useState } from "react";

import { canDisable, getOcrEngines, updateOcrEngines, type OcrEngineConfig } from "@/lib/settingsApi";

/**
 * Bật/tắt engine OCR cho pipeline v2 (lưu vào HANNOM_VOTE_ENGINES). Chỉ Admin,
 * áp dụng toàn hệ thống, luôn giữ ≥ min_enabled engine. Bước dịch nghĩa và
 * trích xuất cây không bị ảnh hưởng (vẫn dùng Gemini).
 */
export function OcrEnginesCard({ onSaved }: { onSaved?: () => void }) {
  const [config, setConfig] = useState<OcrEngineConfig | null>(null);
  const [loading, setLoading] = useState(false);
  const [savingName, setSavingName] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

  const load = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      setConfig(await getOcrEngines());
    } catch (err) {
      setError(err instanceof Error ? err.message : "Không tải được danh sách engine");
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    void load();
  }, [load]);

  const toggle = async (name: string, enabled: boolean) => {
    if (!config) return;
    const next = config.engines.filter((e) => (e.name === name ? enabled : e.enabled)).map((e) => e.name);
    setSavingName(name);
    try {
      setConfig(await updateOcrEngines(next));
      message.success(`Đã ${enabled ? "bật" : "tắt"} ${name}`);
      onSaved?.();
    } catch (err) {
      message.error(err instanceof Error ? err.message : "Lưu thất bại");
    } finally {
      setSavingName(null);
    }
  };

  const enabledCount = config?.engines.filter((e) => e.enabled).length ?? 0;

  return (
    <Card title="Engine OCR (pipeline v2)" loading={loading && !config}>
      {error && <Alert type="warning" showIcon className="mb-4" message={error} />}
      {config && (
        <Space direction="vertical" className="w-full">
          <Typography.Text type="secondary">
            Bắt buộc bật ít nhất {config.min_enabled} engine. Với 1–2 engine, kết quả = nguyên văn engine chính
            (backbone); cần ≥3 engine mới vote từng dòng thật sự. Dịch nghĩa và trích xuất cây không bị ảnh hưởng.
          </Typography.Text>
          <List
            dataSource={config.engines}
            renderItem={(engine) => {
              const locked = !canDisable(config, engine.name);
              const toggleSwitch = (
                <Switch
                  checked={engine.enabled}
                  disabled={locked || savingName !== null}
                  loading={savingName === engine.name}
                  onChange={(checked) => void toggle(engine.name, checked)}
                  aria-label={`Bật/tắt ${engine.label}`}
                />
              );
              return (
                <List.Item
                  actions={[
                    locked ? (
                      <Tooltip key="sw" title={`Không thể tắt — phải bật ít nhất ${config.min_enabled} engine`}>
                        <span>{toggleSwitch}</span>
                      </Tooltip>
                    ) : (
                      <span key="sw">{toggleSwitch}</span>
                    ),
                  ]}
                >
                  <List.Item.Meta
                    title={
                      <Space>
                        {engine.label}
                        <Typography.Text code>{engine.name}</Typography.Text>
                      </Space>
                    }
                    description={
                      engine.ready ? (
                        <Tag color="green">Sẵn sàng</Tag>
                      ) : (
                        <Tooltip title={engine.ready_reason}>
                          <Tag color="gold">Chưa cấu hình</Tag>
                        </Tooltip>
                      )
                    }
                  />
                </List.Item>
              );
            }}
          />
          <Typography.Text type="secondary">Đang bật {enabledCount}/{config.engines.length} engine.</Typography.Text>
        </Space>
      )}
    </Card>
  );
}
