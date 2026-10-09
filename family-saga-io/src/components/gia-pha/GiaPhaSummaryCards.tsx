import { useRef } from "react";
import { useQuery } from "@tanstack/react-query";
import { Alert, Button, Card, Col, Progress, Row, Skeleton, Tag, Tooltip, Typography } from "antd";
import {
  ApartmentOutlined,
  BookOutlined,
  ClockCircleOutlined,
  NumberOutlined,
  ReloadOutlined,
  TeamOutlined,
} from "@ant-design/icons";
import { useTranslation } from "react-i18next";
import type { ReactNode } from "react";

import { getGiaPhaSummary, type GiaPhaSummary } from "@/lib/giaPhaApi";

/** Cache phía trình duyệt: dùng chung khoá cho /gia-pha và các trang Tổng quan nên chuyển qua lại là có ngay. */
export const GIA_PHA_SUMMARY_KEY = ["gia-pha-summary"] as const;
const STALE_MS = 30_000; // bằng TTL cache của server

const number = (value: number) => value.toLocaleString("vi-VN");

export function StatTile({ icon, label, value, hint }: { icon: ReactNode; label: string; value: ReactNode; hint?: ReactNode }) {
  return (
    <Card size="small" className="h-full border-[hsl(var(--border))]">
      <div className="flex items-center gap-3">
        <div
          className="flex h-9 w-9 shrink-0 items-center justify-center rounded-xl text-lg sm:h-11 sm:w-11 sm:text-xl"
          style={{ background: "hsl(var(--accent))", color: "hsl(var(--primary))" }}
          aria-hidden
        >
          {icon}
        </div>
        <div className="min-w-0">
          <div className="text-xs leading-snug text-muted-foreground">{label}</div>
          <div className="text-2xl font-semibold leading-tight">{value}</div>
          {hint && <div className="text-xs leading-snug text-muted-foreground">{hint}</div>}
        </div>
      </div>
    </Card>
  );
}

function CodeSourceBar({ summary }: { summary: GiaPhaSummary }) {
  const { t } = useTranslation();
  const segments = [
    { key: "catalogue", label: t("maDinhDanh.sourceCatalogue", { defaultValue: "Đã chốt" }), value: summary.code_source.catalogue, color: "hsl(var(--primary))" },
    { key: "gemini", label: t("maDinhDanh.sourceGemini", { defaultValue: "Tự tạo (Gemini)" }), value: summary.code_source.gemini, color: "hsl(var(--primary) / 0.55)" },
    { key: "other", label: t("giaPhaSummary.codeOther", { defaultValue: "Nguồn khác" }), value: summary.code_source.other, color: "hsl(var(--primary) / 0.3)" },
    { key: "none", label: t("giaPhaSummary.codeNone", { defaultValue: "Chưa có mã" }), value: summary.without_code, color: "hsl(var(--muted-foreground) / 0.35)" },
  ].filter((segment) => segment.value > 0);
  return (
    <div>
      <div className="flex h-3 w-full overflow-hidden rounded-full bg-muted" role="img" aria-label={t("giaPhaSummary.codeSources", { defaultValue: "Nguồn mã định danh" })}>
        {segments.map((segment) => (
          <Tooltip key={segment.key} title={`${segment.label}: ${number(segment.value)}`}>
            <div style={{ width: `${(segment.value / Math.max(summary.total, 1)) * 100}%`, background: segment.color }} />
          </Tooltip>
        ))}
      </div>
      <div className="mt-3 flex flex-wrap gap-x-4 gap-y-1 text-xs text-muted-foreground">
        {segments.map((segment) => (
          <span key={segment.key} className="inline-flex items-center gap-1.5">
            <span className="inline-block h-2.5 w-2.5 rounded-full" style={{ background: segment.color }} />
            {segment.label} <strong className="text-foreground">{number(segment.value)}</strong>
          </span>
        ))}
      </div>
    </div>
  );
}

interface GiaPhaSummaryCardsProps {
  /** compact: chỉ hàng thẻ số (dùng đầu trang /gia-pha). Mặc định đầy đủ (Tổng quan). */
  compact?: boolean;
  className?: string;
}

/**
 * Thống kê tóm tắt Gia phả cho phạm vi người xem (khách / user / admin). Dữ liệu do backend tổng hợp
 * và cache 30 giây; React Query cache thêm 30 giây phía trình duyệt. Nút làm mới bỏ qua cả hai.
 */
export function GiaPhaSummaryCards({ compact = false, className }: GiaPhaSummaryCardsProps) {
  const { t } = useTranslation();
  const forceRefresh = useRef(false);
  const { data, error, isLoading, isFetching, refetch } = useQuery({
    queryKey: GIA_PHA_SUMMARY_KEY,
    queryFn: () => {
      const refresh = forceRefresh.current;
      forceRefresh.current = false;
      return getGiaPhaSummary(refresh);
    },
    staleTime: STALE_MS,
  });

  if (isLoading) {
    return (
      <div className={className} data-testid="gia-pha-summary-loading">
        <Row gutter={[16, 16]}>
          {[0, 1, 2, 3].map((i) => (
            <Col xs={12} lg={6} key={i}>
              <Card size="small"><Skeleton active avatar paragraph={{ rows: 1 }} title={false} /></Card>
            </Col>
          ))}
        </Row>
      </div>
    );
  }
  if (error || !data) {
    return (
      <Alert
        className={className}
        type="warning"
        showIcon
        message={t("giaPhaSummary.error", { defaultValue: "Không tải được thống kê" })}
        action={<Button size="small" onClick={() => void refetch()}>{t("familyTree.reload", { defaultValue: "Tải lại" })}</Button>}
      />
    );
  }

  const builtPercent = data.total > 0 ? Math.round((data.built / data.total) * 100) : 0;
  const reload = () => {
    forceRefresh.current = true;
    void refetch();
  };
  const maxHo = Math.max(...data.top_ho_toc.map((item) => item.count), 1);

  return (
    <div className={className}>
      <div className="mb-3 flex flex-wrap items-center justify-between gap-2">
        <Typography.Text type="secondary" className="text-xs">
          {t("giaPhaSummary.updatedAt", { defaultValue: "Cập nhật {{time}}", time: new Date(data.generated_at).toLocaleTimeString("vi-VN") })}
        </Typography.Text>
        <Button size="small" type="text" icon={<ReloadOutlined />} loading={isFetching} onClick={reload}>
          {t("giaPhaSummary.refresh", { defaultValue: "Làm mới số liệu" })}
        </Button>
      </div>

      <Row gutter={[16, 16]}>
        <Col xs={12} lg={6}>
          <StatTile icon={<BookOutlined />} label={t("giaPhaSummary.total", { defaultValue: "Tổng số bộ gia phả" })} value={number(data.total)} />
        </Col>
        <Col xs={12} lg={6}>
          <StatTile
            icon={<ApartmentOutlined />}
            label={t("giaPhaSummary.built", { defaultValue: "Đã dựng cây" })}
            value={number(data.built)}
            hint={t("giaPhaSummary.builtHint", { defaultValue: "{{percent}}% tổng số bộ", percent: builtPercent })}
          />
        </Col>
        <Col xs={12} lg={6}>
          <StatTile
            icon={<ClockCircleOutlined />}
            label={t("giaPhaSummary.pending", { defaultValue: "Chờ dựng cây" })}
            value={number(data.pending)}
          />
        </Col>
        <Col xs={12} lg={6}>
          <StatTile
            icon={<NumberOutlined />}
            label={t("giaPhaSummary.withCode", { defaultValue: "Có mã định danh" })}
            value={`${number(data.with_code)}/${number(data.total)}`}
            hint={
              data.scope === "public"
                ? undefined
                : t("giaPhaSummary.nodesHint", { defaultValue: "{{n}} nhân vật trong các cây", n: number(data.nodes) })
            }
          />
        </Col>
      </Row>

      {!compact && (
        <Row gutter={[16, 16]} className="!mt-4">
          {data.pages && (
            <Col xs={24} lg={10}>
              <Card
                size="small"
                className="h-full border-[hsl(var(--border))]"
                title={t("giaPhaSummary.progressTitle", { defaultValue: "Tiến độ xử lý văn bản" })}
                extra={<Tag>{t("giaPhaSummary.pagesTotal", { defaultValue: "{{n}} trang", n: number(data.pages.pages) })}</Tag>}
              >
                {[
                  { key: "ocr", label: t("giaPhaSummary.ocr", { defaultValue: "Chữ Hán (OCR)" }), percent: data.pages.ocr_percent, count: data.pages.ocr_pages },
                  { key: "translit", label: t("giaPhaSummary.translit", { defaultValue: "Phiên âm" }), percent: data.pages.transliteration_percent, count: data.pages.transliteration_pages },
                  { key: "translation", label: t("giaPhaSummary.translation", { defaultValue: "Dịch nghĩa" }), percent: data.pages.translation_percent, count: data.pages.translation_pages },
                ].map((row) => (
                  <div key={row.key} className="mb-3 last:mb-0">
                    <div className="mb-1 flex items-baseline justify-between text-xs">
                      <span>{row.label}</span>
                      <span className="text-muted-foreground">
                        {number(row.count)}/{number(data.pages!.pages)} {t("giaPhaSummary.pageUnit", { defaultValue: "trang" })}
                      </span>
                    </div>
                    <Progress percent={row.percent} size="small" aria-label={row.label} />
                  </div>
                ))}
              </Card>
            </Col>
          )}
          <Col xs={24} lg={data.pages ? 7 : 12}>
            <Card size="small" className="h-full border-[hsl(var(--border))]" title={t("giaPhaSummary.codeSources", { defaultValue: "Nguồn mã định danh" })}>
              <CodeSourceBar summary={data} />
            </Card>
          </Col>
          <Col xs={24} lg={data.pages ? 7 : 12}>
            <Card
              size="small"
              className="h-full border-[hsl(var(--border))]"
              title={t("giaPhaSummary.topHo", { defaultValue: "Họ tộc nhiều bộ nhất" })}
              extra={<TeamOutlined />}
            >
              {data.top_ho_toc.length === 0 ? (
                <Typography.Text type="secondary">{t("giaPhaSummary.noHo", { defaultValue: "Chưa có dữ liệu họ tộc" })}</Typography.Text>
              ) : (
                data.top_ho_toc.map((item) => (
                  <div key={item.ho_toc} className="mb-2 last:mb-0">
                    <div className="mb-0.5 flex justify-between text-xs">
                      <span>{item.ho_toc}</span>
                      <strong>{number(item.count)}</strong>
                    </div>
                    <div className="h-2 overflow-hidden rounded-full bg-muted">
                      <div className="h-full rounded-full" style={{ width: `${(item.count / maxHo) * 100}%`, background: "hsl(var(--primary))" }} />
                    </div>
                  </div>
                ))
              )}
            </Card>
          </Col>
        </Row>
      )}
    </div>
  );
}

export default GiaPhaSummaryCards;
