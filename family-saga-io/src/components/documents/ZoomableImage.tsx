import { useState } from "react";
import { Button, Modal, Segmented } from "antd";
import { useTranslation } from "react-i18next";

import { BoundingBoxOverlay, type BBoxItem } from "@/components/documents/BoundingBoxOverlay";

type ZoomableImageProps = {
  imageUrl: string;
  alt: string;
  /** Có bbox → ảnh "khung chữ" (vẽ khung cả ở ảnh nhỏ lẫn khi phóng to). */
  bbox?: BBoxItem[];
  showOrder?: boolean;
};

type ZoomMode = "screen" | "natural";

/**
 * Ảnh trang gia phả: bấm vào để phóng to trong khung lớn, có 2 chế độ —
 * "Vừa" (vừa màn hình, thấy cả trang) và "Đầy đủ" (kích thước thật, cuộn để xem chữ nhỏ).
 * Bấm vào ảnh trong khung để đổi qua lại giữa hai chế độ.
 */
export function ZoomableImage({ imageUrl, alt, bbox, showOrder = false }: ZoomableImageProps) {
  const { t } = useTranslation();
  const [open, setOpen] = useState(false);
  const [mode, setMode] = useState<ZoomMode>("screen");
  const hasBoxes = !!bbox && bbox.length > 0;

  return (
    <>
      <div
        role="button"
        tabIndex={0}
        aria-label={t("pageViewer.zoomOpen", { defaultValue: "Phóng to: {{alt}}", alt })}
        style={{ cursor: "zoom-in", display: "inline-block", maxWidth: "100%" }}
        onClick={() => setOpen(true)}
        onKeyDown={(event) => {
          if (event.key === "Enter" || event.key === " ") {
            event.preventDefault();
            setOpen(true);
          }
        }}
      >
        <BoundingBoxOverlay imageUrl={imageUrl} alt={alt} bbox={bbox ?? []} showBoxes={hasBoxes} showOrder={showOrder} />
      </div>
      <Modal
        open={open}
        onCancel={() => setOpen(false)}
        footer={null}
        width="96vw"
        centered
        destroyOnHidden
        title={
          <div className="flex flex-wrap items-center gap-3">
            <span>{alt}</span>
            <Segmented
              size="small"
              value={mode}
              onChange={(value) => setMode(value as ZoomMode)}
              options={[
                { value: "screen", label: t("pageViewer.zoomFit", { defaultValue: "Vừa" }) },
                { value: "natural", label: t("pageViewer.zoomFull", { defaultValue: "Đầy đủ" }) },
              ]}
            />
            <Button size="small" onClick={() => setMode((m) => (m === "screen" ? "natural" : "screen"))}>
              {mode === "screen"
                ? t("pageViewer.zoomToFull", { defaultValue: "Xem cỡ thật" })
                : t("pageViewer.zoomToFit", { defaultValue: "Thu vừa màn hình" })}
            </Button>
          </div>
        }
      >
        <div
          data-testid="zoom-body"
          data-mode={mode}
          style={{ maxHeight: "80vh", overflow: "auto", textAlign: "center", cursor: mode === "screen" ? "zoom-in" : "zoom-out" }}
          onClick={() => setMode((m) => (m === "screen" ? "natural" : "screen"))}
        >
          {/* key đổi theo chế độ để đo lại kích thước hiển thị (khung chữ phải co giãn theo ảnh). */}
          <BoundingBoxOverlay
            key={mode}
            imageUrl={imageUrl}
            alt={alt}
            bbox={bbox ?? []}
            showBoxes={hasBoxes}
            showOrder={showOrder}
            fit={mode}
          />
        </div>
      </Modal>
    </>
  );
}
