import { useEffect, useState } from "react";
import { Button, Empty, Modal, Segmented, Typography } from "antd";
import { LeftOutlined, RightOutlined } from "@ant-design/icons";
import { useTranslation } from "react-i18next";

import { BoundingBoxOverlay, type BBoxItem } from "@/components/documents/BoundingBoxOverlay";

type ZoomableImageProps = {
  imageUrl: string;
  alt: string;
  /** Có bbox → ảnh "khung chữ" (vẽ khung cả ở ảnh nhỏ). */
  bbox?: BBoxItem[];
  showOrder?: boolean;
  /** Bấm ảnh (hoặc Enter/Space) để mở khung phóng to; khung do `PageZoomModal` hiển thị. */
  onOpen: () => void;
};

/** Ảnh trang gia phả cỡ nhỏ, bấm để mở khung phóng to. */
export function ZoomableImage({ imageUrl, alt, bbox, showOrder = false, onOpen }: ZoomableImageProps) {
  const { t } = useTranslation();
  const hasBoxes = !!bbox && bbox.length > 0;
  return (
    <div
      role="button"
      tabIndex={0}
      aria-label={t("pageViewer.zoomOpen", { defaultValue: "Phóng to: {{alt}}", alt })}
      style={{ cursor: "zoom-in", display: "inline-block", maxWidth: "100%" }}
      onClick={onOpen}
      onKeyDown={(event) => {
        if (event.key === "Enter" || event.key === " ") {
          event.preventDefault();
          onOpen();
        }
      }}
    >
      <BoundingBoxOverlay imageUrl={imageUrl} alt={alt} bbox={bbox ?? []} showBoxes={hasBoxes} showOrder={showOrder} />
    </div>
  );
}

type ZoomMode = "screen" | "natural";

type PageZoomModalProps = {
  open: boolean;
  onClose: () => void;
  /** null = trang đang xem chưa có ảnh (khung vẫn mở để chuyển tiếp sang trang khác). */
  imageUrl: string | null;
  alt: string;
  bbox?: BBoxItem[];
  showOrder?: boolean;
  /** Vị trí trang đang xem, ví dụ "3/58". */
  position: string;
  hasPrev: boolean;
  hasNext: boolean;
  onPrev: () => void;
  onNext: () => void;
};

/**
 * Khung phóng to ảnh trang, 2 chế độ — "Vừa" (vừa màn hình, thấy cả trang) và "Đầy đủ" (kích thước thật, cuộn để xem
 * chữ nhỏ) — và nút Trước / Sau (cũng phím ← / →) để xem trang khác mà không phải đóng khung. Chế độ đang chọn
 * được giữ khi chuyển trang. Bấm vào ảnh để đổi qua lại giữa hai chế độ.
 */
export function PageZoomModal({ open, onClose, imageUrl, alt, bbox, showOrder = false, position, hasPrev, hasNext, onPrev, onNext }: PageZoomModalProps) {
  const { t } = useTranslation();
  const [mode, setMode] = useState<ZoomMode>("screen");
  const hasBoxes = !!bbox && bbox.length > 0;

  useEffect(() => {
    if (!open) return;
    const onKey = (event: KeyboardEvent) => {
      const target = event.target as HTMLElement | null;
      if (target && (target.tagName === "INPUT" || target.tagName === "TEXTAREA" || target.isContentEditable)) return;
      if (event.key === "ArrowLeft" && hasPrev) onPrev();
      if (event.key === "ArrowRight" && hasNext) onNext();
    };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [open, hasPrev, hasNext, onPrev, onNext]);

  return (
    <Modal
      open={open}
      onCancel={onClose}
      footer={null}
      width="96vw"
      centered
      destroyOnHidden
      title={
        <div className="flex flex-wrap items-center gap-3">
          <Button size="small" icon={<LeftOutlined />} disabled={!hasPrev} onClick={onPrev}>
            {t("pageViewer.zoomPrev", { defaultValue: "Trang trước" })}
          </Button>
          <Typography.Text data-testid="zoom-position">{position}</Typography.Text>
          <Button size="small" disabled={!hasNext} onClick={onNext}>
            {t("pageViewer.zoomNext", { defaultValue: "Trang sau" })} <RightOutlined />
          </Button>
          <span className="text-sm font-normal">{alt}</span>
          <Segmented
            size="small"
            value={mode}
            onChange={(value) => setMode(value as ZoomMode)}
            options={[
              { value: "screen", label: t("pageViewer.zoomFit", { defaultValue: "Vừa" }) },
              { value: "natural", label: t("pageViewer.zoomFull", { defaultValue: "Đầy đủ" }) },
            ]}
          />
        </div>
      }
    >
      <div
        data-testid="zoom-body"
        data-mode={mode}
        style={{ maxHeight: "80vh", overflow: "auto", textAlign: "center", cursor: mode === "screen" ? "zoom-in" : "zoom-out" }}
        onClick={() => setMode((m) => (m === "screen" ? "natural" : "screen"))}
      >
        {imageUrl ? (
          // key đổi theo chế độ và theo ảnh để đo lại kích thước hiển thị (khung chữ phải co giãn theo ảnh).
          <BoundingBoxOverlay
            key={`${mode}|${imageUrl}`}
            imageUrl={imageUrl}
            alt={alt}
            bbox={bbox ?? []}
            showBoxes={hasBoxes}
            showOrder={showOrder}
            fit={mode}
          />
        ) : (
          <Empty description={t("pageViewer.noImage", { defaultValue: "Chưa có ảnh cho trang này" })} />
        )}
      </div>
    </Modal>
  );
}
