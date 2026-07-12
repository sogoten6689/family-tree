import { useMemo } from "react";
import { Button, Select, Space } from "antd";
import { CompressOutlined, MinusOutlined, PlusOutlined } from "@ant-design/icons";
import { useTranslation } from "react-i18next";

import { ZOOM_PRESETS, zoomToPercent } from "./familyTreeZoom";

type Props = {
  scale: number;
  onZoomIn: () => void;
  onZoomOut: () => void;
  onSetScale: (scale: number) => void;
  onFit: () => void;
  onReset: () => void;
};

export function FamilyTreeZoomToolbar({
  scale,
  onZoomIn,
  onZoomOut,
  onSetScale,
  onFit,
  onReset,
}: Props) {
  const { t } = useTranslation();
  const percent = zoomToPercent(scale);

  const percentOptions = useMemo(() => {
    const base = ZOOM_PRESETS.map((preset) => ({
      value: Math.round(preset * 100),
      label: `${Math.round(preset * 100)}%`,
    }));
    if (!base.some((opt) => opt.value === percent)) {
      base.push({ value: percent, label: `${percent}%` });
    }
    return base.sort((a, b) => a.value - b.value);
  }, [percent]);

  return (
    <Space.Compact className="no-print">
      <Button icon={<MinusOutlined />} onClick={onZoomOut} aria-label="Zoom out" />
      <Select
        value={percent}
        onChange={(value) => onSetScale(value / 100)}
        style={{ width: 88 }}
        options={percentOptions}
        popupMatchSelectWidth={false}
      />
      <Button icon={<PlusOutlined />} onClick={onZoomIn} aria-label="Zoom in" />
      <Button icon={<CompressOutlined />} onClick={onFit}>
        {t("familyTree.renderer.zoomFit", { defaultValue: "Fit" })}
      </Button>
      <Button onClick={onReset}>{t("familyTree.renderer.zoomReset", { defaultValue: "100%" })}</Button>
    </Space.Compact>
  );
}
