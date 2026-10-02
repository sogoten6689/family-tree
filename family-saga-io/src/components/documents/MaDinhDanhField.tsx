import { ThunderboltOutlined } from "@ant-design/icons";
import { Alert, Button, Space, Tag, Tooltip, Typography } from "antd";
import { useState } from "react";
import { useTranslation } from "react-i18next";

import { autoMaDinhDanh, type UserScan } from "@/lib/userWorkspaceApi";

/**
 * Mã định danh của 1 bộ gia phả + nguồn của mã. Chưa có mã → nút tự tạo:
 * Gemini trích quy mô/hình thức/họ/địa danh/năm soạn từ bản dịch, số thứ tự
 * đánh riêng theo chữ A–V (1 lượt gọi Gemini, tốn phí). Mã đã có không đổi.
 */
export function MaDinhDanhField({ scan, onChanged }: { scan: UserScan; onChanged: () => void }) {
  const { t } = useTranslation();
  const [busy, setBusy] = useState(false);
  const [problems, setProblems] = useState<string[]>([]);

  const run = async () => {
    setBusy(true);
    setProblems([]);
    try {
      const result = await autoMaDinhDanh(scan.id);
      setProblems(result.problems);
      if (result.ma_dinh_danh) onChanged();
    } catch (err) {
      setProblems([err instanceof Error ? err.message : "Không tạo được mã"]);
    } finally {
      setBusy(false);
    }
  };

  if (scan.ma_dinh_danh) {
    return (
      <Space wrap>
        <Typography.Text code>{scan.ma_dinh_danh}</Typography.Text>
        {scan.ma_dinh_danh_nguon === "gemini" ? (
          <Tooltip
            title={t("maDinhDanh.geminiHint", {
              defaultValue: "Tự tạo từ thông tin Gemini trích ở bản dịch — nên đối chiếu lại khi đọc.",
            })}
          >
            <Tag color="gold">{t("maDinhDanh.sourceGemini", { defaultValue: "Tự tạo (Gemini)" })}</Tag>
          </Tooltip>
        ) : scan.ma_dinh_danh_nguon === "catalogue" ? (
          <Tag color="blue">{t("maDinhDanh.sourceCatalogue", { defaultValue: "Đã chốt" })}</Tag>
        ) : null}
      </Space>
    );
  }

  const hasText = Boolean(scan.source_text || scan.transliteration_text);
  return (
    <Space direction="vertical" className="w-full">
      <Space wrap>
        <Typography.Text type="secondary">{t("maDinhDanh.none", { defaultValue: "Chưa có mã" })}</Typography.Text>
        <Tooltip
          title={
            hasText
              ? t("maDinhDanh.autoHint", { defaultValue: "Gọi Gemini 1 lần (tốn phí) để trích thông tin và tạo mã." })
              : t("maDinhDanh.needText", { defaultValue: "Cần có bản dịch/phiên âm trước." })
          }
        >
          <Button size="small" icon={<ThunderboltOutlined />} loading={busy} disabled={!hasText} onClick={() => void run()}>
            {t("maDinhDanh.autoBtn", { defaultValue: "Tạo mã tự động" })}
          </Button>
        </Tooltip>
      </Space>
      {problems.length > 0 && (
        <Alert
          type="warning"
          showIcon
          message={t("maDinhDanh.failed", { defaultValue: "Chưa tạo được mã" })}
          description={
            <ul className="list-disc pl-5">
              {problems.map((p) => (
                <li key={p}>{p}</li>
              ))}
            </ul>
          }
        />
      )}
    </Space>
  );
}
