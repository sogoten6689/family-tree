import { useMemo, useState } from "react";
import { Button, Select, Space, Typography } from "antd";
import { ExpandOutlined, PrinterOutlined } from "@ant-design/icons";
import { useTranslation } from "react-i18next";

import type { FamilyMember } from "@/data/familyMockData";
import type { BalkanNode } from "@/lib/familyTreeApi";
import { toFamilyMembers } from "@/lib/familyTreeUtils";

import { FamilyTreeFullScreenView } from "./FamilyTreeFullScreenView";
import { FamilyTreeRendererContent } from "./FamilyTreeRendererContent";
import {
  DEFAULT_RENDERER_ID,
  DEFAULT_THEME_ID,
  FAMILY_TREE_RENDERERS,
  FAMILY_TREE_THEMES,
  type FamilyTreeVisualSettings,
  type RendererId,
  RENDERER_IDS,
  THEME_IDS,
  loadVisualSettings,
  saveVisualSettings,
  supportsFullScreen,
  supportsTheme,
} from "./familyTreeRenderers";
import { usePrintFamilyTree } from "./usePrintFamilyTree";

import "./family-tree-themes.css";
import "./family-tree-print.css";

type Props = {
  nodes: BalkanNode[];
  treeName?: string;
  members?: FamilyMember[];
  selectedMemberId?: number | null;
  onSelectMember?: (memberId: number) => void;
};

export function FamilyTreeVisualPanel({
  nodes,
  treeName,
  members: membersProp,
  selectedMemberId,
  onSelectMember,
}: Props) {
  const { t } = useTranslation();
  const { print } = usePrintFamilyTree();
  const [settings, setSettings] = useState<FamilyTreeVisualSettings>(() => loadVisualSettings());
  const [fullOpen, setFullOpen] = useState(false);

  const { rendererId, themeId } = settings;

  const members = useMemo(
    () => membersProp ?? toFamilyMembers(nodes),
    [membersProp, nodes],
  );

  const updateSettings = (next: Partial<FamilyTreeVisualSettings>) => {
    setSettings((prev) => {
      const merged = { ...prev, ...next };
      saveVisualSettings(merged);
      return merged;
    });
  };

  const rendererOptions = RENDERER_IDS.map((id) => {
    const meta = FAMILY_TREE_RENDERERS[id];
    return {
      value: id,
      label: t(meta.labelKey, { defaultValue: meta.labelDefault }),
      disabled: !meta.enabled,
    };
  });

  const themeOptions = THEME_IDS.map((id) => {
    const meta = FAMILY_TREE_THEMES[id];
    return {
      value: id,
      label: t(meta.labelKey, { defaultValue: meta.labelDefault }),
    };
  });

  const activeMeta = FAMILY_TREE_RENDERERS[rendererId];
  const rendererLabel = t(activeMeta.labelKey, { defaultValue: activeMeta.labelDefault });

  return (
    <div className="family-tree-visual-panel">
      <div className="no-print flex flex-wrap items-center justify-between gap-3 mb-4">
        <Space wrap>
          <Typography.Text type="secondary">
            {t("familyTree.renderer.styleLabel", { defaultValue: "Kiểu sơ đồ" })}:
          </Typography.Text>
          <Select<RendererId>
            value={rendererId}
            onChange={(value) => updateSettings({ rendererId: value })}
            options={rendererOptions}
            style={{ minWidth: 200 }}
          />
          {supportsTheme(rendererId) && (
            <>
              <Typography.Text type="secondary">
                {t("familyTree.renderer.themeLabel", { defaultValue: "Giao diện" })}:
              </Typography.Text>
              <Select
                value={themeId}
                onChange={(value) => updateSettings({ themeId: value })}
                options={themeOptions}
                style={{ minWidth: 140 }}
              />
            </>
          )}
          {supportsFullScreen(rendererId) && (
            <Button icon={<ExpandOutlined />} onClick={() => setFullOpen(true)}>
              {t("familyTree.renderer.viewFull", { defaultValue: "Xem toàn màn" })}
            </Button>
          )}
          <Button icon={<PrinterOutlined />} onClick={print}>
            {t("familyTree.renderer.printPdf", { defaultValue: "In PDF" })}
          </Button>
        </Space>
        <Typography.Text type="secondary" className="text-sm">
          {t("familyTree.renderer.dataHint", {
            count: nodes.length,
            renderer: rendererLabel,
            defaultValue: "{{count}} thành viên · Cùng nguồn SSOT · {{renderer}}",
          })}
        </Typography.Text>
      </div>

      <FamilyTreeRendererContent
        rendererId={rendererId}
        themeId={themeId}
        nodes={nodes}
        members={members}
        treeName={treeName}
        selectedMemberId={selectedMemberId}
        onSelectMember={onSelectMember}
      />

      <FamilyTreeFullScreenView
        open={fullOpen}
        onClose={() => setFullOpen(false)}
        rendererId={rendererId}
        themeId={themeId}
        nodes={nodes}
        members={members}
        treeName={treeName}
        selectedMemberId={selectedMemberId}
        onSelectMember={onSelectMember}
        rendererLabel={rendererLabel}
      />
    </div>
  );
}

export { DEFAULT_RENDERER_ID, DEFAULT_THEME_ID };
