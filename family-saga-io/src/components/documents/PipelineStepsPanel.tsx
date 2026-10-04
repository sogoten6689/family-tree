import { useState } from "react";
import { Button, Card, Collapse, Empty, Select, Space, Steps, Tag, Typography } from "antd";
import { LeftOutlined, RightOutlined } from "@ant-design/icons";
import { useTranslation } from "react-i18next";

import { VoteCharView } from "./VoteCharView";
import { engineLabel, isVoteMetaV2, type VoteMetaV2 } from "./voteMetaV2";
import { VoteDiffLine, type UncertainSpan } from "./VoteDiffLine";

export type EngineOcrInfo = {
  text: string;
  score: number | null;
  similarity_to_others: number;
};

/** Meta vote theo dòng (schema 1, cũ). Schema 2 (theo từng chữ): VoteMetaV2. */
export type VoteMetaV1 = {
  vote_method: string | null;
  engines: Record<string, EngineOcrInfo>;
  uncertain_spans: UncertainSpan[];
  uncertain_rate: number;
  structural_diffs: unknown[];
};

export type VoteMeta = VoteMetaV1 | VoteMetaV2;

type PipelineStepsPanelProps = {
  pipelineVersion?: string;
  transliterationText?: string | null;
  translationText?: string | null;
  voteMeta?: VoteMeta[] | null;
  /** Bước mở sẵn (0 = OCR từng engine, 1 = Vote, …). */
  initialStep?: number;
  /** Chữ Hán của trang (1 trang) — để liệt kê cả các dòng đã thống nhất (vote theo dòng). */
  hannomText?: string | null;
};

const { Paragraph, Text } = Typography;

/** Số dòng tranh chấp vẽ mỗi lần — có trang OCR vỡ thành hàng nghìn mẩu
 * (scan#20 trang 76: 4.949 dòng) làm trình duyệt treo nếu vẽ hết. */
const SPAN_PAGE_SIZE = 50;

/**
 * Xem chi tiết từng bước (OCR theo engine -> vote -> phiên âm -> dịch nghĩa).
 * Hiện khi CÓ dữ liệu cho ít nhất 1 bước — kể cả scan mở lại (vote_meta đã
 * lưu) và pipeline v1 (chỉ có phiên âm/dịch; bước OCR/vote ghi rõ không có).
 * vote_meta là danh sách theo trang → chọn trang để xem. Bấm thẳng vào step
 * bất kỳ hoặc dùng nút quay lại/đi tiếp.
 */
export function PipelineStepsPanel({
  pipelineVersion,
  transliterationText,
  translationText,
  voteMeta,
  initialStep = 0,
  hannomText,
}: PipelineStepsPanelProps) {
  const { t } = useTranslation();
  const [stepIndex, setStepIndex] = useState(initialStep);
  const [pageIndex, setPageIndex] = useState(0);
  const [spanLimit, setSpanLimit] = useState(SPAN_PAGE_SIZE);

  const pageCount = voteMeta?.length ?? 0;
  const hasData = pipelineVersion === "v2" || pageCount > 0 || !!transliterationText || !!translationText;
  if (!hasData) return null;

  const safePage = Math.min(pageIndex, Math.max(pageCount - 1, 0));
  const rawPageMeta = voteMeta?.[safePage];
  const pageMetaV2 = isVoteMetaV2(rawPageMeta) ? rawPageMeta : null;
  const pageVoteMeta = rawPageMeta && !pageMetaV2 ? (rawPageMeta as VoteMetaV1) : undefined;
  const noVoteData = (
    <Empty
      description={t("docReader.stepNoVoteData", {
        defaultValue: "Không có dữ liệu OCR nhiều engine / vote cho bộ này (pipeline v1).",
      })}
      image={Empty.PRESENTED_IMAGE_SIMPLE}
    />
  );
  // Vote theo dòng chỉ lưu dòng bất đồng; các dòng còn lại của chữ Hán là dòng
  // các engine đã thống nhất (span.line = chỉ số dòng, từ 0). Chỉ khi xem 1 trang.
  const disputed = new Set((pageVoteMeta?.uncertain_spans ?? []).map((s) => s.line));
  const agreedLines =
    pageVoteMeta && hannomText && pageCount === 1
      ? hannomText
          .split("\n")
          .map((text, line) => ({ text, line }))
          .filter((l) => l.text.trim() && !disputed.has(l.line))
      : [];
  const engineEntries = pageVoteMeta?.engines ? Object.entries(pageVoteMeta.engines) : [];
  const engineEntriesV2 = pageMetaV2 ? Object.entries(pageMetaV2.engines) : [];

  const steps = [
    {
      title: t("docReader.stepOcr"),
      content:
        engineEntriesV2.length > 0 ? (
          <div className="pipeline-steps-engines">
            {engineEntriesV2.map(([name, info]) => (
              <div key={name} className="pipeline-steps-engine">
                <Text strong>{engineLabel(name)}</Text>
                <Tag className="ml-2">{t("docReader.voteV2.chars", { defaultValue: "{{n}} chữ", n: info.han_chars })}</Tag>
                {name === pageMetaV2?.backbone && (
                  <Tag color="blue">{t("docReader.voteV2.backbone", { defaultValue: "nền" })}</Tag>
                )}
                {info.excluded && <Tag title={info.excluded}>{t("docReader.voteV2.excluded", { defaultValue: "không bỏ phiếu" })}</Tag>}
                {info.excluded && (
                  <Text type="secondary" className="block text-xs">
                    {info.excluded}
                  </Text>
                )}
                <Paragraph className="pipeline-steps-engine-text" ellipsis={{ rows: 12, expandable: true }}>
                  {info.text}
                </Paragraph>
              </div>
            ))}
          </div>
        ) : engineEntries.length > 0 ? (
          <div className="pipeline-steps-engines">
            {engineEntries.map(([name, info]) => (
              <div key={name} className="pipeline-steps-engine">
                <Text strong>{name}</Text>
                {info.score != null && (
                  <Tag className="ml-2">{t("docReader.stepOcrScore", { score: info.score.toFixed(2) })}</Tag>
                )}
                <Tag>{t("docReader.stepOcrSimilarity", { value: Math.round(info.similarity_to_others * 100) })}</Tag>
                <Paragraph className="pipeline-steps-engine-text">{info.text}</Paragraph>
              </div>
            ))}
          </div>
        ) : (
          noVoteData
        ),
    },
    {
      title: t("docReader.stepVote"),
      content: pageMetaV2 ? (
        <VoteCharView meta={pageMetaV2} />
      ) : pageVoteMeta ? (
        <div>
          <Paragraph>
            <Text strong>{t("docReader.stepVoteMethod")}: </Text>
            <Text code>{pageVoteMeta.vote_method || "—"}</Text>
          </Paragraph>
          <Paragraph>
            <Text strong>{t("docReader.stepVoteUncertainRate")}: </Text>
            {Math.round((pageVoteMeta.uncertain_rate || 0) * 100)}%{" "}
            {t("docReader.stepVoteUncertainLines", { count: pageVoteMeta.uncertain_spans?.length || 0 })}
          </Paragraph>
          {pageVoteMeta.uncertain_spans?.length ? (
            <div className="vote-spans">
              {pageVoteMeta.uncertain_spans.slice(0, spanLimit).map((span) => (
                <VoteDiffLine key={span.line} span={span} />
              ))}
              {pageVoteMeta.uncertain_spans.length > spanLimit && (
                <Button onClick={() => setSpanLimit((n) => n + SPAN_PAGE_SIZE)}>
                  {t("docReader.voteShowMore", {
                    defaultValue: "Hiện thêm ({{shown}}/{{total}} dòng)",
                    shown: spanLimit,
                    total: pageVoteMeta.uncertain_spans.length,
                  })}
                </Button>
              )}
            </div>
          ) : (
            <Text type="secondary">{t("docReader.voteNoSpans")}</Text>
          )}
          {agreedLines.length > 0 && (
            <Collapse
              className="mt-3"
              size="small"
              items={[
                {
                  key: "agreed",
                  label: t("docReader.voteAgreedLines", {
                    defaultValue: "Các dòng đã thống nhất ({{count}})",
                    count: agreedLines.length,
                  }),
                  children: (
                    <div className="vote-spans">
                      {agreedLines.map((l) => (
                        <div key={l.line} className="vote-agreed-line">
                          <Text strong>{t("docReader.voteLine", { line: l.line + 1 })}</Text>
                          <Tag color="green">✓</Tag>
                          <Text className="pipeline-steps-engine-text !mt-0">{l.text}</Text>
                        </div>
                      ))}
                    </div>
                  ),
                },
              ]}
            />
          )}
        </div>
      ) : (
        noVoteData
      ),
    },
    {
      title: t("docReader.stepTransliteration"),
      content: transliterationText ? (
        <Paragraph className="pipeline-steps-engine-text">{transliterationText}</Paragraph>
      ) : (
        <Empty description={t("docReader.stepOcrEmpty")} image={Empty.PRESENTED_IMAGE_SIMPLE} />
      ),
    },
    {
      title: t("docReader.stepTranslation"),
      content: translationText ? (
        <Paragraph className="pipeline-steps-engine-text">{translationText}</Paragraph>
      ) : (
        <Empty description={t("docReader.stepOcrEmpty")} image={Empty.PRESENTED_IMAGE_SIMPLE} />
      ),
    },
  ];

  return (
    <Card
      className="pipeline-steps-panel"
      title={t("docReader.pipelineStepsTitle")}
      extra={
        pageCount > 1 ? (
          <Space>
            <Text type="secondary">{t("docReader.stepPage", { defaultValue: "Trang" })}</Text>
            <Select
              size="small"
              value={safePage}
              onChange={(value) => {
                setPageIndex(value);
                setSpanLimit(SPAN_PAGE_SIZE);
              }}
              options={Array.from({ length: pageCount }, (_, i) => ({ value: i, label: `${i + 1}/${pageCount}` }))}
              aria-label={t("docReader.stepPage", { defaultValue: "Trang" })}
              style={{ minWidth: 96 }}
            />
          </Space>
        ) : null
      }
    >
      <Steps
        current={stepIndex}
        onChange={setStepIndex}
        items={steps.map((step) => ({ title: step.title }))}
      />
      <div className="pipeline-steps-content">{steps[stepIndex].content}</div>
      <div className="pipeline-steps-nav">
        <Button icon={<LeftOutlined />} disabled={stepIndex === 0} onClick={() => setStepIndex((i) => i - 1)}>
          {t("docReader.stepPrev")}
        </Button>
        <Button
          type="primary"
          disabled={stepIndex === steps.length - 1}
          onClick={() => setStepIndex((i) => i + 1)}
        >
          {t("docReader.stepNext")} <RightOutlined />
        </Button>
      </div>
    </Card>
  );
}
