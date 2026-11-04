import { useQuery } from "@tanstack/react-query";
import { Alert, Button, Card, Image, Pagination, Popover, Progress, Radio, Select, Space, Statistic, Table, Tabs, Tag, Typography } from "antd";
import type { ColumnsType } from "antd/es/table";
import { useEffect, useMemo, useState } from "react";
import { Link, useSearchParams } from "react-router-dom";

import {
  getBook,
  getOverview,
  pageImageUrl,
  type AlignedPair,
  type BookDetail,
  type BookSummary,
  type MissingRow,
  type StudentSummary,
} from "@/lib/doiChieuApi";
import { useAuth } from "@/contexts/AuthContext";

import {
  VERDICT_LABEL,
  loadVerdicts,
  markChangedChars,
  sampleLines,
  saveVerdicts,
  storageKey,
  summarize,
  toCsv,
  type Verdict,
} from "./doiChieuGrading";
import SoatTab from "./SoatTab";

const pct = (x: number | null | undefined) => (x == null ? "—" : `${Math.round(x * 100)}%`);

const coverageColor = (c: number) => (c >= 0.7 ? "green" : c >= 0.4 ? "gold" : "red");

const HanWithChanges = ({ han, ocr }: { han: string; ocr: string }) => (
  <span lang="zh-Hant" style={{ fontSize: 16 }}>
    {markChangedChars(han, ocr).map((c, i) =>
      c.changed ? (
        <mark key={i} title="Chữ không có trong đoạn OCR tương ứng" style={{ background: "#ffe58f", padding: 0 }}>
          {c.ch}
        </mark>
      ) : (
        <span key={i}>{c.ch}</span>
      ),
    )}
  </span>
);

const PageLinks = ({ student, book, pages }: { student: string; book: string; pages: string[] }) => (
  <Space size={4} wrap>
    {pages.map((p) => (
      <Popover key={p} trigger="click" placement="left" content={<Image width={360} src={pageImageUrl(student, book, p)} alt={`Trang ${p}`} />}>
        <Button size="small" type="link" style={{ padding: 0 }}>
          tr.{p}
        </Button>
      </Popover>
    ))}
  </Space>
);

const studentColumns = (target: number): ColumnsType<StudentSummary> => [
  { title: "Sinh viên", dataIndex: "ten" },
  { title: "Cuốn đã nộp", render: (_, s) => `${s.submitted}/${s.books.length}` },
  {
    title: `Cặp hợp lệ / ${target.toLocaleString("vi-VN")}`,
    render: (_, s) => (
      <Space>
        <Progress percent={Math.min(100, Math.round((s.valid / target) * 100))} size="small" style={{ width: 140 }} />
        <span>{s.valid.toLocaleString("vi-VN")}</span>
      </Space>
    ),
    sorter: (a, b) => a.valid - b.valid,
  },
  {
    title: "Lỗi định dạng",
    dataIndex: "format_errors",
    render: (n: number) => (n ? <Tag color="red">{n}</Tag> : <Tag color="green">0</Tag>),
  },
];

const SourceLink = ({ link }: { link: string | null }) =>
  link ? (
    <a href={link} target="_blank" rel="noreferrer">
      Bản gốc ↗
    </a>
  ) : (
    <Typography.Text type="secondary">bản gốc trong gói lab</Typography.Text>
  );

const bookColumns = (onOpen: (book: string) => void): ColumnsType<BookSummary> => [
  {
    title: "Cuốn",
    render: (_, b) => (
      <Space orientation="vertical" size={0}>
        <span>{b.ten ?? b.id}</span>
        <Typography.Text type="secondary" style={{ fontSize: 12 }}>
          {b.id} · <SourceLink link={b.link} />
        </Typography.Text>
      </Space>
    ),
  },
  { title: "Tệp nộp", dataIndex: "tsv", render: (t: string | null) => t ?? <Typography.Text type="secondary">chưa nộp</Typography.Text> },
  { title: "Cặp", dataIndex: "pairs" },
  { title: "Hợp lệ", dataIndex: "valid" },
  { title: "Lỗi định dạng", dataIndex: "format_errors" },
  { title: "Trang có bản máy", dataIndex: "machine_pages" },
  { title: "Ảnh trang", dataIndex: "image_pages" },
  {
    title: "Độ phủ OCR",
    dataIndex: "ocr_coverage",
    render: (c: number | null) => pct(c),
  },
  {
    title: "",
    render: (_, b) => (
      <Button size="small" disabled={!b.tsv && !b.machine_rows && !b.image_pages} onClick={() => onOpen(b.id)}>
        {b.tsv || b.machine_rows ? "Đối chiếu" : "Xem ảnh"}
      </Button>
    ),
  },
];

type PairFilter = "all" | "errors" | "low";

const PairsTab = ({ detail }: { detail: BookDetail }) => {
  const [filter, setFilter] = useState<PairFilter>("all");
  const rows = detail.pairs.filter((p) =>
    filter === "errors" ? p.errors.length > 0 : filter === "low" ? p.coverage < 0.5 : true,
  );
  const columns: ColumnsType<AlignedPair> = [
    { title: "Dòng", dataIndex: "line", width: 60 },
    {
      title: "Hán (sinh viên)",
      width: "26%",
      render: (_, p) => (
        <>
          <HanWithChanges han={p.han} ocr={p.may_han} />
          {p.errors.map((e) => (
            <Tag key={e} color="red" style={{ marginTop: 4 }}>
              {e}
            </Tag>
          ))}
        </>
      ),
    },
    { title: "Việt (sinh viên)", dataIndex: "viet", width: "30%" },
    {
      title: "Bản máy (OCR + dịch máy)",
      width: "30%",
      render: (_, p) =>
        p.may_han ? (
          <>
            <Typography.Paragraph type="secondary" lang="zh-Hant" style={{ margin: 0 }} ellipsis={{ rows: 2, expandable: true }}>
              {p.may_han}
            </Typography.Paragraph>
            <Typography.Paragraph style={{ margin: 0 }} ellipsis={{ rows: 3, expandable: true }}>
              {p.may_viet}
            </Typography.Paragraph>
          </>
        ) : (
          <Typography.Text type="secondary">không tìm thấy trong OCR</Typography.Text>
        ),
    },
    {
      title: "Khớp OCR",
      dataIndex: "coverage",
      width: 90,
      render: (c: number) => <Tag color={coverageColor(c)}>{pct(c)}</Tag>,
      sorter: (a, b) => a.coverage - b.coverage,
    },
    {
      title: "Trang",
      width: 90,
      render: (_, p) => <PageLinks student={detail.student} book={detail.book} pages={p.trang} />,
    },
  ];
  return (
    <Space orientation="vertical" style={{ width: "100%" }}>
      <Radio.Group value={filter} onChange={(e) => setFilter(e.target.value)}>
        <Radio.Button value="all">Tất cả ({detail.pairs.length})</Radio.Button>
        <Radio.Button value="errors">Lỗi định dạng ({detail.pairs.filter((p) => p.errors.length).length})</Radio.Button>
        <Radio.Button value="low">Khớp OCR &lt; 50% ({detail.pairs.filter((p) => p.coverage < 0.5).length})</Radio.Button>
      </Radio.Group>
      <Typography.Paragraph type="secondary" style={{ margin: 0 }}>
        Chữ <mark style={{ background: "#ffe58f" }}>tô vàng</mark> không có trong đoạn OCR tương ứng — thường là chữ sinh viên đã sửa so
        với OCR. "Khớp OCR" thấp: cặp không tìm được trong bản máy (sửa nhiều, thêm nội dung, hoặc OCR sai thứ tự cột).
      </Typography.Paragraph>
      <Table rowKey="line" size="small" columns={columns} dataSource={rows} pagination={{ pageSize: 50, showSizeChanger: false }} />
    </Space>
  );
};

const MissingTab = ({ detail }: { detail: BookDetail }) => {
  const columns: ColumnsType<MissingRow> = [
    {
      title: "Trang",
      width: 90,
      render: (_, r) => <PageLinks student={detail.student} book={detail.book} pages={[r.trang]} />,
    },
    { title: "Cột", dataIndex: "dong", width: 60 },
    { title: "Hán (OCR)", dataIndex: "han", render: (h: string) => <span lang="zh-Hant">{h}</span> },
    { title: "Dịch máy", dataIndex: "viet" },
  ];
  return (
    <Space orientation="vertical" style={{ width: "100%" }}>
      <Typography.Paragraph type="secondary" style={{ margin: 0 }}>
        Cột chữ có trong bản máy nhưng không cặp nào của sinh viên phủ tới: ứng viên cho lỗi MISSING, hoặc phần sinh viên chưa làm, hoặc trang
        sơ đồ/bảng được phép bỏ.
      </Typography.Paragraph>
      <Table rowKey="index" size="small" columns={columns} dataSource={detail.missing} pagination={{ pageSize: 50, showSizeChanger: false }} />
    </Space>
  );
};

const GradeTab = ({ detail, threshold }: { detail: BookDetail; threshold: number }) => {
  const key = storageKey(detail.student, detail.book);
  const [verdicts, setVerdicts] = useState<Record<number, Verdict>>(() => loadVerdicts(key));
  useEffect(() => setVerdicts(loadVerdicts(key)), [key]);

  const valid = detail.pairs.filter((p) => p.errors.length === 0);
  const sample = useMemo(() => {
    const lines = new Set(sampleLines(valid.map((p) => p.line), key));
    return valid.filter((p) => lines.has(p.line));
  }, [valid, key]);

  const setVerdict = (line: number, v: Verdict) => {
    const next = { ...verdicts, [line]: v };
    setVerdicts(next);
    saveVerdicts(key, next);
  };

  const inSample = Object.fromEntries(Object.entries(verdicts).filter(([l]) => sample.some((p) => p.line === Number(l))));
  const sum = summarize(inSample);

  const download = () => {
    const csv = toCsv(sample.map((p) => ({ line: p.line, han: p.han, viet: p.viet, verdict: verdicts[p.line] })));
    const url = URL.createObjectURL(new Blob([csv], { type: "text/csv;charset=utf-8" }));
    const a = document.createElement("a");
    a.href = url;
    a.download = `cham_${detail.student}_${detail.book}.csv`;
    a.click();
    URL.revokeObjectURL(url);
  };

  const columns: ColumnsType<AlignedPair> = [
    { title: "Dòng", dataIndex: "line", width: 60 },
    { title: "Hán", dataIndex: "han", render: (h: string) => <span lang="zh-Hant">{h}</span> },
    { title: "Việt", dataIndex: "viet" },
    { title: "Dịch máy (tham khảo)", dataIndex: "may_viet", render: (v: string) => <Typography.Text type="secondary">{v}</Typography.Text> },
    {
      title: "Nhãn",
      width: 200,
      render: (_, p) => (
        <Select<Verdict>
          aria-label={`Nhãn dòng ${p.line}`}
          placeholder="Chưa chấm"
          value={verdicts[p.line]}
          onChange={(v) => setVerdict(p.line, v)}
          style={{ width: 190 }}
          options={(Object.keys(VERDICT_LABEL) as Verdict[]).map((v) => ({ value: v, label: VERDICT_LABEL[v] }))}
        />
      ),
    },
  ];

  const failed = sum.rate != null && sum.rate > threshold;
  return (
    <Space orientation="vertical" style={{ width: "100%" }}>
      <Space wrap size="large">
        <Statistic title="Cặp trong mẫu" value={sample.length} suffix={`/ ${valid.length}`} />
        <Statistic title="Đã chấm" value={sum.checked} />
        <Statistic title="Cặp lỗi" value={sum.errors} />
        <Statistic
          title={`Tỷ lệ lỗi (ngưỡng ${pct(threshold)})`}
          value={pct(sum.rate)}
          styles={{ content: { color: sum.rate == null ? undefined : failed ? "#cf1322" : "#389e0d" } }}
        />
        <Button onClick={download} disabled={!sample.length}>
          Tải kết quả chấm (CSV)
        </Button>
      </Space>
      <Typography.Paragraph type="secondary" style={{ margin: 0 }}>
        Mẫu ngẫu nhiên 5% số cặp hợp lệ (tối thiểu 20), cố định theo sinh viên và cuốn. Nhãn chỉ lưu trong trình duyệt này — trang không cần
        đăng nhập nên không ghi lên máy chủ; tải CSV để lưu lại. OMISSION {sum.byType.OMISSION} · ADDITION {sum.byType.ADDITION} · MISSING{" "}
        {sum.byType.MISSING}.
      </Typography.Paragraph>
      <Table rowKey="line" size="small" columns={columns} dataSource={sample} pagination={false} />
    </Space>
  );
};

const PagesTab = ({ detail }: { detail: BookDetail }) => {
  const [index, setIndex] = useState(0);
  const page = detail.pages[index];
  if (!page) return <Typography.Text type="secondary">Chưa có ảnh trang trên máy chủ.</Typography.Text>;
  return (
    <Space orientation="vertical" align="center" style={{ width: "100%" }}>
      <Pagination
        simple
        current={index + 1}
        total={detail.pages.length}
        pageSize={1}
        onChange={(n) => setIndex(n - 1)}
        showSizeChanger={false}
      />
      <Typography.Text type="secondary">Trang {page}</Typography.Text>
      <Image src={pageImageUrl(detail.student, detail.book, page)} alt={`Trang ${page}`} style={{ maxWidth: "100%", maxHeight: "80vh" }} />
    </Space>
  );
};

const BookView = ({ student, book, threshold, onBack }: { student: string; book: string; threshold: number; onBack: () => void }) => {
  const { data, error, isLoading } = useQuery({ queryKey: ["doi-chieu", student, book], queryFn: () => getBook(student, book) });
  const { isAdmin } = useAuth();
  if (error) return <Alert type="error" showIcon title="Không tải được cuốn" description={String(error)} />;
  return (
    <Card
      loading={isLoading}
      title={
        <Space>
          <Button onClick={onBack}>← Danh sách</Button>
          <span>
            {data?.ten ?? book} <Typography.Text type="secondary">({student} / {book})</Typography.Text>
          </span>
          {data && <SourceLink link={data.link} />}
        </Space>
      }
    >
      {data && !data.tsv && !data.stats.machine_rows ? (
        <>
          <Typography.Paragraph type="secondary">Cuốn này chưa có bản máy và chưa có bài nộp; dưới đây là ảnh trang.</Typography.Paragraph>
          <PagesTab detail={data} />
        </>
      ) : data ? (
        <>
          <Space wrap size="large" style={{ marginBottom: 12 }}>
            <Statistic title="Cặp" value={data.stats.pairs} />
            <Statistic title="Hợp lệ" value={data.stats.valid} />
            <Statistic title="Lỗi định dạng" value={data.stats.format_errors} />
            <Statistic title="Độ phủ OCR" value={pct(data.stats.ocr_coverage)} />
            <Statistic title="Cột máy chưa phủ" value={data.missing.length} />
          </Space>
          <Tabs
            items={[
              { key: "pairs", label: "Cặp song song", children: <PairsTab detail={data} /> },
              { key: "missing", label: `Bản máy chưa dóng (${data.missing.length})`, children: <MissingTab detail={data} /> },
              { key: "grade", label: "Chấm mẫu lỗi", children: <GradeTab detail={data} threshold={threshold} /> },
              { key: "pages", label: `Ảnh trang (${data.pages.length})`, children: <PagesTab detail={data} /> },
              ...(isAdmin ? [{ key: "soat", label: "Soát", children: <SoatTab detail={data} /> }] : []),
            ]}
          />
        </>
      ) : null}
    </Card>
  );
};

const DoiChieuPage = () => {
  const [params, setParams] = useSearchParams();
  const student = params.get("sv");
  const book = params.get("cuon");
  const { data, error, isLoading } = useQuery({ queryKey: ["doi-chieu"], queryFn: getOverview });
  const threshold = data?.error_threshold ?? 0.3;
  const target = data?.target ?? 2000;

  return (
    <div style={{ maxWidth: 1280, margin: "0 auto", width: "100%" }}>
      <Typography.Title level={2}>Đối chiếu dóng hàng Hán – Việt</Typography.Title>
      <Typography.Paragraph type="secondary">
        Kết quả dóng hàng sinh viên nộp, đặt cạnh bản máy của lab (OCR + dịch máy, ghép theo chữ Hán). Chỉ tiêu và ngưỡng lỗi theo Guideline
        CV. <Link to="/nghien-cuu/quan-ly">← Thông tin nghiên cứu</Link>
      </Typography.Paragraph>
      {student && book ? (
        <BookView student={student} book={book} threshold={threshold} onBack={() => setParams({})} />
      ) : error ? (
        <Alert type="error" showIcon title="Không tải được dữ liệu" description={String(error)} />
      ) : (
        <Card loading={isLoading}>
          {data && data.students.length === 0 ? (
            <Alert type="info" showIcon title="Chưa có bài nộp nào" description="Máy chủ chưa có cuốn nào trong thư mục dữ liệu đối chiếu." />
          ) : (
            <Table
              rowKey="id"
              size="small"
              pagination={false}
              columns={studentColumns(target)}
              dataSource={data?.students ?? []}
              expandable={{
                expandedRowRender: (s) => (
                  <Table
                    rowKey="id"
                    size="small"
                    pagination={false}
                    columns={bookColumns((b) => setParams({ sv: s.id, cuon: b }))}
                    dataSource={s.books}
                  />
                ),
              }}
            />
          )}
        </Card>
      )}
    </div>
  );
};

export default DoiChieuPage;
