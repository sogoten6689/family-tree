import { Slider } from "antd";
import { useMemo, useRef, useState, type PointerEvent as ReactPointerEvent } from "react";

import type { KhungTrang } from "@/lib/doiChieuApi";

import { alignToAnchors, type DraftChar } from "./lopPhu";

export type OverlayMode = "keo" | "song";

const PAPER = "#ffffff";
const INK = "#111111";
const CHANGED = "#d4380d";

const TextPage = ({
  khung,
  draft,
  page,
  onPick,
}: {
  khung: KhungTrang;
  draft: DraftChar[];
  page: string;
  onPick: (rowKey: number) => void;
}) => {
  const placed = useMemo(
    () => alignToAnchors(khung.chu.map((c) => c.c), draft, page),
    [khung, draft, page],
  );
  return (
    <svg
      role="img"
      aria-label={`Chữ phục dựng trang ${page}`}
      viewBox={`0 0 ${khung.rong} ${khung.cao}`}
      style={{ display: "block", width: "100%", height: "auto", background: PAPER }}
    >
      {khung.chu.map(({ b }, i) => {
        const p = placed[i];
        if (!p) return null;
        const [x0, y0, x1, y1] = b;
        return (
          <text
            key={i}
            x={(x0 + x1) / 2}
            y={(y0 + y1) / 2}
            fontSize={Math.min(x1 - x0, y1 - y0) * 0.92}
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
    </svg>
  );
};

/** Ảnh gốc và chữ phục dựng đúng vị trí: kéo đường chia qua lại, hoặc đặt cạnh nhau. */
const SoatOverlay = ({
  mode,
  imageUrl,
  khung,
  draft,
  page,
  onPick,
}: {
  mode: OverlayMode;
  imageUrl: string;
  khung: KhungTrang;
  draft: DraftChar[];
  page: string;
  onPick: (rowKey: number) => void;
}) => {
  const [split, setSplit] = useState(50);
  const box = useRef<HTMLDivElement>(null);

  const moveTo = (e: ReactPointerEvent) => {
    const rect = box.current?.getBoundingClientRect();
    if (rect?.width) setSplit(Math.min(100, Math.max(0, ((e.clientX - rect.left) / rect.width) * 100)));
  };

  const image = <img src={imageUrl} alt={`Trang ${page}`} style={{ display: "block", width: "100%", height: "auto" }} />;
  const text = <TextPage khung={khung} draft={draft} page={page} onPick={onPick} />;

  if (mode === "song") {
    return (
      <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 8 }}>
        {image}
        {text}
      </div>
    );
  }
  return (
    <>
      <div ref={box} style={{ position: "relative", userSelect: "none", touchAction: "none" }}>
        {image}
        <div style={{ position: "absolute", inset: 0, clipPath: `inset(0 0 0 ${split}%)` }}>{text}</div>
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
