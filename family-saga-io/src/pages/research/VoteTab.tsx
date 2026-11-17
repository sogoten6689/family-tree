import { useQuery } from "@tanstack/react-query";
import { Alert, Button, Image, Popover, Radio, Space, Spin, Statistic, Table, Tag, Tooltip, Typography } from "antd";
import type { ColumnsType } from "antd/es/table";
import { useMemo, useState } from "react";

import { getVote, pageImageUrl, type BookDetail, type VoteChar, type VoteKind, type VotePage, type VoteSummary } from "@/lib/doiChieuApi";

export const VOTE_LABEL: Record<VoteKind, string> = {
  dong_y: "Mọi phiếu đồng ý",
  de_xuat_sua: "Đề xuất sửa",
  can_soat: "Cần soát",
  soat_tay_dong_ngan: "Dòng ngắn cần soát",
  mot_phieu: "Chỉ bản nền (máy khác không đọc được chữ này)",
};

const KIND_STYLE: Record<VoteKind, { background?: string; color?: string }> = {
  dong_y: {},
  de_xuat_sua: { background: "#ffccc7" },
  can_soat: { background: "#ffe58f" },
  soat_tay_dong_ngan: { background: "#ffe58f" },
  mot_phieu: { color: "#8c8c8c" },
};

const pct = (x: number | null) => (x == null ? "—" : `${Math.round(x * 100)}%`);

export interface VoteRow {
  key: string;
  page: string;
  line: number;
  text: string;
  /** Chữ bị đánh dấu theo vị trí; dòng ngắn đánh dấu cả dòng. */
  marks: Map<number, VoteChar>;
  kinds: Set<VoteKind>;
  pageReview: boolean;
  paddle?: number;
  voters: number;
}

export type VoteFilter = "de_xuat_sua" | "can_soat" | "issues" | "page_review";

export const flattenVote = (pages: VotePage[]): VoteRow[] =>
  pages.flatMap((p) =>
    p.dong.map((d, i) => {
      const marks = new Map<number, VoteChar>();
      const kinds = new Set<VoteKind>();
      if (d.kq) {
        kinds.add(d.kq);
        if (d.kq !== "dong_y") [...d.nen].forEach((ch, j) => marks.set(j, { vi_tri: j, nen: ch, phieu: {}, kq: d.kq! }));
      }
      for (const c of d.chu ?? []) {
        marks.set(c.vi_tri, c);
        kinds.add(c.kq);
      }
      return {
        key: `${p.page_id}:${i}`,
        page: p.page_id,
        line: i + 1,
        text: d.nen,
        marks,
        kinds,
        pageReview: !!p.trang_soat_tay,
        paddle: p.paddle_khop,
        voters: p.so_phieu,
      };
    }),
  );

export const filterVote = (rows: VoteRow[], f: VoteFilter) =>
  rows.filter((r) =>
    f === "page_review"
      ? r.pageReview
      : f === "issues"
        ? r.kinds.has("de_xuat_sua") || r.kinds.has("can_soat") || r.kinds.has("soat_tay_dong_ngan")
        : f === "can_soat"
          ? r.kinds.has("can_soat") || r.kinds.has("soat_tay_dong_ngan")
          : r.kinds.has(f),
  );

const votesText = (c: VoteChar) =>
  Object.entries(c.phieu)
    .sort((a, b) => b[1] - a[1])
    .map(([ch, n]) => `${ch}×${n}`)
    .join(" · ");

const MarkedLine = ({ row }: { row: VoteRow }) => (
  <span lang="zh-Hant" style={{ fontSize: 16 }}>
    {[...row.text].map((ch, i) => {
      const m = row.marks.get(i);
      if (!m) return <span key={i}>{ch}</span>;
      const tip = `${VOTE_LABEL[m.kq]}${Object.keys(m.phieu).length ? `: ${votesText(m)}` : ""}`;
      return (
        <Tooltip key={i} title={tip}>
          <mark style={{ padding: 0, ...KIND_STYLE[m.kq], ...(KIND_STYLE[m.kq].background ? {} : { background: "transparent" }) }}>{ch}</mark>
        </Tooltip>
      );
    })}
  </span>
);

const SuggestList = ({ row }: { row: VoteRow }) => {
  const items = [...row.marks.values()].filter((c) => c.kq === "de_xuat_sua" || (c.kq === "can_soat" && Object.keys(c.phieu).length > 1));
  if (!items.length) return null;
  return (
    <Space size={4} wrap>
      {items.map((c) => (
        <Tag key={c.vi_tri} color={c.kq === "de_xuat_sua" ? "red" : "gold"} lang="zh-Hant">
          {c.nen} → {votesText(c)}
        </Tag>
      ))}
    </Space>
  );
};

export const VoteStats = ({ s }: { s: VoteSummary }) => (
  <Space wrap size="large">
    <Statistic title="Trang đã vote" value={s.pages} />
    <Statistic title="Chữ" value={s.chars} />
    <Statistic title="Đồng ý (chữ ≥ 2 phiếu)" value={pct(s.agree_rate)} />
    <Statistic title="Đề xuất sửa" value={s.de_xuat_sua} />
    <Statistic title="Cần soát" value={s.can_soat + s.soat_tay_dong_ngan} />
    <Statistic title="Trang soát tay" value={s.pages_review} />
    <Statistic title="Chữ chỉ có bản nền" value={s.mot_phieu} />
  </Space>
);

const VoteTab = ({ detail }: { detail: BookDetail }) => {
  const { data, error, isLoading } = useQuery({
    queryKey: ["doi-chieu", detail.student, detail.book, "vote"],
    queryFn: () => getVote(detail.student, detail.book),
    enabled: !!detail.vote,
  });
  const [filter, setFilter] = useState<VoteFilter>("de_xuat_sua");
  const rows = useMemo(() => (data ? flattenVote(data.pages) : []), [data]);
  const shown = useMemo(() => filterVote(rows, filter), [rows, filter]);
  const hasImages = useMemo(() => new Set(detail.pages), [detail.pages]);

  if (!detail.vote) return <Typography.Text type="secondary">Cuốn này chưa có kết quả vote OCR.</Typography.Text>;
  if (error) return <Alert type="error" showIcon title="Không tải được kết quả vote" description={String(error)} />;

  const columns: ColumnsType<VoteRow> = [
    {
      title: "Trang",
      width: 80,
      render: (_, r) =>
        hasImages.has(r.page) ? (
          <Popover trigger="click" placement="right" content={<Image width={360} src={pageImageUrl(detail.student, detail.book, r.page)} alt={`Trang ${r.page}`} />}>
            <Button size="small" type="link" style={{ padding: 0 }}>
              tr.{r.page}
            </Button>
          </Popover>
        ) : (
          `tr.${r.page}`
        ),
    },
    { title: "Dòng", dataIndex: "line", width: 60 },
    { title: "Chữ nền (tô màu chỗ bất đồng)", render: (_, r) => <MarkedLine row={r} /> },
    { title: "Phiếu", render: (_, r) => <SuggestList row={r} /> },
    {
      title: "Thông tin trang",
      width: 150,
      render: (_, r) => (
        <Space orientation="vertical" size={0}>
          <Typography.Text type="secondary" style={{ fontSize: 12 }}>
            {r.voters} phiếu{r.paddle != null ? ` · Paddle khớp ${pct(r.paddle)}` : ""}
          </Typography.Text>
          {r.pageReview && <Tag color="purple">soát tay cả trang</Tag>}
        </Space>
      ),
    },
  ];

  return (
    <Space orientation="vertical" style={{ width: "100%" }}>
      <VoteStats s={detail.vote} />
      <Typography.Paragraph type="secondary" style={{ margin: 0 }}>
        Chữ nền là bản OCR đang dùng; các engine OCR khác (kể cả PaddleOCR chạy trên máy lab) bỏ phiếu từng chữ, so sau khi quy dị thể.{" "}
        <mark style={{ background: "#ffccc7", padding: 0 }}>Đỏ</mark>: đa số phiếu (≥ 2, trên tổng ≥ 3) chọn chữ khác chữ nền.{" "}
        <mark style={{ background: "#ffe58f", padding: 0 }}>Vàng</mark>: phiếu bất đồng, cần xem ảnh. Máy nào không ghép được chữ ở vị trí đó thì tính phiếu trắng, không tính là bất đồng; xám: không máy nào khác đọc được chữ đó, chỉ có bản nền. Trang Paddle khớp
        dưới 50% (sơ đồ cây, chữ viết tay) không lấy phiếu Paddle và cần soát tay. Đây là gợi ý để soát, chưa sửa vào dữ liệu.
      </Typography.Paragraph>
      <Radio.Group
        value={filter}
        onChange={(e) => setFilter(e.target.value)}
        optionType="button"
        options={[
          { value: "de_xuat_sua", label: `Đề xuất sửa` },
          { value: "can_soat", label: "Cần soát" },
          { value: "issues", label: "Mọi dòng có vấn đề" },
          { value: "page_review", label: "Trang soát tay" },
        ]}
      />
      {isLoading ? (
        <Spin />
      ) : (
        <Table rowKey="key" size="small" columns={columns} dataSource={shown} pagination={{ pageSize: 50, showSizeChanger: false }} />
      )}
    </Space>
  );
};

export default VoteTab;
