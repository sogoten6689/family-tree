import { Tag, Tooltip, Typography } from "antd";
import { useMemo, useState } from "react";
import { useTranslation } from "react-i18next";

import { engineLabel, type VoteMetaV2, type VoteSlot, type VoteSlotStatus } from "./voteMetaV2";

/** Lớp màu theo trạng thái: xanh = tự sửa, vàng = cần xem (đề xuất / chỉ 2 phiếu), đỏ = hoà. */
const STATUS_CLASS: Partial<Record<VoteSlotStatus, string>> = {
  auto_fixed: "vote-c-fixed",
  suggested: "vote-c-review",
  kept_weak: "vote-c-review",
  tie: "vote-c-tie",
  unaligned: "vote-c-tie",
};

const { Text } = Typography;

/** Tách theo code point (chữ Nôm ngoài BMP là 1 chữ, không phải 2). */
const chars = (s: string) => Array.from(s);

type LineView = {
  chars: { ch: string; slot?: VoteSlot; inserts: VoteSlot[] }[];
};

function buildLines(meta: VoteMetaV2): LineView[] {
  const charSlots = new Map<number, VoteSlot>();
  const insertSlots = new Map<number, VoteSlot[]>();
  for (const s of meta.slots) {
    if (s.kind === "char") charSlots.set(s.index, s);
    else if (s.proposal) insertSlots.set(s.index, [...(insertSlots.get(s.index) ?? []), s]);
  }
  let offset = 0;
  return meta.lines.map((line) => {
    const cs = chars(line).map((ch, i) => ({
      ch,
      slot: charSlots.get(offset + i),
      inserts: insertSlots.get(offset + i) ?? [],
    }));
    offset += cs.length;
    return { chars: cs };
  });
}

/** Phiếu của từng engine tại 1 vị trí: engine → giá trị ("" = không có chữ). */
function votesByEngine(slot: VoteSlot | undefined, voters: string[], final: string): Record<string, string> {
  if (!slot) return Object.fromEntries(voters.map((e) => [e, final]));
  const out: Record<string, string> = {};
  for (const [value, engines] of Object.entries(slot.votes)) for (const e of engines) out[e] = value;
  return out;
}

/**
 * Vote theo từng chữ: tóm tắt trang, cả trang tô màu từng chữ, bấm 1 dòng →
 * bảng đối chiếu (mỗi hàng 1 engine, mỗi cột 1 chữ). Quy ước: ≥3 phiếu tự sửa,
 * 2 phiếu chỉ đề xuất, hoà giữ chữ của engine nền.
 */
export function VoteCharView({ meta }: { meta: VoteMetaV2 }) {
  const { t } = useTranslation();
  const [selected, setSelected] = useState<number | null>(null);
  const lines = useMemo(() => buildLines(meta), [meta]);
  const voters = Object.entries(meta.engines)
    .filter(([, e]) => e.voted)
    .map(([name]) => name);
  const s = meta.stats;
  const pct = Math.round((meta.review_rate || 0) * 100);

  const summary: [string, string | number][] = [
    [t("docReader.voteV2.review", { defaultValue: "Chữ cần soát" }), `${pct}%`],
    [t("docReader.voteV2.autoFixed", { defaultValue: "Tự sửa (≥3 phiếu)" }), s.auto_fixed ?? 0],
    [t("docReader.voteV2.suggested", { defaultValue: "Đề xuất (2 phiếu)" }), s.suggested ?? 0],
    [t("docReader.voteV2.tie", { defaultValue: "Hoà phiếu" }), (s.tie ?? 0) + (s.unaligned ?? 0)],
  ];

  const sel = selected != null ? lines[selected] : null;

  return (
    <div className="vote-v2">
      <div className="vote-v2-summary">
        {summary.map(([label, value]) => (
          <div key={label} className="vote-v2-metric">
            <Text type="secondary" className="vote-v2-metric-label">
              {label}
            </Text>
            <div className="vote-v2-metric-value">{value}</div>
          </div>
        ))}
      </div>

      <div className="vote-v2-engines">
        {Object.entries(meta.engines).map(([name, e]) => (
          <Tooltip key={name} title={e.excluded ?? undefined}>
            <Tag color={e.excluded ? "default" : name === meta.backbone ? "blue" : undefined}>
              {engineLabel(name)}
              {name === meta.backbone && ` · ${t("docReader.voteV2.backbone", { defaultValue: "nền" })}`}
              {e.excluded && ` · ${t("docReader.voteV2.excluded", { defaultValue: "không bỏ phiếu" })}`}
              <Text type="secondary" className="vote-v2-engine-count">
                {" "}
                {t("docReader.voteV2.chars", { defaultValue: "{{n}} chữ", n: e.han_chars })}
              </Text>
            </Tag>
          </Tooltip>
        ))}
      </div>
      {meta.page_status === "unaligned" && (
        <Text type="warning" className="vote-v2-note">
          {t("docReader.voteV2.unaligned", {
            defaultValue: "Chỉ 1 engine đọc được trang này — chưa có gì để đối chiếu, cần soát cả trang.",
          })}
        </Text>
      )}

      <div className="vote-v2-legend">
        <span>
          <span className="vote-c-fixed">字</span> {t("docReader.voteV2.legendFixed", { defaultValue: "đã tự sửa" })}
        </span>
        <span>
          <span className="vote-c-review">字</span> {t("docReader.voteV2.legendReview", { defaultValue: "cần xem (2 phiếu / có đề xuất)" })}
        </span>
        <span>
          <span className="vote-c-tie">字</span> {t("docReader.voteV2.legendTie", { defaultValue: "hoà phiếu" })}
        </span>
        <span>{t("docReader.voteV2.legendClick", { defaultValue: "Bấm 1 dòng để xem bảng đối chiếu" })}</span>
      </div>

      <div className="vote-v2-text">
        {lines.map((line, li) => (
          <button
            type="button"
            key={li}
            className={`vote-v2-line${selected === li ? " is-selected" : ""}`}
            onClick={() => setSelected(selected === li ? null : li)}
            aria-label={t("docReader.voteLine", { line: li + 1 })}
          >
            <span className="vote-v2-line-no">{li + 1}</span>
            <span className="vote-han">
              {line.chars.map((c, ci) => (
                <span key={ci}>
                  {c.inserts.map((ins, k) => (
                    <span key={`i${k}`} className="vote-c-insert" title={`+${ins.proposal}`}>
                      ‸
                    </span>
                  ))}
                  <span className={c.slot ? (STATUS_CLASS[c.slot.status] ?? "") : ""}>{c.ch}</span>
                </span>
              ))}
            </span>
          </button>
        ))}
      </div>

      {sel && selected != null && (
        <div className="vote-v2-grid-wrap">
          <Text strong>{t("docReader.voteLine", { line: selected + 1 })}</Text>
          <table className="vote-v2-grid vote-han">
            <tbody>
              {voters.map((engine) => (
                <tr key={engine}>
                  <th>
                    {engineLabel(engine)}
                    {engine === meta.backbone && ` (${t("docReader.voteV2.backbone", { defaultValue: "nền" })})`}
                  </th>
                  {sel.chars.map((c, ci) => {
                    const v = votesByEngine(c.slot, voters, c.ch)[engine];
                    const value = v === undefined ? "–" : v === "" ? "·" : v;
                    return (
                      <td key={ci} className={v !== undefined && v !== c.ch ? "vote-v2-diff" : ""}>
                        {value}
                      </td>
                    );
                  })}
                </tr>
              ))}
              <tr className="vote-v2-result">
                <th>{t("docReader.voteV2.result", { defaultValue: "Kết quả" })}</th>
                {sel.chars.map((c, ci) => (
                  <td key={ci} className={c.slot ? (STATUS_CLASS[c.slot.status] ?? "") : ""}>
                    {c.ch}
                  </td>
                ))}
              </tr>
            </tbody>
          </table>
          <ul className="vote-v2-notes">
            {sel.chars.flatMap((c, ci) => {
              const notes = [];
              if (c.slot?.status === "suggested")
                notes.push(
                  <li key={`s${ci}`}>
                    {t("docReader.voteV2.noteSuggest", {
                      defaultValue: "Chữ {{pos}}: đề xuất “{{to}}” thay cho “{{from}}”",
                      pos: ci + 1,
                      to: c.slot.proposal || t("docReader.voteNoChar"),
                      from: c.ch,
                    })}
                  </li>,
                );
              if (c.slot?.status === "auto_fixed")
                notes.push(
                  <li key={`f${ci}`}>
                    {t("docReader.voteV2.noteFixed", {
                      defaultValue: "Chữ {{pos}}: đã sửa “{{from}}” → “{{to}}”",
                      pos: ci + 1,
                      from: c.slot.backbone,
                      to: c.ch,
                    })}
                  </li>,
                );
              for (const ins of c.inserts)
                notes.push(
                  <li key={`i${ci}`}>
                    {t("docReader.voteV2.noteInsert", {
                      defaultValue: "Trước chữ {{pos}}: đề xuất thêm “{{text}}”",
                      pos: ci + 1,
                      text: ins.proposal,
                    })}
                  </li>,
                );
              return notes;
            })}
          </ul>
        </div>
      )}
    </div>
  );
}
