import { Collapse, Empty, Tag, Typography } from "antd";
import { useTranslation } from "react-i18next";

export type EngineOcrInfo = {
  text: string;
  score: number | null;
  similarity_to_others: number;
};

export type VoteMeta = {
  vote_method: string | null;
  engines: Record<string, EngineOcrInfo>;
  uncertain_spans: unknown[];
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
 * Xem chi tiết từng bước của pipeline v2 (OCR theo engine -> vote -> phiên
 * âm -> dịch nghĩa) — trước đây backend đã tính (vote_meta) nhưng chưa có
 * chỗ nào hiển thị. Chỉ hiện khi pipeline_version="v2" (v1 không có dữ liệu
 * nhiều engine để so sánh).
 */
export function PipelineStepsPanel({
  pipelineVersion,
  transliterationText,
  translationText,
  voteMeta,
}: PipelineStepsPanelProps) {
  const { t } = useTranslation();
  if (pipelineVersion !== "v2") return null;

  const pageVoteMeta = voteMeta?.[0];
  const engineEntries = pageVoteMeta?.engines ? Object.entries(pageVoteMeta.engines) : [];

  return (
    <Collapse
      className="pipeline-steps-panel"
      items={[
        {
          key: "steps",
          label: t("docReader.pipelineStepsTitle"),
          children: (
            <Collapse
              items={[
                {
                  key: "ocr",
                  label: t("docReader.stepOcr"),
                  children:
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
                      <Empty description={t("docReader.stepOcrEmpty")} image={Empty.PRESENTED_IMAGE_SIMPLE} />
                    ),
                },
                {
                  key: "vote",
                  label: t("docReader.stepVote"),
                  children: pageVoteMeta ? (
                    <div>
                      <Paragraph>
                        <Text strong>{t("docReader.stepVoteMethod")}: </Text>
                        <Text code>{pageVoteMeta.vote_method || "—"}</Text>
                      </Paragraph>
                      <Paragraph>
                        <Text strong>{t("docReader.stepVoteUncertainRate")}: </Text>
                        {Math.round((pageVoteMeta.uncertain_rate || 0) * 100)}%
                        {" "}
                        {t("docReader.stepVoteUncertainLines", { count: pageVoteMeta.uncertain_spans?.length || 0 })}
                      </Paragraph>
                    </div>
                  ) : (
                    <Empty description={t("docReader.stepOcrEmpty")} image={Empty.PRESENTED_IMAGE_SIMPLE} />
                  ),
                },
                {
                  key: "transliteration",
                  label: t("docReader.stepTransliteration"),
                  children: transliterationText ? (
                    <Paragraph className="pipeline-steps-engine-text">{transliterationText}</Paragraph>
                  ) : (
                    <Empty description={t("docReader.stepOcrEmpty")} image={Empty.PRESENTED_IMAGE_SIMPLE} />
                  ),
                },
                {
                  key: "translation",
                  label: t("docReader.stepTranslation"),
                  children: translationText ? (
                    <Paragraph className="pipeline-steps-engine-text">{translationText}</Paragraph>
                  ) : (
                    <Empty description={t("docReader.stepOcrEmpty")} image={Empty.PRESENTED_IMAGE_SIMPLE} />
                  ),
                },
              ]}
            />
          ),
        },
      ]}
    />
  );
}
