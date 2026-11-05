import { Alert, Button, Input, Popconfirm, Space, Typography } from "antd";
import { useEffect, useMemo, useRef, useState, type PointerEvent as ReactPointerEvent } from "react";

import type { KhungSua, KhungTrang } from "@/lib/doiChieuApi";

import { BAN_TAM_KEY, placeOnPage, rowKeysOf, type DraftChar } from "./lopPhu";
import { ACTIVE_FILL, ACTIVE_STROKE, boxColor, boxFrom, insertIndex, moveBox, numberSize, rowLabels, useWheelZoom, type Diem, type Hop, type OChu } from "./oChu";
import { Numbers, ZoomBar, type OverlayRow } from "./SoatOverlay";

const SELECTED = "#cf1322";
/** Kéo ngắn hơn chừng này (theo pixel ảnh) thì coi là bấm, không vẽ ô, để bấm nhầm không sinh ô rác. */
const MIN_DRAW = 6;
const MAX_UNDO = 100;

type EditBox = OChu & { gutter: boolean };

type Drag =
  | { kind: "ve"; start: Diem; box: Hop | null }
  | { kind: "di"; index: number; start: Diem; origin: Hop; before: EditBox[]; moved: boolean }
  | { kind: "co"; index: number; opposite: Diem; before: EditBox[]; moved: boolean };

const fromKhung = (k: KhungTrang): EditBox[] => [
  ...k.chu.map((c) => ({ ...c, gutter: false })),
  ...(k.ban_tam?.chu ?? []).map((c) => ({ ...c, gutter: true })),
];

const toCell = ({ c, b, u, n }: EditBox, width: number, height: number): OChu => ({
  c: c.trim(),
  // Ô máy có thể chưa qua bước kẹp vào ảnh, lưu lên sẽ bị từ chối cả trang.
  b: boxFrom([b[0], b[1]], [b[2], b[3]], width, height),
  ...(u ? { u } : {}),
  ...(n ? { n } : {}),
});

const edited = (box: EditBox, change: Partial<EditBox>): EditBox => {
  const { u: _estimated, ...rest } = box;
  return { ...rest, n: box.n === "them" ? "them" : "sua", ...change };
};

/** Bốn góc của ô, theo thứ tự trái trên, phải trên, phải dưới, trái dưới. */
const corners = ([x0, y0, x1, y1]: Hop): Diem[] => [
  [x0, y0],
  [x1, y0],
  [x1, y1],
  [x0, y1],
];

/** Chế độ sửa ô chữ của một trang: chọn, kéo, đổi cỡ, vẽ thêm, xoá. Lưu riêng, không đụng tệp ô của máy. */
const SuaOChu = ({
  khung,
  imageUrl,
  page,
  draft,
  banTam,
  rows,
  activeKey = null,
  onHighlight,
  onSave,
  onRestore,
  onClose,
}: {
  khung: KhungTrang;
  imageUrl: string;
  page: string;
  draft: DraftChar[];
  banTam: string;
  /** Các dòng của trang này theo đúng thứ tự, số dòng tính từ đây. */
  rows: OverlayRow[];
  activeKey?: number | null;
  /** Báo dòng của ô vừa chọn để làm sáng dòng đó ở phần soát, không chuyển con trỏ khỏi ô gõ chữ. */
  onHighlight?: (rowKey: number) => void;
  onSave: (edit: KhungSua) => Promise<KhungTrang>;
  onRestore: (phienBan: number) => Promise<KhungTrang>;
  onClose: () => void;
}) => {
  const { rong: width, cao: height } = khung;
  const [boxes, setBoxes] = useState(() => fromKhung(khung));
  const [saved, setSaved] = useState(() => JSON.stringify(fromKhung(khung)));
  const [version, setVersion] = useState(khung.phien_ban ?? 0);
  const [hasEdit, setHasEdit] = useState(!!khung.da_sua);
  const [selected, setSelected] = useState<number | null>(null);
  const [past, setPast] = useState<EditBox[][]>([]);
  const [drawing, setDrawing] = useState<Hop | null>(null);
  const [zoom, setZoom] = useState(1);
  const [busy, setBusy] = useState(false);
  const [problem, setProblem] = useState<string | null>(null);
  const svg = useRef<SVGSVGElement>(null);
  const drag = useRef<Drag | null>(null);
  const panes = useRef<(HTMLDivElement | null)[]>([]);
  useWheelZoom(panes, setZoom);

  const dirty = useMemo(() => JSON.stringify(boxes) !== saved, [boxes, saved]);
  const counts = useMemo(
    () => ({ sua: boxes.filter((b) => b.n === "sua").length, them: boxes.filter((b) => b.n === "them").length }),
    [boxes],
  );
  // Ô mới rơi vào khoảng ngang của cột bản tâm thì thuộc bản tâm.
  const gutterRange = useMemo<[number, number] | null>(() => {
    const cells = khung.ban_tam?.chu ?? [];
    return cells.length ? [Math.min(...cells.map((c) => c.b[0])), Math.max(...cells.map((c) => c.b[2]))] : null;
  }, [khung]);

  // Dóng chữ tốn thời gian và chỉ phụ thuộc vào chữ, nên kéo ô không phải tính lại.
  const bodyChars = JSON.stringify(boxes.filter((b) => !b.gutter).map((b) => b.c));
  const gutterChars = JSON.stringify(boxes.filter((b) => b.gutter).map((b) => b.c));
  const placed = useMemo(() => {
    const body: string[] = JSON.parse(bodyChars);
    return placeOnPage(body, JSON.parse(gutterChars), draft, banTam, page);
  }, [bodyChars, gutterChars, draft, banTam, page]);
  const rowKeys = useMemo(() => rowKeysOf(placed, (JSON.parse(bodyChars) as string[]).length), [placed, bodyChars]);
  const numbers = useMemo(() => new Map(rows.map((r, i) => [r.key, i + 1])), [rows]);

  const remember = (before: EditBox[]) => setPast((p) => [...p.slice(1 - MAX_UNDO), before]);

  const removeAt = (index: number) => {
    remember(boxes);
    setBoxes(boxes.filter((_, i) => i !== index));
    setSelected(null);
  };

  useEffect(() => {
    if (!dirty) return;
    const warn = (e: BeforeUnloadEvent) => e.preventDefault();
    window.addEventListener("beforeunload", warn);
    return () => window.removeEventListener("beforeunload", warn);
  }, [dirty]);

  useEffect(() => {
    if (selected === null) return;
    const onKey = (e: KeyboardEvent) => {
      const target = e.target as HTMLElement | null;
      if ((e.key === "Delete" || e.key === "Backspace") && !target?.closest?.("input, textarea")) {
        e.preventDefault();
        removeAt(selected);
      }
    };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  });

  const pointOf = (e: { clientX: number; clientY: number }): Diem | null => {
    const rect = svg.current?.getBoundingClientRect();
    if (!rect?.width || !rect.height) return null;
    return [((e.clientX - rect.left) / rect.width) * width, ((e.clientY - rect.top) / rect.height) * height];
  };

  const begin = (e: ReactPointerEvent, make: (at: Diem) => Drag) => {
    const at = pointOf(e);
    if (!at) return;
    e.stopPropagation();
    svg.current?.setPointerCapture?.(e.pointerId);
    drag.current = make(at);
  };

  const updateBox = (index: number, b: Hop, d: { before: EditBox[]; moved: boolean }) => {
    if (!d.moved) remember(d.before);
    d.moved = true;
    setBoxes((cur) => cur.map((box, i) => (i === index ? edited(box, { b }) : box)));
  };

  const onPointerMove = (e: ReactPointerEvent) => {
    const d = drag.current;
    const at = d && pointOf(e);
    if (!d || !at) return;
    if (d.kind === "ve") {
      d.box = boxFrom(d.start, at, width, height);
      setDrawing(d.box);
    } else if (d.kind === "di") {
      updateBox(d.index, moveBox(d.origin, at[0] - d.start[0], at[1] - d.start[1], width, height), d);
    } else {
      updateBox(d.index, boxFrom(d.opposite, at, width, height), d);
    }
  };

  const addBox = (b: Hop) => {
    const [x0, , x1] = b;
    const middleX = (x0 + x1) / 2;
    const gutter = !!gutterRange && gutterRange[0] <= middleX && middleX <= gutterRange[1];
    const mainCount = boxes.filter((x) => !x.gutter).length;
    const group = boxes.filter((x) => x.gutter === gutter);
    const at = (gutter ? mainCount : 0) + insertIndex(group, b);
    remember(boxes);
    setBoxes([...boxes.slice(0, at), { c: "", b, n: "them", gutter }, ...boxes.slice(at)]);
    setSelected(at);
  };

  const onPointerUp = () => {
    const d = drag.current;
    drag.current = null;
    if (d?.kind !== "ve") return;
    setDrawing(null);
    if (d.box && d.box[2] - d.box[0] >= MIN_DRAW && d.box[3] - d.box[1] >= MIN_DRAW) addBox(d.box);
    else setSelected(null);
  };

  const undo = () => {
    setBoxes(past[past.length - 1]);
    setPast(past.slice(0, -1));
    setSelected(null);
  };

  const run = async (work: () => Promise<void>) => {
    setBusy(true);
    setProblem(null);
    try {
      await work();
    } catch (e) {
      setProblem(e instanceof Error ? e.message : String(e));
    } finally {
      setBusy(false);
    }
  };

  const save = () => {
    const empty = boxes.findIndex((b) => !b.c.trim());
    if (empty >= 0) {
      setSelected(empty);
      setProblem("Còn ô chưa có chữ: gõ chữ cho ô đang chọn, hoặc xoá ô đó.");
      return;
    }
    const cellsOf = (gutter: boolean) => boxes.filter((b) => b.gutter === gutter).map((b) => toCell(b, width, height));
    void run(async () => {
      const next = await onSave({ chu: cellsOf(false), ban_tam_chu: khung.ban_tam ? cellsOf(true) : undefined, phien_ban: version });
      setVersion(next.phien_ban ?? version + 1);
      setHasEdit(true);
      setSaved(JSON.stringify(boxes));
    });
  };

  const restore = () =>
    void run(async () => {
      const machine = await onRestore(version);
      const next = fromKhung(machine);
      setBoxes(next);
      setSaved(JSON.stringify(next));
      setPast([]);
      setSelected(null);
      setVersion(0);
      setHasEdit(false);
    });

  const current = selected === null ? null : boxes[selected];
  const selectedRow = selected === null ? null : rowKeys[selected];
  const highlightKey = selected === null ? activeKey : selectedRow;
  const rowText = () => {
    if (selectedRow === BAN_TAM_KEY) return "Thuộc bản tâm.";
    if (selectedRow === null) return "Chưa gán được vào dòng nào: chữ của ô chưa khớp với các dòng soát.";
    const n = numbers.get(selectedRow);
    return n ? `Thuộc dòng ${n}.` : "Thuộc một dòng ở trang kề.";
  };
  const handle = width / 110 / zoom;

  return (
    <div data-testid="sua-o-chu">
      <Space wrap style={{ marginBottom: 8 }}>
        <ZoomBar zoom={zoom} setZoom={setZoom} />
        <Button size="small" disabled={!past.length || busy} onClick={undo}>
          Hoàn tác
        </Button>
        <Button size="small" type="primary" disabled={!dirty || busy} onClick={save}>
          {dirty ? "Lưu ô chữ" : "Đã lưu ô chữ"}
        </Button>
        {hasEdit && (
          <Popconfirm
            title="Bỏ các ô đã sửa của trang này, quay về ô máy?"
            description="Bản đã sửa vẫn được giữ trong lịch sử trên máy chủ."
            okText="Khôi phục"
            cancelText="Chưa"
            onConfirm={restore}
          >
            <Button size="small" disabled={busy}>
              Khôi phục ô máy
            </Button>
          </Popconfirm>
        )}
        <Popconfirm title="Thoát và bỏ các thay đổi chưa lưu?" okText="Bỏ thay đổi" cancelText="Ở lại" disabled={!dirty} onConfirm={onClose}>
          <Button size="small" onClick={() => !dirty && onClose()}>
            Thoát sửa ô
          </Button>
        </Popconfirm>
      </Space>
      <Typography.Paragraph type="secondary" style={{ margin: "0 0 8px" }}>
        Bấm vào ô để chọn, kéo ô để dời, kéo chấm ở góc để đổi cỡ, kéo ở chỗ trống để vẽ ô mới. Ô <span style={{ color: boxColor({ n: "sua" }) }}>xanh lá</span> là ô do người chỉnh. Có {boxes.length} ô, đã chỉnh {counts.sua}, đã thêm {counts.them}. Sửa ở đây không đổi chữ ở các dòng soát.
      </Typography.Paragraph>
      <div style={{ minHeight: 32, marginBottom: 8 }}>
        {current && selected !== null ? (
          <Space wrap>
            <span>Chữ trong ô{current.gutter ? " (bản tâm)" : ""}:</span>
            <Input
              key={selected}
              aria-label="Chữ trong ô"
              lang="zh-Hant"
              size="small"
              autoFocus={!current.c}
              maxLength={4}
              value={current.c}
              style={{ width: 72, fontSize: 16 }}
              onChange={(e) => {
                remember(boxes);
                setBoxes(boxes.map((box, i) => (i === selected ? edited(box, { c: e.target.value }) : box)));
              }}
            />
            <Button size="small" danger onClick={() => removeAt(selected)}>
              Xoá ô
            </Button>
            <Typography.Text data-testid="dong-cua-o" type={selectedRow === null ? "warning" : "secondary"}>
              {rowText()}
            </Typography.Text>
          </Space>
        ) : (
          <Typography.Text type="secondary">Chưa chọn ô nào.</Typography.Text>
        )}
      </div>
      {problem && <Alert type="error" showIcon closable style={{ marginBottom: 8 }} title={problem} onClose={() => setProblem(null)} />}
      <div
        ref={(n) => {
          panes.current[0] = n;
        }}
        data-testid="khung-xem"
        // Luôn cuộn trong khung để thanh công cụ và ô gõ chữ không trôi khỏi màn hình.
        style={{ overflow: "auto", maxHeight: "75vh", minWidth: 0 }}
      >
        <div data-testid="noi-dung-xem" style={{ position: "relative", lineHeight: 0, width: `${zoom * 100}%`, userSelect: "none" }}>
          <img src={imageUrl} alt={`Trang ${page}`} draggable={false} style={{ display: "block", width: "100%", height: "auto" }} />
          <svg
            ref={svg}
            data-testid="vung-sua-o"
            viewBox={`0 0 ${width} ${height}`}
            style={{ position: "absolute", inset: 0, width: "100%", height: "100%", cursor: "crosshair", touchAction: "none" }}
            onPointerDown={(e) => begin(e, (start) => ({ kind: "ve", start, box: null }))}
            onPointerMove={onPointerMove}
            onPointerUp={onPointerUp}
            onPointerCancel={onPointerUp}
          >
            {boxes.map((box, i) => (
              <rect
                key={i}
                data-testid="o-sua"
                data-chon={i === selected || undefined}
                data-dang-chon={(rowKeys[i] !== null && rowKeys[i] === highlightKey) || undefined}
                x={box.b[0]}
                y={box.b[1]}
                width={box.b[2] - box.b[0]}
                height={box.b[3] - box.b[1]}
                fill={i === selected ? "rgba(207, 19, 34, 0.15)" : rowKeys[i] !== null && rowKeys[i] === highlightKey ? ACTIVE_FILL : "transparent"}
                stroke={i === selected ? SELECTED : rowKeys[i] !== null && rowKeys[i] === highlightKey ? ACTIVE_STROKE : boxColor(box)}
                strokeWidth={i === selected ? 2 : 1}
                strokeDasharray={box.u ? "3 2" : undefined}
                vectorEffect="non-scaling-stroke"
                style={{ cursor: "move" }}
                onPointerDown={(e) => {
                  setSelected(i);
                  const row = rowKeys[i];
                  if (row !== null) onHighlight?.(row);
                  begin(e, (start) => ({ kind: "di", index: i, start, origin: box.b, before: boxes, moved: false }));
                }}
              />
            ))}
            <Numbers labels={rowLabels(boxes, width, placed, numbers)} size={numberSize(width)} />
            {current &&
              selected !== null &&
              corners(current.b).map(([x, y], corner) => (
                <circle
                  key={corner}
                  data-testid="goc-o"
                  cx={x}
                  cy={y}
                  r={handle}
                  fill={SELECTED}
                  stroke="#ffffff"
                  strokeWidth={1}
                  vectorEffect="non-scaling-stroke"
                  style={{ cursor: corner % 2 ? "nesw-resize" : "nwse-resize" }}
                  onPointerDown={(e) =>
                    begin(e, () => ({ kind: "co", index: selected, opposite: corners(current.b)[(corner + 2) % 4], before: boxes, moved: false }))
                  }
                />
              ))}
            {drawing && (
              <rect
                data-testid="o-dang-ve"
                x={drawing[0]}
                y={drawing[1]}
                width={drawing[2] - drawing[0]}
                height={drawing[3] - drawing[1]}
                fill="rgba(56, 158, 13, 0.15)"
                stroke={boxColor({ n: "them" })}
                strokeWidth={2}
                vectorEffect="non-scaling-stroke"
                pointerEvents="none"
              />
            )}
          </svg>
        </div>
      </div>
    </div>
  );
};

export default SuaOChu;
