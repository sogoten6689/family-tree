import { useMemo, useRef, useState } from "react";
import { Button, Select, Space, Typography } from "antd";
import { ExpandOutlined, PrinterOutlined } from "@ant-design/icons";
import { useTranslation } from "react-i18next";

import type { FamilyMember } from "@/data/familyMockData";
import type { BalkanNode } from "@/lib/familyTreeApi";
import { toFamilyMembers } from "@/lib/familyTreeUtils";

import type { CytoscapeViewHandle } from "./FamilyTreeCytoscapeView";
import { FamilyTreeFullScreenView } from "./FamilyTreeFullScreenView";
import { FamilyTreePrintSettingsBar } from "./FamilyTreePrintSettingsBar";
import { FamilyTreeRendererContent } from "./FamilyTreeRendererContent";
import { FamilyTreeZoomToolbar } from "./FamilyTreeZoomToolbar";
import { buildPrintPages } from "./familyTreePrintLayout";
import {
  DEFAULT_PRINT_SETTINGS,
  type PrintSettings,
  loadPrintSettings,
  savePrintSettings,
} from "./familyTreePrintTypes";
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
  supportsZoom,
} from "./familyTreeRenderers";
import { useDomZoom } from "./useDomZoom";
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
  const [settings, setSettings] = useState<FamilyTreeVisualSettings>(() => loadVisualSettings());
  const [printSettings, setPrintSettings] = useState<PrintSettings>(() => loadPrintSettings());
  const [fullOpen, setFullOpen] = useState(false);
  const [cyScale, setCyScale] = useState(1);

  const domZoom = useDomZoom();
  const domContainerRef = useRef<HTMLDivElement>(null);
  const domContentRef = useRef<HTMLDivElement>(null);
  const cytoscapeRef = useRef<CytoscapeViewHandle>(null);

  const { rendererId, themeId } = settings;
  const { print } = usePrintFamilyTree(printSettings);

  const members = useMemo(
    () => membersProp ?? toFamilyMembers(nodes),
    [membersProp, nodes],
  );

  const printPages = useMemo(
    () => buildPrintPages(members, printSettings),
    [members, printSettings],
  );

  const updateSettings = (next: Partial<FamilyTreeVisualSettings>) => {
    setSettings((prev) => {
      const merged = { ...prev, ...next };
      saveVisualSettings(merged);
      return merged;
    });
  };

  const updatePrintSettings = (next: Partial<PrintSettings>) => {
    setPrintSettings((prev) => {
      const merged = { ...prev, ...next };
      savePrintSettings(merged);
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
  const zoomEnabled = supportsZoom(rendererId);
  const activeZoomScale = rendererId === "cytoscape-dagre" ? cyScale : domZoom.scale;

  const handleZoomIn = () => {
    if (rendererId === "cytoscape-dagre") {
      cytoscapeRef.current?.zoomIn();
      return;
    }
    domZoom.zoomIn();
  };

  const handleZoomOut = () => {
    if (rendererId === "cytoscape-dagre") {
      cytoscapeRef.current?.zoomOut();
      return;
    }
    domZoom.zoomOut();
  };

  const handleSetZoom = (scale: number) => {
    if (rendererId === "cytoscape-dagre") {
      cytoscapeRef.current?.setZoom(scale);
      return;
    }
    domZoom.setZoom(scale);
  };

  const handleFit = () => {
    if (rendererId === "cytoscape-dagre") {
      cytoscapeRef.current?.fit();
      return;
    }
    domZoom.fit(domContainerRef.current, domContentRef.current);
  };

  const handleResetZoom = () => {
    if (rendererId === "cytoscape-dagre") {
      cytoscapeRef.current?.reset();
      return;
    }
    domZoom.reset();
  };

  const handlePrint = () => {
    const goPrint = () => {
      requestAnimationFrame(() => {
        requestAnimationFrame(() => print());
      });
    };
    if (rendererId !== "print-preview") {
      updateSettings({ rendererId: "print-preview" });
      goPrint();
      return;
    }
    goPrint();
  };

  return (
    <div className="family-tree-visual-panel">
      <div className="no-print flex flex-col gap-3 mb-4">
        <div className="flex flex-wrap items-center justify-between gap-3">
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
            {zoomEnabled && (
              <FamilyTreeZoomToolbar
                scale={activeZoomScale}
                onZoomIn={handleZoomIn}
                onZoomOut={handleZoomOut}
                onSetScale={handleSetZoom}
                onFit={handleFit}
                onReset={handleResetZoom}
              />
            )}
            {supportsFullScreen(rendererId) && (
              <Button icon={<ExpandOutlined />} onClick={() => setFullOpen(true)}>
                {t("familyTree.renderer.viewFull", { defaultValue: "Xem toàn màn" })}
              </Button>
            )}
            <Button icon={<PrinterOutlined />} onClick={handlePrint}>
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

        <FamilyTreePrintSettingsBar
          settings={printSettings}
          pageCount={printPages.length}
          onChange={updatePrintSettings}
        />
      </div>

      {!fullOpen && (
        <FamilyTreeRendererContent
          rendererId={rendererId}
          themeId={themeId}
          nodes={nodes}
          members={members}
          treeName={treeName}
          selectedMemberId={selectedMemberId}
          onSelectMember={onSelectMember}
          domScale={domZoom.scale}
          domContainerRef={domContainerRef}
          domContentRef={domContentRef}
          cytoscapeRef={cytoscapeRef}
          onCytoscapeZoomChange={setCyScale}
          printSettings={printSettings}
        />
      )}

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
        domZoom={domZoom}
        domContainerRef={domContainerRef}
        domContentRef={domContentRef}
        cytoscapeRef={cytoscapeRef}
        cyScale={cyScale}
        onCytoscapeZoomChange={setCyScale}
        printSettings={printSettings}
      />
    </div>
  );
}

export { DEFAULT_RENDERER_ID, DEFAULT_THEME_ID, DEFAULT_PRINT_SETTINGS };
