import { useRef, useState } from "react";

export type BBoxItem = {
  bbox_xyxy: [number, number, number, number];
  han?: string;
  confidence?: number | null;
};

type BoundingBoxOverlayProps = {
  imageUrl: string;
  alt?: string;
  bbox: BBoxItem[];
  showBoxes: boolean;
};

/**
 * Ảnh gốc + overlay bounding box tuỳ chọn. Toạ độ bbox_xyxy nằm trong hệ
 * pixel của ảnh GỐC (naturalWidth/Height), không phải pixel hiển thị — nên
 * phải đo kích thước hiển thị thật của <img> rồi scale lại mỗi box.
 */
export function BoundingBoxOverlay({ imageUrl, alt, bbox, showBoxes }: BoundingBoxOverlayProps) {
  const imgRef = useRef<HTMLImageElement>(null);
  const [size, setSize] = useState<{ natW: number; natH: number; dispW: number; dispH: number } | null>(null);

  const measure = () => {
    const img = imgRef.current;
    if (!img || !img.naturalWidth || !img.naturalHeight) return;
    setSize({ natW: img.naturalWidth, natH: img.naturalHeight, dispW: img.clientWidth, dispH: img.clientHeight });
  };

  const scaleX = size && size.natW ? size.dispW / size.natW : 1;
  const scaleY = size && size.natH ? size.dispH / size.natH : 1;

  return (
    <div style={{ position: "relative", display: "inline-block", lineHeight: 0, maxWidth: "100%" }}>
      <img
        ref={imgRef}
        src={imageUrl}
        alt={alt}
        onLoad={measure}
        style={{ maxWidth: "100%", display: "block" }}
      />
      {showBoxes &&
        size &&
        bbox.map((box, index) => {
          const [x0, y0, x1, y1] = box.bbox_xyxy;
          return (
            <div
              key={index}
              title={
                box.han
                  ? `${box.han}${box.confidence != null ? ` (${Math.round(box.confidence * 100)}%)` : ""}`
                  : undefined
              }
              style={{
                position: "absolute",
                left: x0 * scaleX,
                top: y0 * scaleY,
                width: Math.max(1, (x1 - x0) * scaleX),
                height: Math.max(1, (y1 - y0) * scaleY),
                border: "2px solid #ff4d4f",
                boxSizing: "border-box",
                pointerEvents: "auto",
              }}
            />
          );
        })}
    </div>
  );
}
