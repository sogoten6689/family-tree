import { CopyOutlined, EditOutlined, SnippetsOutlined, SwapOutlined } from "@ant-design/icons";
import { Button, Checkbox, Image, Input, Segmented, Tooltip } from "antd";
import { useState } from "react";
import { useTranslation } from "react-i18next";
import { BoundingBoxOverlay, type BBoxItem } from "./BoundingBoxOverlay";
import "./ReaderWorkspace.css";

type ReaderWorkspaceProps = {
  hannomText: string;
  vietnameseText: string;
  translationText?: string;
  editableHannom: boolean;
  vietnameseDisabled: boolean;
  busy: boolean;
  imageUrl: string | null;
  filename?: string;
  bbox?: BBoxItem[] | null;
  onHannomChange: (text: string) => void;
  onVietnameseChange: (text: string) => void;
  onToggleHannom: (editable: boolean) => void;
  onPaste: () => void;
  onCopy: () => void;
};

export function ReaderWorkspace(props: ReaderWorkspaceProps) {
  const { t } = useTranslation();
  const [swapped, setSwapped] = useState(false);
  const [showImage, setShowImage] = useState(true);
  const [imgMode, setImgMode] = useState<"original" | "bbox">("original");
  const hasTranslation = !!props.translationText;
  const hasBbox = !!(props.bbox && props.bbox.length > 0);
  const [mobileColumn, setMobileColumn] = useState("hannom");
  const baseColumns = swapped ? ["vietnamese", "hannom"] : ["hannom", "vietnamese"];
  const columns = hasTranslation ? [...baseColumns, "dichNghia"] : baseColumns;
  const labels: Record<string, string> = {
    hannom: t("docReader.columnHannom"),
    vietnamese: t("docReader.columnQuocNgu"),
    dichNghia: t("docReader.columnDichNghia"),
  };

  const textForColumn = (key: string): string => {
    if (key === "hannom") return props.hannomText;
    if (key === "vietnamese") return props.vietnameseText;
    return props.translationText || "";
  };

  return (
    <section className="reader-workspace" aria-label={t("docReader.workspaceLabel")}>
      <div className="reader-mobile-tabs">
        <Segmented block value={mobileColumn} onChange={setMobileColumn}
          options={columns.map((key) => ({ value: key, label: labels[key] }))} />
      </div>
      <div className="reader-columns">
        {columns.map((key) => (
          <section key={key} className={`reader-column reader-column-${key} ${mobileColumn === key ? "reader-column-active" : ""}`}>
            <h2 className="reader-column-title">{labels[key]}</h2>
            <Input.TextArea
              aria-label={labels[key]}
              value={textForColumn(key)}
              readOnly={key === "dichNghia" || props.busy || (key === "hannom" && !props.editableHannom)}
              disabled={key === "vietnamese" && props.vietnameseDisabled}
              onChange={(event) => {
                if (key === "hannom") props.onHannomChange(event.target.value);
                else if (key === "vietnamese") props.onVietnameseChange(event.target.value);
              }}
              placeholder={t(
                key === "hannom"
                  ? "docReader.hannomWorkspacePlaceholder"
                  : key === "dichNghia"
                    ? "docReader.columnDichNghia"
                    : props.vietnameseDisabled
                      ? "docReader.quocNguAwaitOcr"
                      : "docReader.quocNguPlaceholder",
              )}
              className="reader-text"
            />
          </section>
        ))}
        <Tooltip title={t("docReader.btnSwapColumns")}>
          <Button type="text" className="reader-swap" icon={<SwapOutlined />}
            aria-label={t("docReader.btnSwapColumns")} onClick={() => setSwapped((value) => !value)} />
        </Tooltip>
      </div>
      <div className="reader-toolbar">
        <div className="reader-options">
          <Checkbox checked={props.editableHannom} disabled={props.busy}
            onChange={(event) => props.onToggleHannom(event.target.checked)}>{t("docReader.chkTypeHannom")}</Checkbox>
          <Checkbox checked={showImage && !!props.imageUrl} disabled={!props.imageUrl}
            onChange={(event) => setShowImage(event.target.checked)}>{t("docReader.chkShowImageResult")}</Checkbox>
          {hasBbox && showImage && props.imageUrl && (
            <Segmented
              size="small"
              value={imgMode}
              onChange={(value) => setImgMode(value as "original" | "bbox")}
              options={[
                { value: "original", label: t("docReader.imgModeOriginal") },
                { value: "bbox", label: t("docReader.imgModeBbox") },
              ]}
            />
          )}
        </div>
        <span className="reader-count">{t("docReader.charCount", { count: Array.from(props.editableHannom ? props.hannomText : props.vietnameseText).length })}</span>
        <div className="reader-actions">
          <Tooltip title={t("docReader.btnPaste")}><Button type="text" icon={<SnippetsOutlined />}
            aria-label={t("docReader.btnPaste")} disabled={props.busy || (!props.editableHannom && props.vietnameseDisabled)} onClick={props.onPaste} /></Tooltip>
          <Tooltip title={t("docReader.btnEditHannom")}><Button type="text" icon={<EditOutlined />}
            aria-label={t("docReader.btnEditHannom")} aria-pressed={props.editableHannom} disabled={props.busy}
            onClick={() => props.onToggleHannom(!props.editableHannom)} /></Tooltip>
          <Tooltip title={t("docReader.btnCopy")}><Button type="text" icon={<CopyOutlined />}
            aria-label={t("docReader.btnCopy")} disabled={!props.vietnameseText} onClick={props.onCopy} /></Tooltip>
        </div>
        {props.editableHannom && <p className="reader-edit-hint">{t("docReader.hannomLocalEditHint")}</p>}
      </div>
      {showImage && props.imageUrl && (
        <figure className="reader-source">
          <figcaption>{t("docReader.sourceImageTitle")} <span>{props.filename}</span></figcaption>
          {hasBbox ? (
            <BoundingBoxOverlay
              imageUrl={props.imageUrl}
              alt={props.filename || t("docReader.sourceImageTitle")}
              bbox={props.bbox || []}
              showBoxes={imgMode === "bbox"}
            />
          ) : (
            <Image src={props.imageUrl} alt={props.filename || t("docReader.sourceImageTitle")} />
          )}
        </figure>
      )}
    </section>
  );
}
