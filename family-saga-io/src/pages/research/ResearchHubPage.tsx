import { WarningOutlined } from "@ant-design/icons";
import { Alert, Card, Input, Select, Space, Table, Tabs, Tag, Typography } from "antd";
import type { ColumnsType } from "antd/es/table";
import { useState } from "react";
import { Link } from "react-router-dom";

import { AXES, FLASHCARDS, MOCK_QUESTIONS } from "./defenseReviewData";
import {
  CENTRAL_QUESTION,
  EVALUATION_RULES,
  HYPOTHESES,
  LABEL_SOURCE_LABEL,
  METHODS,
  RESEARCH_QUESTIONS,
  RESULTS,
  STAGES,
  STATUS_LABEL,
  UPDATED_AT,
  fmt,
  matches,
  type LabelSource,
  type Result,
  type RqId,
  type Status,
} from "./researchHubData";

export interface Filters {
  query: string;
  rq: RqId | "all";
  status: Status | "all";
  label: LabelSource | "all";
}

const STATUS_COLOR: Record<Status, string> = { measured: "green", in_progress: "gold", todo: "default" };
const LABEL_COLOR: Record<LabelSource, string> = { human: "blue", machine: "red", semi_auto: "orange" };

const StatusTag = ({ s }: { s: Status }) => <Tag color={STATUS_COLOR[s]}>{STATUS_LABEL[s]}</Tag>;
const LabelTag = ({ l }: { l: LabelSource }) => (
  <Tag color={LABEL_COLOR[l]} icon={l === "machine" ? <WarningOutlined /> : undefined}>
    {LABEL_SOURCE_LABEL[l]}
  </Tag>
);

const viDate = (iso: string | null) => (iso ? iso.split("-").reverse().join("/") : "—");

const Empty = () => <Typography.Text type="secondary">Không có mục nào khớp bộ lọc.</Typography.Text>;

/** Bộ lọc nào không áp dụng cho tab này thì ghi ra, để người xem không tưởng là đã lọc. */
const IgnoredNote = ({ filters, ignores }: { filters: Filters; ignores: ("rq" | "status" | "label")[] }) => {
  const names = { rq: "câu hỏi nghiên cứu", status: "trạng thái", label: "loại nhãn" };
  const active = ignores.filter((k) => filters[k] !== "all");
  if (active.length === 0) return null;
  return (
    <Typography.Paragraph type="secondary" style={{ margin: 0 }}>
      Tab này không lọc theo {active.map((k) => names[k]).join(", ")}.
    </Typography.Paragraph>
  );
};

export const filterResults = (f: Filters) =>
  RESULTS.filter(
    (r) =>
      (f.rq === "all" || r.rqs.includes(f.rq)) &&
      (f.status === "all" || r.status === f.status) &&
      (f.label === "all" || r.labelSource === f.label) &&
      matches(f.query, r.system, r.dataset, r.source, r.note),
  );

const QuestionsTab = ({ filters }: { filters: Filters }) => {
  const list = RESEARCH_QUESTIONS.filter(
    (q) =>
      (filters.rq === "all" || q.id === filters.rq) &&
      (filters.status === "all" || q.status === filters.status) &&
      matches(filters.query, q.id, q.question, q.experiment, q.statusNote, q.topic),
  );
  return (
    <Space orientation="vertical" style={{ width: "100%" }}>
      <Alert type="info" showIcon title="Câu hỏi trung tâm" description={CENTRAL_QUESTION} />
      <IgnoredNote filters={filters} ignores={["label"]} />
      {list.map((q) => (
        <Card
          key={q.id}
          size="small"
          title={
            <Space wrap>
              <Typography.Text strong>{q.id}</Typography.Text>
              <Tag color={q.kind === "understand" ? "geekblue" : "green"}>{q.topic}</Tag>
            </Space>
          }
          extra={<StatusTag s={q.status} />}
        >
          <Typography.Paragraph strong style={{ marginBottom: 8 }}>
            {q.question}
          </Typography.Paragraph>
          <Typography.Paragraph style={{ marginBottom: 8 }}>
            <Typography.Text type="secondary">Thí nghiệm: </Typography.Text>
            {q.experiment}
          </Typography.Paragraph>
          <Typography.Paragraph style={{ marginBottom: 8 }}>
            <Typography.Text type="secondary">Hiện trạng: </Typography.Text>
            {q.statusNote}
          </Typography.Paragraph>
          <Typography.Text type="secondary">
            Giả thuyết: {HYPOTHESES.filter((h) => h.rq === q.id).map((h) => h.id).join(", ") || "—"} · Kết quả liên quan:{" "}
            {RESULTS.filter((r) => r.rqs.includes(q.id)).length}
          </Typography.Text>
        </Card>
      ))}
      {list.length === 0 && <Empty />}
    </Space>
  );
};

const HypothesesTab = ({ filters }: { filters: Filters }) => {
  const list = HYPOTHESES.filter(
    (h) =>
      (filters.rq === "all" || h.rq === filters.rq) &&
      (filters.status === "all" || h.status === filters.status) &&
      matches(filters.query, h.id, h.statement, h.evidence),
  );
  return (
    <Space orientation="vertical" style={{ width: "100%" }}>
      <IgnoredNote filters={filters} ignores={["label"]} />
      {list.map((h) => (
        <Card key={h.id} size="small" title={`${h.id} · ${h.rq}`} extra={<StatusTag s={h.status} />}>
          <Typography.Paragraph style={{ marginBottom: 8 }}>{h.statement}</Typography.Paragraph>
          <Typography.Text type="secondary">Bằng chứng đến nay: </Typography.Text>
          {h.evidence}
        </Card>
      ))}
      {list.length === 0 && <Empty />}
    </Space>
  );
};

const MethodsTab = ({ filters }: { filters: Filters }) => {
  const list = METHODS.filter(
    (m) =>
      (filters.rq === "all" || m.rqs.includes(filters.rq)) &&
      (filters.label === "all" || m.labelSource === filters.label) &&
      matches(filters.query, m.name, m.why, m.result, m.takeaway, m.stage),
  );
  return (
    <Space orientation="vertical" style={{ width: "100%" }}>
      <Typography.Paragraph type="secondary" style={{ margin: 0 }}>
        19 phương pháp đã thử đến 28/10/2026, đều là áp dụng cái có sẵn; {METHODS.filter((m) => m.negative).length} phương pháp cho
        kết quả âm, không khác biệt hoặc chưa kết luận được. Mọi phương pháp đều đã chạy, nên tab này không lọc theo trạng thái.
      </Typography.Paragraph>
      {STAGES.map((stage) => {
        const rows = list.filter((m) => m.stage === stage);
        if (rows.length === 0) return null;
        return (
          <div key={stage}>
            <Typography.Title level={5}>{stage}</Typography.Title>
            <Space orientation="vertical" style={{ width: "100%" }}>
              {rows.map((m) => (
                <Card
                  key={m.n}
                  size="small"
                  title={<Typography.Text strong style={{ whiteSpace: "normal" }}>{`#${m.n}. ${m.name}`}</Typography.Text>}
                  extra={
                    <Space size={4} wrap>
                      {m.labelSource && <LabelTag l={m.labelSource} />}
                      {m.negative && <Tag>Kết quả âm</Tag>}
                    </Space>
                  }
                >
                  <Typography.Paragraph style={{ marginBottom: 6 }}>
                    <Typography.Text type="secondary">Vì sao chọn: </Typography.Text>
                    {m.why}
                  </Typography.Paragraph>
                  <Typography.Paragraph style={{ marginBottom: 6 }}>
                    <Typography.Text type="secondary">Kết quả: </Typography.Text>
                    {m.result}
                  </Typography.Paragraph>
                  <Typography.Paragraph style={{ marginBottom: 6 }}>
                    <Typography.Text type="secondary">Rút ra: </Typography.Text>
                    {m.takeaway}
                  </Typography.Paragraph>
                  {m.rqs.length > 0 && <Typography.Text type="secondary">Liên quan: {m.rqs.join(", ")}</Typography.Text>}
                </Card>
              ))}
            </Space>
          </div>
        );
      })}
      {list.length === 0 && <Empty />}
    </Space>
  );
};

const resultColumns: ColumnsType<Result> = [
  { title: "Hệ thống", dataIndex: "system", width: 220, render: (v: string, r) => <>{v}<br /><Typography.Text type="secondary">{r.task} · {r.pipeline === "vi" ? "tiếng Việt" : "chữ Hán"}</Typography.Text></> },
  { title: "Tập dữ liệu", dataIndex: "dataset", width: 200, render: (v: string, r) => <>{v}{r.n && <><br /><Typography.Text type="secondary">{r.n}</Typography.Text></>}</> },
  { title: "Loại nhãn", dataIndex: "labelSource", width: 120, render: (l: LabelSource) => <LabelTag l={l} /> },
  { title: "F1", dataIndex: "value", width: 110, align: "right", render: (v: number | null, r) => (v === null ? "—" : <><Typography.Text strong>{fmt(v)}</Typography.Text>{r.ci95 && <><br /><Typography.Text type="secondary">CI95 {r.ci95}</Typography.Text></>}</>) },
  { title: "Trạng thái", dataIndex: "status", width: 100, render: (s: Status) => <StatusTag s={s} /> },
  { title: "Ngày đo", dataIndex: "date", width: 100, render: viDate },
  {
    title: "Nguồn, ghi chú",
    dataIndex: "source",
    width: 320,
    render: (v: string, r) => (
      <>
        <Typography.Text code>{v}</Typography.Text>
        {r.labelSource === "machine" && r.value !== null && (
          <><br /><Typography.Text type="danger">Đo trên nhãn máy, không phải độ chính xác thật.</Typography.Text></>
        )}
        {r.note && <><br />{r.note}</>}
      </>
    ),
  },
];

const ResultsTab = ({ filters }: { filters: Filters }) => {
  const list = filterResults(filters);
  return (
    <Space orientation="vertical" style={{ width: "100%" }}>
      <Alert
        type="warning"
        showIcon
        title="Đọc kết quả theo loại nhãn"
        description="Chỉ so các số cùng tập dữ liệu và cùng loại nhãn. Số trên nhãn máy (Gemini chưa soát) chỉ cho biết mô hình tái tạo nhãn máy tốt đến đâu; số trên nhãn bán tự động cũng không phải thước đo chất lượng. Ngày đo là ngày ghi nhận trong nguồn."
      />
      <Table<Result>
        rowKey="id"
        size="small"
        columns={resultColumns}
        dataSource={list}
        pagination={false}
        scroll={{ x: 1170 }}
        locale={{ emptyText: "Không có kết quả nào khớp bộ lọc." }}
      />
      <Typography.Title level={5}>Quy tắc đánh giá chung</Typography.Title>
      <ul style={{ margin: 0, paddingLeft: 20, listStyle: "disc" }}>
        {EVALUATION_RULES.map((r) => (
          <li key={r}>{r}</li>
        ))}
      </ul>
    </Space>
  );
};

const axisLabel = (id: string) => AXES.find((a) => a.id === id)?.label ?? id;

const QaTab = ({ filters }: { filters: Filters }) => {
  // Thẻ ôn tập không gắn RQ; lọc RQ theo việc nội dung có nhắc tới RQ đó.
  const rqOk = (...texts: string[]) => filters.rq === "all" || texts.some((t) => t.includes(filters.rq));
  const cards = FLASHCARDS.filter((c) => rqOk(c.question, ...c.answer, c.gap ?? "") && matches(filters.query, c.question, ...c.answer, c.gap));
  const mocks = MOCK_QUESTIONS.filter(
    (q) => rqOk(q.question, q.model, q.trap, ...q.mustHave) && matches(filters.query, q.question, q.model, q.trap, ...q.mustHave),
  );
  return (
    <Space orientation="vertical" style={{ width: "100%" }}>
      <Typography.Paragraph type="secondary" style={{ margin: 0 }}>
        Lấy từ <Link to="/nghien-cuu/on-tap">trang ôn tập</Link>. Lọc theo RQ là lọc các thẻ có nhắc tới RQ đó trong nội dung.
      </Typography.Paragraph>
      <IgnoredNote filters={filters} ignores={["status", "label"]} />
      <Typography.Title level={5}>Thẻ hỏi–đáp ({cards.length})</Typography.Title>
      {cards.map((c) => (
        <Card key={c.id} size="small" title={<Typography.Text strong style={{ whiteSpace: "normal" }}>{c.question}</Typography.Text>} extra={<Tag>{axisLabel(c.axis)}</Tag>}>
          <ul style={{ margin: 0, paddingLeft: 20, listStyle: "disc" }}>
            {c.answer.map((line) => (
              <li key={line}>{line}</li>
            ))}
          </ul>
          {c.gap && <Alert style={{ marginTop: 8 }} type="warning" showIcon title="Chưa đo / điểm yếu" description={c.gap} />}
        </Card>
      ))}
      <Typography.Title level={5}>Câu hỏi phản biện ({mocks.length})</Typography.Title>
      {mocks.map((q) => (
        <Card key={q.id} size="small" title={<Typography.Text strong style={{ whiteSpace: "normal" }}>{q.question}</Typography.Text>} extra={<Tag>{axisLabel(q.axis)}</Tag>}>
          <Typography.Paragraph style={{ marginBottom: 6 }}>{q.model}</Typography.Paragraph>
          <Typography.Text type="secondary">Tránh: </Typography.Text>
          {q.trap}
        </Card>
      ))}
      {cards.length + mocks.length === 0 && <Empty />}
    </Space>
  );
};

const ALL = { label: "Tất cả", value: "all" } as const;

/** Trang này là trang cha của mọi trang nghiên cứu; các trang con đều có nút quay về đây. */
const CHILD_PAGES = [
  { href: "/nghien-cuu/de-cuong.html", label: "Đề cương", desc: "Tên đề tài, mục tiêu, khung chương" },
  { href: "/nghien-cuu/ket-qua.html", label: "Kết quả", desc: "Báo cáo số liệu đã đo" },
  { href: "/nghien-cuu/on-tap", label: "Ôn tập bảo vệ", desc: "Thẻ hỏi–đáp, trắc nghiệm, phản biện", spa: true },
  { href: "/nghien-cuu/hoi-nghi.html", label: "Hội nghị", desc: "Bài báo cáo hội nghị" },
  { href: "/nghien-cuu/slide-hoi-nghi.html", label: "Slide hội nghị", desc: "20 slide trình chiếu" },
  { href: "/nghien-cuu/goi-viec.html", label: "Gói việc sinh viên", desc: "Phân công dữ liệu cho sinh viên" },
  { href: "/nghien-cuu/doi-chieu", label: "Đối chiếu dóng hàng", desc: "Bài nộp sinh viên so với bản máy, chấm mẫu lỗi", spa: true },
];

const ResearchHubPage = () => {
  const [filters, setFilters] = useState<Filters>({ query: "", rq: "all", status: "all", label: "all" });
  const set = <K extends keyof Filters>(k: K) => (v: Filters[K]) => setFilters((f) => ({ ...f, [k]: v }));

  const items = [
    { key: "rq", label: "Câu hỏi nghiên cứu", children: <QuestionsTab filters={filters} /> },
    { key: "hyp", label: "Giả thuyết", children: <HypothesesTab filters={filters} /> },
    { key: "methods", label: "Phương pháp", children: <MethodsTab filters={filters} /> },
    { key: "results", label: "Kết quả", children: <ResultsTab filters={filters} /> },
    { key: "qa", label: "Hỏi–đáp", children: <QaTab filters={filters} /> },
  ];

  return (
    <div style={{ maxWidth: 1100, margin: "0 auto", width: "100%" }}>
      <Typography.Title level={2}>Thông tin nghiên cứu</Typography.Title>
      <Typography.Paragraph type="secondary">
        Gom câu hỏi nghiên cứu, giả thuyết, phương pháp, kết quả và câu hỏi ôn tập của luận văn. Nội dung chốt ngày {viDate(UPDATED_AT)}, lấy
        từ kết quả đã đo của đề tài; chưa được thầy duyệt.
      </Typography.Paragraph>
      <nav aria-label="Các trang con của đề tài" style={{ marginBottom: 16 }}>
        <Space wrap size={[8, 8]}>
          {CHILD_PAGES.map((p) => (
            <Card key={p.href} size="small" style={{ width: 200 }}>
              {p.spa ? <Link to={p.href}>{p.label}</Link> : <a href={p.href}>{p.label}</a>}
              <Typography.Paragraph type="secondary" style={{ margin: "4px 0 0", fontSize: 12 }}>
                {p.desc}
              </Typography.Paragraph>
            </Card>
          ))}
        </Space>
      </nav>
      <Space wrap style={{ marginBottom: 16 }}>
        <Input.Search
          allowClear
          placeholder="Tìm (gõ không dấu được)"
          value={filters.query}
          onChange={(e) => set("query")(e.target.value)}
          style={{ width: 260 }}
        />
        <Select<Filters["rq"]>
          aria-label="Lọc theo câu hỏi nghiên cứu"
          value={filters.rq}
          onChange={set("rq")}
          style={{ width: 140 }}
          options={[{ ...ALL, label: "Mọi RQ" }, ...RESEARCH_QUESTIONS.map((q) => ({ label: q.id, value: q.id }))]}
        />
        <Select<Filters["status"]>
          aria-label="Lọc theo trạng thái"
          value={filters.status}
          onChange={set("status")}
          style={{ width: 160 }}
          options={[{ ...ALL, label: "Mọi trạng thái" }, ...(Object.keys(STATUS_LABEL) as Status[]).map((s) => ({ label: STATUS_LABEL[s], value: s }))]}
        />
        <Select<Filters["label"]>
          aria-label="Lọc theo loại nhãn"
          value={filters.label}
          onChange={set("label")}
          style={{ width: 160 }}
          options={[{ ...ALL, label: "Mọi loại nhãn" }, ...(Object.keys(LABEL_SOURCE_LABEL) as LabelSource[]).map((l) => ({ label: LABEL_SOURCE_LABEL[l], value: l }))]}
        />
      </Space>
      <Tabs items={items} />
    </div>
  );
};

export default ResearchHubPage;
