import { Alert, Card, List, Space, Switch, Tag, Tooltip, Typography, message } from "antd";
import { useCallback, useEffect, useState } from "react";

import {
  canDisable,
  getOcrEngines,
  getTextEngines,
  updateOcrEngines,
  updateTextEngines,
  type OcrEngineConfig,
  type TextEngineConfig,
} from "@/lib/settingsApi";

type EngineToggleCardProps<C extends OcrEngineConfig> = {
  title: string;
  description: (config: C) => React.ReactNode;
  load: () => Promise<C>;
  save: (enabled: string[]) => Promise<C>;
  extra?: (config: C) => React.ReactNode;
  empty?: React.ReactNode;
  onSaved?: () => void;
};

/** Danh sách engine + công tắc, khoá công tắc khi tắt sẽ xuống dưới mức tối
 * thiểu (backend cũng chặn). Dùng chung cho engine OCR và phiên âm/dịch. */
function EngineToggleCard<C extends OcrEngineConfig>({
  title,
  description,
  load: loadConfig,
  save,
  extra,
  empty,
  onSaved,
}: EngineToggleCardProps<C>) {
  const [config, setConfig] = useState<C | null>(null);
  const [loading, setLoading] = useState(false);
  const [savingName, setSavingName] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

  const load = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      setConfig(await loadConfig());
    } catch (err) {
      setError(err instanceof Error ? err.message : "Không tải được danh sách engine");
    } finally {
      setLoading(false);
    }
  }, [loadConfig]);

  useEffect(() => {
    void load();
  }, [load]);

  const toggle = async (name: string, enabled: boolean) => {
    if (!config) return;
    const next = config.engines.filter((e) => (e.name === name ? enabled : e.enabled)).map((e) => e.name);
    setSavingName(name);
    try {
      setConfig(await save(next));
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
    <Card title={title} loading={loading && !config}>
      {error && <Alert type="warning" showIcon className="mb-4" message={error} />}
      {config && (
        <Space direction="vertical" className="w-full">
          <Typography.Text type="secondary">{description(config)}</Typography.Text>
          {extra?.(config)}
          {config.engines.length === 0 && empty}
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

/**
 * Bật/tắt engine OCR cho pipeline v2 (lưu vào HANNOM_VOTE_ENGINES). Chỉ Admin,
 * áp dụng toàn hệ thống, luôn giữ ≥ min_enabled engine. Bước dịch nghĩa và
 * trích xuất cây không bị ảnh hưởng (vẫn dùng Gemini).
 */
export function OcrEnginesCard({ onSaved }: { onSaved?: () => void }) {
  return (
    <EngineToggleCard<OcrEngineConfig>
      title="Engine OCR (pipeline v2)"
      load={getOcrEngines}
      save={updateOcrEngines}
      onSaved={onSaved}
      description={(config) =>
        `Bắt buộc bật ít nhất ${config.min_enabled} engine. Với 1–2 engine, kết quả = nguyên văn engine chính (backbone); cần ≥3 engine mới vote từng dòng thật sự. Dịch nghĩa và trích xuất cây không bị ảnh hưởng.`
      }
    />
  );
}

/**
 * Bật/tắt engine phiên âm + dịch nghĩa (lưu vào HANNOM_TEXT_ENGINES). Engine
 * do người dùng tự đăng ký trong app/hannom/text_engines_local.py ở backend.
 */
export function TextEnginesCard({ onSaved }: { onSaved?: () => void }) {
  return (
    <EngineToggleCard<TextEngineConfig>
      title="Engine phiên âm / dịch nghĩa"
      load={getTextEngines}
      save={updateTextEngines}
      onSaved={onSaved}
      description={(config) =>
        `Engine tự đăng ký ở backend (app/hannom/text_engines_local.py). Bắt buộc bật ít nhất ${config.min_enabled} engine khi đã có engine. Người dùng chạy từ tab "Phiên bản & nhập LLM" của bộ gia phả.`
      }
      extra={(config) =>
        config.load_error ? (
          <Alert
            type="error"
            showIcon
            message="Lỗi khi nạp text_engines_local.py"
            description={<pre className="whitespace-pre-wrap text-xs">{config.load_error}</pre>}
          />
        ) : null
      }
      empty={
        <Alert
          type="info"
          showIcon
          message="Chưa có engine nào được đăng ký"
          description="Tạo app/hannom/text_engines_local.py và gọi register_text_engine(tên, hàm) rồi khởi động lại backend."
        />
      }
    />
  );
}
