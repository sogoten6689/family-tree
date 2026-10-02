import { useState } from "react";
import { Button, Card, Empty, Select, Space, Steps, Tag, Typography } from "antd";
import { LeftOutlined, RightOutlined } from "@ant-design/icons";
import { useTranslation } from "react-i18next";

import { VoteDiffLine, type UncertainSpan } from "./VoteDiffLine";

export type EngineOcrInfo = {
  text: string;
  score: number | null;
  similarity_to_others: number;
};

export type VoteMeta = {
  vote_method: string | null;
  engines: Record<string, EngineOcrInfo>;
  uncertain_spans: UncertainSpan[];
  uncertain_rate: number;
  structural_diffs: unknown[];
};

type PipelineStepsPanelProps = {
  pipelineVersion?: string;
  transliterationText?: string | null;
  translationText?: string | null;
  voteMeta?: VoteMeta[] | null;
};

const { Paragraph, Text } = Typography;

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
}: PipelineStepsPanelProps) {
  const { t } = useTranslation();
  const [stepIndex, setStepIndex] = useState(0);
  const [pageIndex, setPageIndex] = useState(0);

  const pageCount = voteMeta?.length ?? 0;
  const hasData = pipelineVersion === "v2" || pageCount > 0 || !!transliterationText || !!translationText;
  if (!hasData) return null;

  const safePage = Math.min(pageIndex, Math.max(pageCount - 1, 0));
  const pageVoteMeta = voteMeta?.[safePage];
  const noVoteData = (
    <Empty
      description={t("docReader.stepNoVoteData", {
        defaultValue: "Không có dữ liệu OCR nhiều engine / vote cho bộ này (pipeline v1).",
      })}
      image={Empty.PRESENTED_IMAGE_SIMPLE}
    />
  );
  const engineEntries = pageVoteMeta?.engines ? Object.entries(pageVoteMeta.engines) : [];

  const steps = [
    {
      title: t("docReader.stepOcr"),
      content:
        engineEntries.length > 0 ? (
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
      content: pageVoteMeta ? (
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
              {pageVoteMeta.uncertain_spans.map((span) => (
                <VoteDiffLine key={span.line} span={span} />
              ))}
            </div>
          ) : (
            <Text type="secondary">{t("docReader.voteNoSpans")}</Text>
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
              onChange={setPageIndex}
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
