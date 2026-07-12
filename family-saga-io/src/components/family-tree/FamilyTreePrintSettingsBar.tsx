import { InputNumber, Select, Space, Typography } from "antd";
import { useTranslation } from "react-i18next";

import type { PrintMode, PrintOrientation, PrintSettings } from "./familyTreePrintTypes";

type Props = {
  settings: PrintSettings;
  pageCount: number;
  onChange: (next: Partial<PrintSettings>) => void;
};

export function FamilyTreePrintSettingsBar({ settings, pageCount, onChange }: Props) {
  const { t } = useTranslation();

  const modeOptions: Array<{ value: PrintMode; label: string }> = [
    { value: "natural", label: t("familyTree.renderer.printNatural", { defaultValue: "Kích thước thật" }) },
    { value: "fit-page", label: t("familyTree.renderer.printFitPage", { defaultValue: "Vừa 1 trang" }) },
    { value: "fit-width", label: t("familyTree.renderer.printFitWidth", { defaultValue: "Vừa chiều ngang" }) },
    {
      value: "split-generation",
      label: t("familyTree.renderer.printSplitGen", { defaultValue: "Chia theo đời" }),
    },
  ];

  const orientationOptions: Array<{ value: PrintOrientation; label: string }> = [
    { value: "portrait", label: t("familyTree.renderer.printPortrait", { defaultValue: "Dọc" }) },
    { value: "landscape", label: t("familyTree.renderer.printLandscape", { defaultValue: "Ngang" }) },
  ];

  return (
    <Space wrap className="no-print w-full">
      <Typography.Text type="secondary">
        {t("familyTree.renderer.printModeLabel", { defaultValue: "Chế độ in" })}:
      </Typography.Text>
      <Select<PrintMode>
        value={settings.mode}
        onChange={(mode) => onChange({ mode })}
        options={modeOptions}
        style={{ minWidth: 160 }}
      />
      <Typography.Text type="secondary">
        {t("familyTree.renderer.printOrientationLabel", { defaultValue: "Hướng" })}:
      </Typography.Text>
      <Select<PrintOrientation>
        value={settings.orientation}
        onChange={(orientation) => onChange({ orientation })}
        options={orientationOptions}
        style={{ minWidth: 100 }}
      />
      {settings.mode === "split-generation" && (
        <>
          <Typography.Text type="secondary">
            {t("familyTree.renderer.printGenPerPage", { defaultValue: "Đời/trang" })}:
          </Typography.Text>
          <InputNumber
            min={1}
            max={10}
            value={settings.generationsPerPage}
            onChange={(value) => onChange({ generationsPerPage: value ?? 3 })}
          />
        </>
      )}
      <Typography.Text type="secondary" className="text-sm">
        {t("familyTree.renderer.printPageCount", {
          count: pageCount,
          defaultValue: "{{count}} trang",
        })}
      </Typography.Text>
    </Space>
  );
}
