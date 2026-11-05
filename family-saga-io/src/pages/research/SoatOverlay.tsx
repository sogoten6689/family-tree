import { Image, Slider } from "antd";
import { useMemo, useRef, useState, type PointerEvent as ReactPointerEvent, type ReactNode } from "react";

import type { KhungTrang } from "@/lib/doiChieuApi";

import { alignToAnchors, draftChars, type DraftChar, type Placed } from "./lopPhu";

export type OverlayMode = "anh" | "keo" | "song" | "dich";

/** Khóa giả của cột bản tâm: không phải dòng soát nên không có số dòng, bấm vào thì tới ô sửa bản tâm. */
export const BAN_TAM_KEY = -1;

export interface OverlayRow {
  key: number;
  viet: string;
  bo: boolean;
}

const PAPER = "#ffffff";
const INK = "#111111";
const CHANGED = "#d4380d";
const BOX = "#1677ff";
const BOX_ESTIMATED = "#d46b08";
const NUMBER = "#0958d9";

interface RowLabel {
  n: number;
  key: number;
  x: number;
  y: number;
}

const numberSize = (khung: KhungTrang) => khung.rong / 50;

/** Số dòng đặt ngay trên chữ đầu tiên của dòng đó. */
const rowLabels = (khung: KhungTrang, placed: (Placed | null)[], numbers: Map<number, number>): RowLabel[] => {
  const seen = new Set<number>();
  const labels: RowLabel[] = [];
  placed.forEach((p, i) => {
    const n = p && numbers.get(p.rowKey);
    if (!p || !n || seen.has(p.rowKey)) return;
    seen.add(p.rowKey);
    const [x0, y0, x1] = khung.chu[i].b;
    const size = numberSize(khung);
    // Dòng sát mép trên thì giữ số trong khung ảnh, chấp nhận đè lên chữ.
    labels.push({ n, key: p.rowKey, x: (x0 + x1) / 2, y: Math.max(size, y0 - size * 0.25) });
  });
  return labels;
};

const Numbers = ({ labels, size, onPick }: { labels: RowLabel[]; size: number; onPick?: (key: number) => void }) => (
  <>
    {labels.map((l) => (
      <text
        key={l.key}
        data-testid="so-dong"
        x={l.x}
        y={l.y}
        fontSize={size}
        fontWeight={700}
        fontFamily="system-ui, sans-serif"
        textAnchor="middle"
        fill={NUMBER}
        stroke={PAPER}
        strokeWidth={size * 0.25}
        paintOrder="stroke"
        style={onPick ? { cursor: "pointer" } : undefined}
        onClick={onPick && (() => onPick(l.key))}
      >
        {l.n}
      </text>
    ))}
  </>
);

/** Ô quanh từng chữ và số dòng, vẽ đè lên ảnh; không nhận chuột để vẫn phóng to được ảnh. */
const BoxLayer = ({ khung, labels }: { khung: KhungTrang; labels: RowLabel[] }) => (
  <svg
    aria-hidden
    viewBox={`0 0 ${khung.rong} ${khung.cao}`}
    style={{ position: "absolute", inset: 0, width: "100%", height: "100%", pointerEvents: "none" }}
  >
    {khung.chu.map(({ b, u }, i) => (
      <rect
        key={i}
        data-testid="o-chu"
        x={b[0]}
        y={b[1]}
        width={b[2] - b[0]}
        height={b[3] - b[1]}
        fill="none"
        stroke={u ? BOX_ESTIMATED : BOX}
        strokeWidth={1}
        strokeDasharray={u ? "3 2" : undefined}
        vectorEffect="non-scaling-stroke"
      />
    ))}
    <Numbers labels={labels} size={numberSize(khung)} />
  </svg>
);

const TextPage = ({
  khung,
  placed,
  labels,
  showNumbers,
  page,
  onPick,
}: {
  khung: KhungTrang;
  placed: (Placed | null)[];
  labels: RowLabel[];
  showNumbers: boolean;
  page: string;
  onPick: (rowKey: number) => void;
}) => (
  <svg
    role="img"
    aria-label={`Chữ phục dựng trang ${page}`}
    viewBox={`0 0 ${khung.rong} ${khung.cao}`}
    style={{ display: "block", width: "100%", height: "auto", background: PAPER }}
  >
    {khung.chu.map(({ b, u }, i) => {
      const p = placed[i];
      if (!p) return null;
      const [x0, y0, x1, y1] = b;
      return (
        <text
          key={i}
          data-testid="chu"
          x={(x0 + x1) / 2}
          y={(y0 + y1) / 2}
          // Khung sát nét nên chữ dẹt như 一 có một chiều rất nhỏ; khung ước lượng thì rộng bằng cả cột.
          fontSize={(u ? Math.min(x1 - x0, y1 - y0) : Math.max(x1 - x0, y1 - y0)) * 0.95}
          fontFamily='"Noto Serif TC", "Songti TC", "SimSun", serif'
          textAnchor="middle"
          dominantBaseline="central"
          fill={p.changed ? CHANGED : INK}
          style={{ cursor: "pointer" }}
          onClick={() => onPick(p.rowKey)}
        >
          {p.ch}
        </text>
      );
    })}
    {showNumbers && <Numbers labels={labels} size={numberSize(khung)} onPick={onPick} />}
  </svg>
);

const TranslationList = ({
  rows,
  numbers,
  page,
  onPick,
}: {
  rows: OverlayRow[];
  numbers: Map<number, number>;
  page: string;
  onPick: (rowKey: number) => void;
}) => (
  <div role="region" aria-label={`Bản dịch trang ${page}`} style={{ padding: "8px 12px", color: INK, fontSize: 14, lineHeight: 1.5 }}>
    {rows.map((r) => (
      <div
        key={r.key}
        data-testid="dong-dich"
        style={{ display: "flex", gap: 8, marginBottom: 8, cursor: "pointer" }}
        onClick={() => onPick(r.key)}
      >
        <strong style={{ color: NUMBER, flex: "none", minWidth: 20, textAlign: "right" }}>{numbers.get(r.key)}</strong>
        <span style={r.viet.trim() ? undefined : { color: "#8c8c8c", fontStyle: "italic" }}>{r.viet.trim() || "(chưa có bản dịch)"}</span>
      </div>
    ))}
  </div>
);

/** Ảnh gốc, kèm chữ phục dựng đúng vị trí hoặc bản dịch: kéo đường chia qua lại, hoặc đặt cạnh nhau. */
const SoatOverlay = ({
  mode,
  imageUrl,
  khung: khungGoc,
  banTam,
  draft,
  rows,
  marks,
  page,
  onPick,
  onPickTranslation,
}: {
  mode: OverlayMode;
  imageUrl: string;
  /** null hoặc chưa có: trang chưa có dữ liệu vị trí chữ, chỉ hiện ảnh và bản dịch. */
  khung: KhungTrang | null | undefined;
  /** Chữ bản tâm đang sửa của trang này. */
  banTam: string;
  draft: DraftChar[];
  /** Các dòng của trang này theo đúng thứ tự, số dòng tính từ đây. */
  rows: OverlayRow[];
  marks: boolean;
  page: string;
  onPick: (rowKey: number) => void;
  onPickTranslation: (rowKey: number) => void;
}) => {
  const [split, setSplit] = useState(50);
  const box = useRef<HTMLDivElement>(null);

  const numbers = useMemo(() => new Map(rows.map((r, i) => [r.key, i + 1])), [rows]);
  const placed = useMemo(() => {
    if (!khungGoc) return [];
    const body = alignToAnchors(khungGoc.chu.map((c) => c.c), draft, page);
    const gutter = khungGoc.ban_tam?.chu ?? [];
    const gutterDraft = draftChars([{ key: BAN_TAM_KEY, trang: page, han: banTam, viet: "", bo: false }]);
    return [...body, ...alignToAnchors(gutter.map((c) => c.c), gutterDraft, page)];
  }, [khungGoc, banTam, draft, page]);
  // Ô bản tâm đi cùng ô thường; rowLabels bỏ qua chúng vì BAN_TAM_KEY không có số dòng.
  const khung = useMemo(
    () => khungGoc && { ...khungGoc, chu: [...khungGoc.chu, ...(khungGoc.ban_tam?.chu ?? [])] },
    [khungGoc],
  );
  const labels = useMemo(() => (khung ? rowLabels(khung, placed, numbers) : []), [khung, placed, numbers]);

  const moveTo = (e: ReactPointerEvent) => {
    const rect = box.current?.getBoundingClientRect();
    if (rect?.width) setSplit(Math.min(100, Math.max(0, ((e.clientX - rect.left) / rect.width) * 100)));
  };

  const layer = marks && khung ? <BoxLayer khung={khung} labels={labels} /> : null;
  const framed = (picture: ReactNode) => (
    <div style={{ position: "relative", lineHeight: 0 }}>
      {picture}
      {layer}
    </div>
  );
  const image = framed(<img src={imageUrl} alt={`Trang ${page}`} style={{ display: "block", width: "100%", height: "auto" }} />);
  const text = khung && (
    <TextPage khung={khung} placed={placed} labels={labels} showNumbers={marks} page={page} onPick={onPick} />
  );

  if (mode === "anh") return framed(<Image src={imageUrl} alt={`Trang ${page}`} width="100%" style={{ width: "100%" }} />);

  if (mode === "song") {
    return (
      <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 8 }}>
        {image}
        {text}
      </div>
    );
  }

  const visibleRows = rows.filter((r) => !r.bo);
  return (
    <>
      <div ref={box} style={{ position: "relative", userSelect: "none" }}>
        {image}
        {mode === "keo" ? (
          <div style={{ position: "absolute", inset: 0, clipPath: `inset(0 0 0 ${split}%)` }}>{text}</div>
        ) : (
          // Bản dịch đọc ngang nên co theo phần còn lại, thay vì bị cắt mất đầu dòng.
          <div style={{ position: "absolute", top: 0, bottom: 0, right: 0, left: `${split}%`, overflow: "auto", background: PAPER }}>
            <TranslationList rows={visibleRows} numbers={numbers} page={page} onPick={onPickTranslation} />
          </div>
        )}
        <div
          data-testid="duong-chia"
          title="Kéo qua lại để so ảnh với chữ"
          onPointerDown={(e) => {
            e.currentTarget.setPointerCapture?.(e.pointerId);
            moveTo(e);
          }}
          onPointerMove={(e) => {
            if (e.buttons) moveTo(e);
          }}
          style={{
            position: "absolute",
            top: 0,
            bottom: 0,
            left: `calc(${split}% - 7px)`,
            width: 14,
            cursor: "ew-resize",
            touchAction: "none",
            display: "flex",
            justifyContent: "center",
          }}
        >
          <div style={{ width: 2, background: CHANGED }} />
        </div>
      </div>
      <Slider aria-label="Vị trí đường chia" value={Math.round(split)} onChange={setSplit} tooltip={{ open: false }} />
    </>
  );
};

export default SoatOverlay;
