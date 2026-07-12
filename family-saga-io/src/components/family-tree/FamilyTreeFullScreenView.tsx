import { useRef } from "react";
import { Modal, Space, Typography } from "antd";
import { useTranslation } from "react-i18next";

import type { FamilyMember } from "@/data/familyMockData";
import type { BalkanNode } from "@/lib/familyTreeApi";

import type { CytoscapeViewHandle } from "./FamilyTreeCytoscapeView";
import { FamilyTreeRendererContent } from "./FamilyTreeRendererContent";
import { FamilyTreeZoomToolbar } from "./FamilyTreeZoomToolbar";
import type { PrintSettings } from "./familyTreePrintTypes";
import type { RendererId, ThemeId } from "./familyTreeRenderers";
import { supportsZoom } from "./familyTreeRenderers";
import type { useDomZoom } from "./useDomZoom";

type DomZoom = ReturnType<typeof useDomZoom>;

type Props = {
  open: boolean;
  onClose: () => void;
  rendererId: RendererId;
  themeId: ThemeId;
  nodes: BalkanNode[];
  members: FamilyMember[];
  treeName?: string;
  selectedMemberId?: number | null;
  onSelectMember?: (memberId: number) => void;
  rendererLabel: string;
  domZoom: DomZoom;
  domContainerRef: React.RefObject<HTMLDivElement | null>;
  domContentRef: React.RefObject<HTMLDivElement | null>;
  cytoscapeRef: React.RefObject<CytoscapeViewHandle | null>;
  cyScale: number;
  onCytoscapeZoomChange: (scale: number) => void;
  printSettings: PrintSettings;
};

export function FamilyTreeFullScreenView({
  open,
  onClose,
  rendererId,
  themeId,
  nodes,
  members,
  treeName,
  selectedMemberId,
  onSelectMember,
  rendererLabel,
  domZoom,
  domContainerRef,
  domContentRef,
  cytoscapeRef,
  cyScale,
  onCytoscapeZoomChange,
  printSettings,
}: Props) {
  const { t } = useTranslation();
  const fullDomContainerRef = useRef<HTMLDivElement>(null);
  const fullDomContentRef = useRef<HTMLDivElement>(null);

  const zoomEnabled = supportsZoom(rendererId);
  const activeZoomScale = rendererId === "cytoscape-dagre" ? cyScale : domZoom.scale;
  const containerRef = open && rendererId === "dom-classic" ? fullDomContainerRef : domContainerRef;
  const contentRef = open && rendererId === "dom-classic" ? fullDomContentRef : domContentRef;

  const handleZoomIn = () => {
    if (rendererId === "cytoscape-dagre") cytoscapeRef.current?.zoomIn();
    else domZoom.zoomIn();
  };

  const handleZoomOut = () => {
    if (rendererId === "cytoscape-dagre") cytoscapeRef.current?.zoomOut();
    else domZoom.zoomOut();
  };

  const handleSetZoom = (scale: number) => {
    if (rendererId === "cytoscape-dagre") cytoscapeRef.current?.setZoom(scale);
    else domZoom.setZoom(scale);
  };

  const handleFit = () => {
    if (rendererId === "cytoscape-dagre") {
      cytoscapeRef.current?.fit();
      return;
    }
    domZoom.fit(containerRef.current, contentRef.current);
  };

  const handleResetZoom = () => {
    if (rendererId === "cytoscape-dagre") cytoscapeRef.current?.reset();
    else domZoom.reset();
  };

  return (
    <Modal
      open={open}
      onCancel={onClose}
      footer={null}
      width="100vw"
      destroyOnClose={false}
      className="family-tree-fullscreen-modal"
      title={
        <Space wrap>
          <Typography.Text>
            {t("familyTree.renderer.fullScreenTitle", {
              renderer: rendererLabel,
              count: nodes.length,
              defaultValue: "{{renderer}} · {{count}} thành viên",
            })}
          </Typography.Text>
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
        </Space>
      }
      styles={{
        body: {
          height: "calc(100vh - 110px)",
          overflow: "auto",
          padding: 16,
        },
      }}
      style={{ top: 0, margin: 0, padding: 0, maxWidth: "100vw" }}
    >
      <FamilyTreeRendererContent
        rendererId={rendererId}
        themeId={themeId}
        nodes={nodes}
        members={members}
        treeName={treeName}
        selectedMemberId={selectedMemberId}
        onSelectMember={onSelectMember}
        graphHeight="calc(100vh - 160px)"
        domScale={domZoom.scale}
        domContainerRef={fullDomContainerRef}
        domContentRef={fullDomContentRef}
        cytoscapeRef={cytoscapeRef}
        onCytoscapeZoomChange={onCytoscapeZoomChange}
        printSettings={printSettings}
      />
    </Modal>
  );
}
