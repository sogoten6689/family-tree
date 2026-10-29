import { CheckCircleOutlined, CloseCircleOutlined, RedoOutlined, WarningOutlined } from "@ant-design/icons";
import { Alert, Button, Card, Checkbox, Input, Progress, Radio, Segmented, Space, Tabs, Tag, Typography } from "antd";
import { useEffect, useState } from "react";

import {
  AXES,
  ERROR_STATEMENTS,
  FLASHCARDS,
  GLOSSARY,
  GLOSSARY_GROUPS,
  MOCK_QUESTIONS,
  QUIZ,
  type AxisId,
  type FlashCard,
  type MockQuestion,
} from "./defenseReviewData";

/** Tiến độ chỉ lưu trong trình duyệt của người xem. */
export const STORAGE_KEY = "family-tree:on-tap-bao-ve:v1";

interface Progress {
  /** id thẻ → đã thuộc hay cần ôn lại */
  cards: Record<string, "known" | "review">;
  quiz: Record<string, number>;
  errors: Record<string, boolean>;
  mockDrafts: Record<string, string>;
  mockChecks: Record<string, number[]>;
  /** id khái niệm → đã hiểu */
  terms: Record<string, boolean>;
}

const EMPTY: Progress = { cards: {}, quiz: {}, errors: {}, mockDrafts: {}, mockChecks: {}, terms: {} };

function loadProgress(): Progress {
  try {
    const raw = window.localStorage.getItem(STORAGE_KEY);
    if (!raw) return EMPTY;
    return { ...EMPTY, ...(JSON.parse(raw) as Partial<Progress>) };
  } catch {
    return EMPTY;
  }
}

function saveProgress(p: Progress) {
  try {
    window.localStorage.setItem(STORAGE_KEY, JSON.stringify(p));
  } catch {
    // Chế độ riêng tư / chặn lưu trữ: trang vẫn chạy, chỉ không nhớ tiến độ.
  }
}

type AxisFilter = AxisId | "all";

const AxisPicker = ({ value, onChange }: { value: AxisFilter; onChange: (v: AxisFilter) => void }) => (
  <Segmented<AxisFilter>
    value={value}
    onChange={onChange}
    options={[{ label: "Tất cả", value: "all" }, ...AXES.map((a) => ({ label: a.label, value: a.id }))]}
    style={{ maxWidth: "100%", overflowX: "auto" }}
  />
);

const axisLabel = (id: AxisId) => AXES.find((a) => a.id === id)?.label ?? id;

const GapNote = ({ text }: { text: string }) => (
  <Alert type="warning" showIcon icon={<WarningOutlined />} title="Chưa đo / điểm yếu cần chuẩn bị" description={text} />
);

// ── Thẻ lật ──
const FlashCardView = ({
  card,
  status,
  onMark,
}: {
  card: FlashCard;
  status?: "known" | "review";
  onMark: (s: "known" | "review") => void;
}) => {
  const [open, setOpen] = useState(false);
  return (
    <Card
      size="small"
      title={<Typography.Text strong style={{ whiteSpace: "normal" }}>{card.question}</Typography.Text>}
      extra={status && <Tag color={status === "known" ? "green" : "orange"}>{status === "known" ? "Đã thuộc" : "Ôn lại"}</Tag>}
    >
      <Space orientation="vertical" style={{ width: "100%" }}>
        <Tag>{axisLabel(card.axis)}</Tag>
        {open ? (
          <>
            <ul style={{ margin: 0, paddingLeft: 20, listStyle: "disc" }}>
              {card.answer.map((line) => (
                <li key={line}>{line}</li>
              ))}
            </ul>
            {card.gap && <GapNote text={card.gap} />}
            <Space wrap>
              <Button onClick={() => onMark("known")} icon={<CheckCircleOutlined />}>
                Đã thuộc
              </Button>
              <Button onClick={() => onMark("review")} icon={<RedoOutlined />}>
                Cần ôn lại
              </Button>
              <Button type="link" onClick={() => setOpen(false)}>
                Úp thẻ
              </Button>
            </Space>
          </>
        ) : (
          <Button type="primary" onClick={() => setOpen(true)}>
            Lật thẻ
          </Button>
        )}
      </Space>
    </Card>
  );
};

const FlashCardsTab = ({ progress, update }: TabProps) => {
  const [axis, setAxis] = useState<AxisFilter>("all");
  const [onlyReview, setOnlyReview] = useState(false);
  const cards = FLASHCARDS.filter(
    (c) => (axis === "all" || c.axis === axis) && (!onlyReview || progress.cards[c.id] !== "known"),
  );
  const known = FLASHCARDS.filter((c) => progress.cards[c.id] === "known").length;
  return (
    <Space orientation="vertical" size="middle" style={{ width: "100%" }}>
      <Progress percent={Math.round((known / FLASHCARDS.length) * 100)} format={() => `${known}/${FLASHCARDS.length} thẻ đã thuộc`} />
      <AxisPicker value={axis} onChange={setAxis} />
      <Checkbox checked={onlyReview} onChange={(e) => setOnlyReview(e.target.checked)}>
        Chỉ hiện thẻ chưa thuộc
      </Checkbox>
      {cards.map((c) => (
        <FlashCardView
          key={c.id}
          card={c}
          status={progress.cards[c.id]}
          onMark={(s) => update((p) => ({ ...p, cards: { ...p.cards, [c.id]: s } }))}
        />
      ))}
      {cards.length === 0 && <Typography.Text type="secondary">Không còn thẻ nào ở bộ lọc này.</Typography.Text>}
    </Space>
  );
};

// ── Phản biện giả lập ──
const MockView = ({ q, progress, update }: { q: MockQuestion } & TabProps) => {
  const [revealed, setRevealed] = useState(false);
  const draft = progress.mockDrafts[q.id] ?? "";
  const checks = progress.mockChecks[q.id] ?? [];
  return (
    <Card size="small" title={<Typography.Text strong style={{ whiteSpace: "normal" }}>{q.question}</Typography.Text>}>
      <Space orientation="vertical" style={{ width: "100%" }}>
        <Tag>{axisLabel(q.axis)}</Tag>
        <Input.TextArea
          aria-label={`Câu trả lời của anh cho: ${q.question}`}
          placeholder="Trả lời như đang đứng trước hội đồng…"
          autoSize={{ minRows: 3 }}
          value={draft}
          onChange={(e) => update((p) => ({ ...p, mockDrafts: { ...p.mockDrafts, [q.id]: e.target.value } }))}
        />
        {!revealed ? (
          <Button type="primary" onClick={() => setRevealed(true)}>
            So với đáp án gợi ý
          </Button>
        ) : (
          <>
            <Typography.Text strong>Câu trả lời cần có (tự chấm):</Typography.Text>
            <Checkbox.Group
              value={checks}
              onChange={(v) => update((p) => ({ ...p, mockChecks: { ...p.mockChecks, [q.id]: v as number[] } }))}
              style={{ display: "flex", flexDirection: "column", gap: 4 }}
            >
              {q.mustHave.map((m, i) => (
                <Checkbox key={m} value={i}>
                  {m}
                </Checkbox>
              ))}
            </Checkbox.Group>
            <Typography.Text type="secondary">
              Đạt {checks.length}/{q.mustHave.length} ý
            </Typography.Text>
            <Alert type="error" showIcon title="Bẫy" description={q.trap} />
            <Alert type="info" title="Đáp án gợi ý" description={q.model} />
          </>
        )}
      </Space>
    </Card>
  );
};

const MockTab = ({ progress, update }: TabProps) => {
  const [axis, setAxis] = useState<AxisFilter>("all");
  const list = MOCK_QUESTIONS.filter((q) => axis === "all" || q.axis === axis);
  return (
    <Space orientation="vertical" size="middle" style={{ width: "100%" }}>
      <AxisPicker value={axis} onChange={setAxis} />
      {list.map((q) => (
        <MockView key={q.id} q={q} progress={progress} update={update} />
      ))}
      {list.length === 0 && <Typography.Text type="secondary">Chưa có câu phản biện cho trục này.</Typography.Text>}
    </Space>
  );
};

// ── Trắc nghiệm số liệu ──
const QuizTab = ({ progress, update }: TabProps) => {
  const answered = QUIZ.filter((q) => progress.quiz[q.id] !== undefined);
  const right = answered.filter((q) => progress.quiz[q.id] === q.answer).length;
  return (
    <Space orientation="vertical" size="middle" style={{ width: "100%" }}>
      <Space wrap>
        <Typography.Text strong>
          Điểm: {right}/{QUIZ.length}
        </Typography.Text>
        <Typography.Text type="secondary">(đã trả lời {answered.length})</Typography.Text>
        <Button size="small" icon={<RedoOutlined />} onClick={() => update((p) => ({ ...p, quiz: {} }))}>
          Làm lại
        </Button>
      </Space>
      {QUIZ.map((q, idx) => {
        const chosen = progress.quiz[q.id];
        const done = chosen !== undefined;
        return (
          <Card key={q.id} size="small" title={<span style={{ whiteSpace: "normal" }}>{`${idx + 1}. ${q.question}`}</span>}>
            <Radio.Group
              value={chosen}
              disabled={done}
              onChange={(e) => update((p) => ({ ...p, quiz: { ...p.quiz, [q.id]: e.target.value as number } }))}
              style={{ display: "flex", flexWrap: "wrap", gap: 8 }}
            >
              {q.options.map((o, i) => (
                <Radio.Button key={o} value={i}>
                  {o}
                </Radio.Button>
              ))}
            </Radio.Group>
            {done && (
              <Alert
                style={{ marginTop: 10 }}
                type={chosen === q.answer ? "success" : "error"}
                showIcon
                title={chosen === q.answer ? "Đúng" : `Sai — đáp án: ${q.options[q.answer]}`}
                description={q.explain}
              />
            )}
          </Card>
        );
      })}
    </Space>
  );
};

// ── Tìm lỗi phát biểu ──
const ErrorsTab = ({ progress, update }: TabProps) => {
  const answered = ERROR_STATEMENTS.filter((s) => progress.errors[s.id] !== undefined);
  const right = answered.filter((s) => progress.errors[s.id] === s.correct).length;
  return (
    <Space orientation="vertical" size="middle" style={{ width: "100%" }}>
      <Typography.Paragraph type="secondary" style={{ margin: 0 }}>
        Hội đồng hay diễn đạt lại kết quả theo cách sai. Phát biểu dưới đây đúng hay sai?
      </Typography.Paragraph>
      <Space wrap>
        <Typography.Text strong>
          Điểm: {right}/{ERROR_STATEMENTS.length}
        </Typography.Text>
        <Button size="small" icon={<RedoOutlined />} onClick={() => update((p) => ({ ...p, errors: {} }))}>
          Làm lại
        </Button>
      </Space>
      {ERROR_STATEMENTS.map((s) => {
        const chosen = progress.errors[s.id];
        const done = chosen !== undefined;
        const pick = (v: boolean) => update((p) => ({ ...p, errors: { ...p.errors, [s.id]: v } }));
        return (
          <Card key={s.id} size="small">
            <Typography.Paragraph style={{ fontStyle: "italic" }}>“{s.statement}”</Typography.Paragraph>
            <Space wrap>
              <Button disabled={done} type={chosen === true ? "primary" : "default"} icon={<CheckCircleOutlined />} onClick={() => pick(true)}>
                Đúng
              </Button>
              <Button disabled={done} type={chosen === false ? "primary" : "default"} icon={<CloseCircleOutlined />} onClick={() => pick(false)}>
                Sai
              </Button>
            </Space>
            {done && (
              <Alert
                style={{ marginTop: 10 }}
                type={chosen === s.correct ? "success" : "error"}
                showIcon
                title={`${chosen === s.correct ? "Chính xác" : "Chưa đúng"} — phát biểu này ${s.correct ? "ĐÚNG" : "SAI"}`}
                description={s.explain}
              />
            )}
          </Card>
        );
      })}
    </Space>
  );
};

// ── Khái niệm ──
const plain = (x: string) => x.normalize("NFD").replace(/[\u0300-\u036f]/g, "").replace(/đ/gi, "d").toLowerCase();

const GlossaryTab = ({ progress, update }: TabProps) => {
  const [group, setGroup] = useState<string>("all");
  const [q, setQ] = useState("");
  const query = plain(q.trim());
  const list = GLOSSARY.filter(
    (g) =>
      (group === "all" || g.group === group) &&
      (!query || plain(`${g.term} ${g.meaning} ${g.inThesis ?? ""}`).includes(query)),
  );
  const understood = GLOSSARY.filter((g) => progress.terms[g.id]).length;
  return (
    <Space orientation="vertical" size="middle" style={{ width: "100%" }}>
      <Progress
        percent={Math.round((understood / GLOSSARY.length) * 100)}
        format={() => `${understood}/${GLOSSARY.length} khái niệm đã hiểu`}
      />
      <Input.Search allowClear placeholder="Tìm khái niệm, ví dụ: F1, XLM-R, kappa…" value={q} onChange={(e) => setQ(e.target.value)} />
      <Segmented<string>
        value={group}
        onChange={setGroup}
        options={[{ label: "Tất cả", value: "all" }, ...GLOSSARY_GROUPS.map((g) => ({ label: g, value: g }))]}
        style={{ maxWidth: "100%", overflowX: "auto" }}
      />
      {list.map((g) => (
        <Card
          key={g.id}
          size="small"
          title={<Typography.Text strong style={{ whiteSpace: "normal" }}>{g.term}</Typography.Text>}
          extra={
            <Checkbox
              checked={!!progress.terms[g.id]}
              onChange={(e) => update((p) => ({ ...p, terms: { ...p.terms, [g.id]: e.target.checked } }))}
            >
              Đã hiểu
            </Checkbox>
          }
        >
          <Space orientation="vertical" style={{ width: "100%" }}>
            <Tag>{g.group}</Tag>
            <Typography.Paragraph style={{ margin: 0 }}>{g.meaning}</Typography.Paragraph>
            {g.inThesis && (
              <Typography.Paragraph style={{ margin: 0 }}>
                <Typography.Text strong>Trong đề tài: </Typography.Text>
                {g.inThesis}
              </Typography.Paragraph>
            )}
            {g.remember && <Alert type="info" showIcon title="Cần nhớ" description={g.remember} />}
          </Space>
        </Card>
      ))}
      {list.length === 0 && <Typography.Text type="secondary">Không tìm thấy khái niệm phù hợp.</Typography.Text>}
    </Space>
  );
};

interface TabProps {
  progress: Progress;
  update: (fn: (p: Progress) => Progress) => void;
}

const DefenseReviewPage = () => {
  const [progress, setProgress] = useState<Progress>(loadProgress);
  useEffect(() => saveProgress(progress), [progress]);
  const update = (fn: (p: Progress) => Progress) => setProgress(fn);

  const items = [
    { key: "terms", label: "Khái niệm", children: <GlossaryTab progress={progress} update={update} /> },
    { key: "cards", label: "Thẻ hỏi–đáp", children: <FlashCardsTab progress={progress} update={update} /> },
    { key: "mock", label: "Phản biện giả lập", children: <MockTab progress={progress} update={update} /> },
    { key: "quiz", label: "Trắc nghiệm số liệu", children: <QuizTab progress={progress} update={update} /> },
    { key: "errors", label: "Tìm lỗi phát biểu", children: <ErrorsTab progress={progress} update={update} /> },
  ];

  return (
    <div style={{ maxWidth: 900, margin: "0 auto", width: "100%" }}>
      <Typography.Title level={2}>Ôn tập bảo vệ luận văn</Typography.Title>
      <Typography.Paragraph type="secondary">
        Câu hỏi phản biện theo 5 trục, số liệu lấy từ kết quả đã đo của đề tài (đến 28/10/2026). Tiến độ chỉ lưu trong trình duyệt này.
      </Typography.Paragraph>
      <Alert
        style={{ marginBottom: 16 }}
        type="info"
        showIcon
        title="Chiến lược khi bị phản biện"
        description="Có backup slide cho mỗi số liệu. Gặp câu chạm vào giới hạn: thừa nhận thẳng phạm vi, nêu nguyên nhân khách quan (dữ liệu, nhãn, tài nguyên) và hướng phát triển. Số đo trên nhãn máy luôn nói rõ là nhãn máy."
      />
      <Tabs items={items} />
      <Button
        size="small"
        danger
        style={{ marginTop: 24 }}
        onClick={() => setProgress(EMPTY)}
      >
        Xoá toàn bộ tiến độ trên trình duyệt này
      </Button>
    </div>
  );
};

export default DefenseReviewPage;
