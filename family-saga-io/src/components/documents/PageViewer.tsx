import { FileImageOutlined } from "@ant-design/icons";
import { Alert, Card, Empty, Image, Pagination, Spin, Typography } from "antd";
import { useEffect, useState } from "react";
import { useTranslation } from "react-i18next";

import { listScanPages, type GiaPhaPageView } from "@/lib/userWorkspaceApi";

import "./ReaderWorkspace.css";

const { Text, Paragraph } = Typography;

/**
 * Xem từng trang của bộ gia phả: ảnh gốc (link tạm từ MinIO, bấm để phóng to)
 * cạnh chữ Hán / phiên âm / dịch nghĩa của version hiện tại. Chỉ chủ bộ hoặc
 * admin mở được (API trả 404 cho người khác).
 */
export function PageViewer({ scanId }: { scanId: number }) {
  const { t } = useTranslation();
  const [pages, setPages] = useState<GiaPhaPageView[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [index, setIndex] = useState(0);

  useEffect(() => {
    let cancelled = false;
    setLoading(true);
    listScanPages(scanId)
      .then((data) => {
        if (cancelled) return;
        setPages(data);
        setIndex(0);
      })
      .catch((err) => !cancelled && setError(err instanceof Error ? err.message : "Không tải được trang"))
      .finally(() => !cancelled && setLoading(false));
    return () => {
      cancelled = true;
    };
  }, [scanId]);

  if (loading) return <Spin className="flex justify-center py-12" />;
  if (error) return <Alert type="warning" showIcon message={error} />;
  if (pages.length === 0) {
    return <Empty description={t("pageViewer.noPages", { defaultValue: "Bộ này chưa có trang." })} />;
  }

  const page = pages[index];
  const withImages = pages.filter((p) => p.image_url).length;
  const texts: [string, string | null, string][] = [
    [t("pageViewer.hannom", { defaultValue: "Chữ Hán Nôm" }), page.hannom_text, "page-viewer-han"],
    [t("pageViewer.transliteration", { defaultValue: "Phiên âm" }), page.transliteration_text, ""],
    [t("pageViewer.translation", { defaultValue: "Dịch nghĩa" }), page.translation_text, ""],
  ];

  return (
    <div className="space-y-3">
      <div className="flex flex-wrap items-center justify-between gap-2">
        <Pagination
          simple
          current={index + 1}
          total={pages.length}
          pageSize={1}
          onChange={(value) => setIndex(value - 1)}
        />
        <Text type="secondary">
          {t("pageViewer.imageCount", {
            defaultValue: "{{n}}/{{total}} trang có ảnh",
            n: withImages,
            total: pages.length,
          })}
        </Text>
      </div>
      <div className="grid gap-4 md:grid-cols-2">
        <Card size="small" title={t("pageViewer.page", { defaultValue: "Trang {{n}}", n: page.page_number })}>
          {page.image_url ? (
            <Image src={page.image_url} alt={t("pageViewer.page", { defaultValue: "Trang {{n}}", n: page.page_number })} />
          ) : (
            <Empty
              image={<FileImageOutlined className="text-4xl text-muted-foreground" />}
              description={t("pageViewer.noImage", { defaultValue: "Chưa có ảnh cho trang này" })}
            />
          )}
        </Card>
        <Card size="small">
          {texts.map(([label, value, className]) => (
            <div key={label} className="mb-3">
              <Text strong>{label}</Text>
              {value ? (
                <Paragraph className={`whitespace-pre-wrap ${className}`}>{value}</Paragraph>
              ) : (
                <Paragraph type="secondary">{t("pageViewer.none", { defaultValue: "Chưa có" })}</Paragraph>
              )}
            </div>
          ))}
        </Card>
      </div>
    </div>
  );
}
