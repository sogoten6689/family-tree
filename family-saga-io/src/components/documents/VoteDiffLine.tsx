import { Tag, Typography } from "antd";
import { useTranslation } from "react-i18next";

/** Đoạn của dòng engine bất đồng, so với dòng thắng (tính sẵn ở backend —
 * app/hannom/vote_diff.py — theo code point; frontend không tính chỉ số). */
export type CharDiffSegment =
  | { op: "equal" | "replace" | "insert"; text: string }
  | { op: "delete"; missing: number };

export type VotedSegment = { text: string; contested: boolean };

export type DisagreeingEngine = {
  engine: string;
  text: string;
  similarity: number;
  diff?: CharDiffSegment[];
};

export type UncertainPosition = {
  backbone_pos?: number;
  backbone_char?: string;
  gap_before?: number;
  insert_index?: number;
  resolved: string | null;
  method: string;
  votes: Record<string, string[]>;
};

export type UncertainSpan = {
  line: number;
  voted_line: string;
  method: string;
  n_agree: number;
  n_total: number;
  disagreeing: DisagreeingEngine[];
  positional?: { uncertain_positions?: UncertainPosition[] };
  voted_segments?: VotedSegment[];
};

const METHOD_CLASS: Record<string, string> = {
  line_majority_override: "vote-span-override",
  line_no_majority: "vote-span-tie",
  line_confirmed_majority: "vote-span-keep",
  line_unanimous: "vote-span-ok",
};

const { Text } = Typography;

function DiffText({ segments, fallback }: { segments?: CharDiffSegment[]; fallback: string }) {
  if (!segments) return <>{fallback}</>;
  return (
    <>
      {segments.map((seg, i) =>
        seg.op === "delete" ? (
          <span key={i} className="vote-ch-gap">
            {"·".repeat(seg.missing)}
          </span>
        ) : (
          <span key={i} className={`vote-ch-${seg.op === "equal" ? "eq" : seg.op === "replace" ? "rep" : "ins"}`}>
            {seg.text}
          </span>
        ),
      )}
    </>
  );
}

function VotedText({ span }: { span: UncertainSpan }) {
  if (!span.voted_segments) return <>{span.voted_line}</>;
  return (
    <>
      {span.voted_segments.map((seg, i) =>
        seg.contested ? (
          <span key={i} className="vote-ch-contested">
            {seg.text}
          </span>
        ) : (
          <span key={i}>{seg.text}</span>
        ),
      )}
    </>
  );
}

/**
 * 1 dòng tranh chấp của bước Vote: dòng thắng (gạch chân chữ bị tranh chấp),
 * phiếu thắng n_agree/n_total, và từng engine bất đồng tô màu theo diff
 * (đỏ = bị thay, vàng = chữ thừa, chấm mờ = chữ thiếu) — cùng cách hiển thị
 * với scripts/build_dashboard.py của repo nghiên cứu.
 */
export function VoteDiffLine({ span }: { span: UncertainSpan }) {
  const { t } = useTranslation();
  const positions = span.positional?.uncertain_positions ?? [];
  const voteLabel = (value: string) =>
    value === "__keep__"
      ? t("docReader.voteKeepBackbone")
      : value === "__delete__" || value === ""
        ? t("docReader.voteNoChar")
        : `"${value}"`;

  return (
    <div className={`vote-span ${METHOD_CLASS[span.method] ?? ""}`}>
      <div className="vote-span-head">
        <Text strong>{t("docReader.voteLine", { line: span.line + 1 })}</Text>
        <Tag>{t(`docReader.voteMethod.${span.method}`, { defaultValue: span.method })}</Tag>
        <Text type="secondary">{t("docReader.voteWinLabel", { agree: span.n_agree, total: span.n_total })}</Text>
      </div>
      <div className="vote-han">
        <VotedText span={span} />
      </div>
      {span.disagreeing.length > 0 && (
        <>
          <Text type="secondary" className="vote-legend">
            {t("docReader.voteLegend")}
          </Text>
          <ul className="vote-dis">
            {span.disagreeing.map((d) => (
              <li key={d.engine}>
                <Text strong>{d.engine}</Text>{" "}
                <Text type="secondary">· sim {d.similarity}</Text>
                <div className="vote-han">
                  <DiffText segments={d.diff} fallback={d.text} />
                </div>
              </li>
            ))}
          </ul>
        </>
      )}
      {positions.length > 0 && (
        <div className="vote-positions">
          {positions.map((p, i) => (
            <div key={i} className={`vote-pos ${p.resolved ? "vote-pos-fixed" : "vote-pos-open"}`}>
              <Text strong>
                {p.backbone_pos != null
                  ? t("docReader.votePosition", { pos: p.backbone_pos + 1, char: p.backbone_char ?? "" })
                  : t("docReader.voteGap", { pos: (p.gap_before ?? 0) + 1 })}
              </Text>{" "}
              {p.resolved ? (
                <>
                  → <span className="vote-ch-rep">{p.resolved}</span>
                </>
              ) : (
                <Text type="secondary" italic>
                  {t("docReader.voteNotResolved")}
                </Text>
              )}
              <div className="vote-pos-votes">
                {Object.entries(p.votes)
                  .map(([value, engines]) => `${voteLabel(value)}: ${engines.join(", ")}`)
                  .join(" · ")}
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
