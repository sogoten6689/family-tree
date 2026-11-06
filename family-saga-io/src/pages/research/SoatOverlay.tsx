import { Button, Image, Slider, Space } from "antd";
import { useEffect, useMemo, useRef, useState, type Dispatch, type PointerEvent as ReactPointerEvent, type ReactNode, type SetStateAction, type UIEvent } from "react";

import type { KhungTrang } from "@/lib/doiChieuApi";

import { BAN_TAM_KEY, placeOnPage, rowKeysOf, type DraftChar, type Placed } from "./lopPhu";
import { ACTIVE_FILL, ACTIVE_STROKE, boxColor, clampZoom, gutterLabel, MAX_ZOOM, MIN_ZOOM, numberSize, rowLabels, useWheelZoom, ZOOM_STEP, type RowLabel } from "./oChu";

export type OverlayMode = "anh" | "keo" | "song" | "dich";

export { BAN_TAM_KEY };

export interface OverlayRow {
  key: number;
  viet: string;
  bo: boolean;
  danh_dau?: string | null;
}

const PAPER = "#ffffff";
const INK = "#111111";
const CHANGED = "#d4380d";
const FLAGGED = "rgba(250, 173, 20, 0.35)";
const NUMBER = "#0958d9";
const UNASSIGNED = "#d46b08";

export const ZoomBar = ({ zoom, setZoom }: { zoom: number; setZoom: Dispatch<SetStateAction<number>> }) => (
  <Space.Compact style={{ marginBottom: 8 }}>
    <Button size="small" aria-label="Thu nhỏ" disabled={zoom <= MIN_ZOOM} onClick={() => setZoom(clampZoom(zoom / ZOOM_STEP))}>
      −
    </Button>
    <Button size="small" title="Về 100%" onClick={() => setZoom(1)}>
      {Math.round(zoom * 100)}%
    </Button>
    <Button size="small" aria-label="Phóng to" disabled={zoom >= MAX_ZOOM} onClick={() => setZoom(clampZoom(zoom * ZOOM_STEP))}>
      +
    </Button>
  </Space.Compact>
);

export const Numbers = ({ labels, size, onPick }: { labels: RowLabel[]; size: number; onPick?: (key: number) => void }) => (
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
        style={onPick ? { cursor: "pointer", pointerEvents: "all" } : { pointerEvents: "none" }}
        onClick={onPick && (() => onPick(l.key))}
      >
        {l.n}
      </text>
    ))}
  </>
);

/** Nhãn của cột bản tâm: bản tâm không phải dòng nội dung nên không mang số dòng. */
export const BanTamLabel = ({ cells, width, onPick }: { cells: { b: [number, number, number, number] }[]; width: number; onPick?: (key: number) => void }) => {
  const at = gutterLabel(cells, width);
  if (!at) return null;
  const size = numberSize(width);
  return (
    <text
      data-testid="nhan-ban-tam"
      fontSize={size}
      fontWeight={700}
      fontFamily="system-ui, sans-serif"
      textAnchor="middle"
      fill={NUMBER}
      stroke={PAPER}
      strokeWidth={size * 0.25}
      paintOrder="stroke"
      style={onPick ? { cursor: "pointer", pointerEvents: "all" } : { pointerEvents: "none" }}
      onClick={onPick && (() => onPick(BAN_TAM_KEY))}
    >
      <tspan x={at.x} y={at.y - size}>Bản</tspan>
      <tspan x={at.x} y={at.y}>tâm</tspan>
    </text>
  );
};

/** Dấu "?" trên ô chưa thuộc dòng nào; không nhận chuột để bấm xuyên xuống ô. */
export const UnassignedMarks = ({ cells, width }: { cells: { b: [number, number, number, number] }[]; width: number }) => (
  <>
    {cells.map(({ b }, i) => (
      <text
        key={i}
        data-testid="dau-chua-gan"
        x={(b[0] + b[2]) / 2}
        y={(b[1] + b[3]) / 2}
        fontSize={numberSize(width)}
        fontWeight={700}
        fontFamily="system-ui, sans-serif"
        textAnchor="middle"
        dominantBaseline="central"
        fill={UNASSIGNED}
        stroke={PAPER}
        strokeWidth={numberSize(width) * 0.25}
        paintOrder="stroke"
        style={{ pointerEvents: "none" }}
      >
        ?
      </text>
    ))}
  </>
);

/** Ô quanh từng chữ và số dòng, vẽ đè lên ảnh. Chỉ ô và số nhận chuột, chỗ còn lại vẫn bấm được vào ảnh để phóng to. */
const BoxLayer = ({
  khung,
  gutterCells,
  unassigned,
  labels,
  flagged,
  active,
  onPickBox,
  onPickNumber,
}: {
  khung: KhungTrang;
  gutterCells: { b: [number, number, number, number] }[];
  unassigned: { b: [number, number, number, number] }[];
  labels: RowLabel[];
  flagged: boolean[];
  active: boolean[];
  onPickBox: (index: number) => void;
  onPickNumber: (rowKey: number) => void;
}) => (
  <svg
    aria-hidden
    viewBox={`0 0 ${khung.rong} ${khung.cao}`}
    style={{ position: "absolute", inset: 0, width: "100%", height: "100%", pointerEvents: "none" }}
  >
    {khung.chu.map(({ b, u, n }, i) => (
      <rect
        key={i}
        data-testid="o-chu"
        x={b[0]}
        y={b[1]}
        width={b[2] - b[0]}
        height={b[3] - b[1]}
        fill={active[i] ? ACTIVE_FILL : flagged[i] ? FLAGGED : "none"}
        data-danh-dau={flagged[i] || undefined}
        data-dang-chon={active[i] || undefined}
        stroke={active[i] ? ACTIVE_STROKE : boxColor({ u, n })}
        strokeWidth={active[i] ? 2 : 1}
        strokeDasharray={u ? "3 2" : undefined}
        vectorEffect="non-scaling-stroke"
        style={{ pointerEvents: "all", cursor: "pointer" }}
        onClick={() => onPickBox(i)}
      />
    ))}
    <Numbers labels={labels} size={numberSize(khung.rong)} onPick={onPickNumber} />
    <BanTamLabel cells={gutterCells} width={khung.rong} onPick={onPickNumber} />
    <UnassignedMarks cells={unassigned} width={khung.rong} />
  </svg>
);

const TextPage = ({
  khung,
  gutterCells,
  unassigned,
  placed,
  rowKeys,
  labels,
  showNumbers,
  active,
  page,
  onPick,
}: {
  khung: KhungTrang;
  gutterCells: { b: [number, number, number, number] }[];
  unassigned: { b: [number, number, number, number] }[];
  placed: (Placed | null)[];
  rowKeys: (number | null)[];
  labels: RowLabel[];
  showNumbers: boolean;
  active: boolean[];
  page: string;
  onPick: (rowKey: number) => void;
}) => (
  <svg
    role="img"
    aria-label={`Chữ phục dựng trang ${page}`}
    viewBox={`0 0 ${khung.rong} ${khung.cao}`}
    style={{ display: "block", width: "100%", height: "auto", background: PAPER }}
  >
    {khung.chu.map(({ b }, i) =>
      active[i] ? <rect key={i} data-dang-chon x={b[0]} y={b[1]} width={b[2] - b[0]} height={b[3] - b[1]} fill={ACTIVE_FILL} /> : null,
    )}
    {khung.chu.map(({ b, u, n }, i) => {
      const p = placed[i];
      if (!p) return null;
      const [x0, y0, x1, y1] = b;
      return (
        <text
          key={i}
          data-testid="chu"
          x={(x0 + x1) / 2}
          y={(y0 + y1) / 2}
          // Khung sát nét nên chữ dẹt như 一 có một chiều rất nhỏ; khung ước lượng thì rộng bằng cả cột, khung vẽ tay thì không biết sát hay rộng.
          fontSize={(u || n ? Math.min(x1 - x0, y1 - y0) : Math.max(x1 - x0, y1 - y0)) * 0.95}
          fontFamily='"Noto Serif TC", "Songti TC", "SimSun", serif'
          textAnchor="middle"
          dominantBaseline="central"
          fill={p.changed ? CHANGED : INK}
          style={{ cursor: "pointer" }}
          onClick={() => {
            const key = rowKeys[i];
            if (key !== null) onPick(key);
          }}
        >
          {p.ch}
        </text>
      );
    })}
    {showNumbers && <Numbers labels={labels} size={numberSize(khung.rong)} onPick={onPick} />}
    {showNumbers && <BanTamLabel cells={gutterCells} width={khung.rong} onPick={onPick} />}
    {showNumbers && <UnassignedMarks cells={unassigned} width={khung.rong} />}
  </svg>
);

const TranslationList = ({
  rows,
  numbers,
  banTamViet,
  activeKey,
  page,
  onPick,
}: {
  rows: OverlayRow[];
  numbers: Map<number, number>;
  banTamViet: string | null;
  activeKey: number | null;
  page: string;
  onPick: (rowKey: number) => void;
}) => (
  <div role="region" aria-label={`Bản dịch trang ${page}`} style={{ padding: "8px 12px", color: INK, fontSize: 14, lineHeight: 1.5 }}>
    {banTamViet !== null && (
      <div
        data-testid="dong-dich-ban-tam"
        data-dong-dich
        data-dang-chon={activeKey === BAN_TAM_KEY || undefined}
        style={{
          marginBottom: 8,
          paddingBottom: 8,
          borderBottom: "1px solid #d9d9d9",
          cursor: "pointer",
          background: activeKey === BAN_TAM_KEY ? ACTIVE_FILL : undefined,
        }}
        onClick={() => onPick(BAN_TAM_KEY)}
      >
        <strong style={{ color: NUMBER }}>Bản tâm: </strong>
        <span style={banTamViet.trim() ? undefined : { color: "#8c8c8c", fontStyle: "italic" }}>{banTamViet.trim() || "(chưa có bản dịch)"}</span>
      </div>
    )}
    {rows.map((r) => (
      <div
        key={r.key}
        data-testid="dong-dich"
        data-dong-dich
        data-dang-chon={activeKey === r.key || undefined}
        style={{ display: "flex", gap: 8, marginBottom: 8, cursor: "pointer", background: activeKey === r.key ? ACTIVE_FILL : undefined }}
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
  banTamViet = null,
  draft,
  rows,
  marks,
  page,
  activeKey = null,
  onPick,
  onPickTranslation,
}: {
  mode: OverlayMode;
  imageUrl: string;
  /** null hoặc chưa có: trang chưa có dữ liệu vị trí chữ, chỉ hiện ảnh và bản dịch. */
  khung: KhungTrang | null | undefined;
  /** Chữ bản tâm đang sửa của trang này. */
  banTam: string;
  /** Bản dịch bản tâm của trang này; null khi trang không có bản tâm. */
  banTamViet?: string | null;
  draft: DraftChar[];
  /** Các dòng của trang này theo đúng thứ tự, số dòng tính từ đây. */
  rows: OverlayRow[];
  marks: boolean;
  page: string;
  /** Dòng đang chọn ở phần soát; các ô và dòng dịch của nó được làm sáng. */
  activeKey?: number | null;
  onPick: (rowKey: number) => void;
  onPickTranslation: (rowKey: number) => void;
}) => {
  const [split, setSplit] = useState(50);
  const [zoom, setZoom] = useState(1);
  const [unplaced, setUnplaced] = useState(false);
  const box = useRef<HTMLDivElement>(null);
  const translations = useRef<HTMLDivElement>(null);
  const panes = useRef<(HTMLDivElement | null)[]>([]);

  const numbers = useMemo(() => new Map(rows.map((r, i) => [r.key, i + 1])), [rows]);
  const placed = useMemo(
    () =>
      khungGoc
        ? placeOnPage(khungGoc.chu.map((c) => c.c), (khungGoc.ban_tam?.chu ?? []).map((c) => c.c), draft, banTam, page)
        : [],
    [khungGoc, banTam, draft, page],
  );
  // Ô bản tâm đi cùng ô thường; rowLabels bỏ qua ô còn thuộc bản tâm vì BAN_TAM_KEY không có số dòng.
  const khung = useMemo(
    () => khungGoc && { ...khungGoc, chu: [...khungGoc.chu, ...(khungGoc.ban_tam?.chu ?? [])] },
    [khungGoc],
  );
  const rowKeys = useMemo(
    () => rowKeysOf(placed, khung?.chu ?? [], khungGoc?.chu.length ?? 0, rows.map((r) => r.key)),
    [placed, khung, khungGoc, rows],
  );
  const labels = useMemo(() => (khung ? rowLabels(khung.chu, khung.rong, rowKeys, numbers) : []), [khung, rowKeys, numbers]);
  const gutterCells = useMemo(() => (khung?.chu ?? []).filter((_, i) => rowKeys[i] === BAN_TAM_KEY), [khung, rowKeys]);
  const unassigned = useMemo(() => (khung?.chu ?? []).filter((_, i) => rowKeys[i] === null), [khung, rowKeys]);
  const active = useMemo(() => rowKeys.map((key) => key !== null && key === activeKey), [rowKeys, activeKey]);

  // Dòng vừa chọn có thể nằm ngoài phần đang nhìn thấy khi phóng to hoặc khi danh sách dịch dài. Chỉ cuộn trong khung, không cuộn cả trang.
  const zoomed = zoom > 1;
  useEffect(() => {
    if (activeKey === null) return;
    const bring = (frame: Element | null | undefined, target: Element | null | undefined) => {
      if (!frame || !target) return;
      const f = frame.getBoundingClientRect();
      const t = target.getBoundingClientRect();
      frame.scrollTop += t.top - f.top - f.height / 3;
      frame.scrollLeft += t.left + t.width / 2 - f.left - f.width / 2;
    };
    if (zoomed) panes.current.forEach((pane) => bring(pane, pane?.querySelector("rect[data-dang-chon]")));
    bring(translations.current, translations.current?.querySelector("[data-dong-dich][data-dang-chon]"));
  }, [activeKey, zoomed, mode]);

  const pickBox = (index: number) => {
    const key = rowKeys[index];
    setUnplaced(key === null);
    if (key !== null) onPick(key);
  };

  const moveTo = (e: ReactPointerEvent) => {
    const rect = box.current?.getBoundingClientRect();
    if (rect?.width) setSplit(Math.min(100, Math.max(0, ((e.clientX - rect.left) / rect.width) * 100)));
  };

  useWheelZoom(panes, setZoom, mode);

  /** Xem song song: cuộn một bên thì bên kia theo, để luôn nhìn cùng một chỗ trên trang. */
  const followScroll = (e: UIEvent<HTMLDivElement>) => {
    const { scrollLeft, scrollTop } = e.currentTarget;
    panes.current.forEach((n) => {
      if (n && n !== e.currentTarget && (n.scrollLeft !== scrollLeft || n.scrollTop !== scrollTop)) {
        n.scrollLeft = scrollLeft;
        n.scrollTop = scrollTop;
      }
    });
  };

  const pane = (index: number, content: ReactNode, sync = false) => (
    <div
      ref={(n) => {
        panes.current[index] = n;
      }}
      data-testid="khung-xem"
      onScroll={sync ? followScroll : undefined}
      // Chưa phóng to thì không tạo thanh cuộn riêng, trang cuộn như cũ.
      style={zoom > 1 ? { overflow: "auto", maxHeight: "80vh", minWidth: 0 } : { minWidth: 0 }}
    >
      <div data-testid="noi-dung-xem" style={{ width: `${zoom * 100}%` }}>
        {content}
      </div>
    </div>
  );

  const zoomBar = (
    <>
      <ZoomBar zoom={zoom} setZoom={setZoom} />
      {unplaced && (
        <span data-testid="o-chua-gan" style={{ marginLeft: 8, color: "#d46b08" }}>
          Ô này chưa thuộc dòng nào. Bấm “Sửa ô chữ”, chọn ô rồi chọn dòng cho nó.
        </span>
      )}
    </>
  );

  const flagged = useMemo(() => {
    const keys = new Set(rows.filter((r) => r.danh_dau).map((r) => r.key));
    return rowKeys.map((key) => key !== null && keys.has(key));
  }, [rows, rowKeys]);

  const layer = marks && khung ? <BoxLayer khung={khung} gutterCells={gutterCells} unassigned={unassigned} labels={labels} flagged={flagged} active={active} onPickBox={pickBox} onPickNumber={onPick} /> : null;
  const framed = (picture: ReactNode) => (
    <div style={{ position: "relative", lineHeight: 0 }}>
      {picture}
      {layer}
    </div>
  );
  const image = framed(<img src={imageUrl} alt={`Trang ${page}`} style={{ display: "block", width: "100%", height: "auto" }} />);
  const text = khung && (
    <TextPage khung={khung} gutterCells={gutterCells} unassigned={unassigned} placed={placed} rowKeys={rowKeys} labels={labels} showNumbers={marks} active={active} page={page} onPick={onPick} />
  );

  if (mode === "anh") {
    return (
      <>
        {zoomBar}
        {pane(0, framed(<Image src={imageUrl} alt={`Trang ${page}`} width="100%" style={{ width: "100%" }} />))}
      </>
    );
  }

  if (mode === "song") {
    return (
      <>
        {zoomBar}
        <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 8 }}>
          {pane(0, image, true)}
          {pane(1, text, true)}
        </div>
      </>
    );
  }

  const visibleRows = rows.filter((r) => !r.bo);
  return (
    <>
      {zoomBar}
      {pane(
        0,
        <div ref={box} style={{ position: "relative", userSelect: "none" }}>
          {image}
          {mode === "keo" ? (
            <div style={{ position: "absolute", inset: 0, clipPath: `inset(0 0 0 ${split}%)` }}>{text}</div>
          ) : (
            // Bản dịch đọc ngang nên co theo phần còn lại, thay vì bị cắt mất đầu dòng.
            <div ref={translations} style={{ position: "absolute", top: 0, bottom: 0, right: 0, left: `${split}%`, overflow: "auto", background: PAPER }}>
              <TranslationList rows={visibleRows} numbers={numbers} banTamViet={banTamViet} activeKey={activeKey} page={page} onPick={onPickTranslation} />
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
            }}
          >
            <div style={{ position: "absolute", top: 0, bottom: 0, left: 6, width: 2, background: CHANGED }} />
            {/* Giữa làn đỏ; khi phóng to thì dính giữa phần đang nhìn thấy để cuộn không mất nút. */}
            <div
              data-testid="nut-keo"
              aria-hidden
              style={{
                position: zoom > 1 ? "sticky" : "absolute",
                top: "50%",
                marginTop: -18,
                marginLeft: -11,
                width: 36,
                height: 36,
                borderRadius: "50%",
                background: CHANGED,
                color: PAPER,
                border: `2px solid ${PAPER}`,
                boxShadow: "0 1px 4px rgba(0,0,0,0.45)",
                display: "flex",
                alignItems: "center",
                justifyContent: "center",
                fontSize: 18,
                lineHeight: 1,
              }}
            >
              ↔
            </div>
          </div>
        </div>,
      )}
      <Slider aria-label="Vị trí đường chia" value={Math.round(split)} onChange={setSplit} tooltip={{ open: false }} />
    </>
  );
};

export default SoatOverlay;
