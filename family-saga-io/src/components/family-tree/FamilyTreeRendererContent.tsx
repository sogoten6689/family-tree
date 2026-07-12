import { useRef, type RefObject } from "react";

import type { FamilyMember } from "@/data/familyMockData";
import type { BalkanNode } from "@/lib/familyTreeApi";

import {
  FamilyTreeCytoscapeView,
  type CytoscapeViewHandle,
} from "./FamilyTreeCytoscapeView";
import { FamilyTreeDomView } from "./FamilyTreeDomView";
import { FamilyTreeMembersTable } from "./FamilyTreeMembersTable";
import { FamilyTreePrintPreview } from "./FamilyTreePrintPreview";
import { FamilyTreeZoomViewport } from "./FamilyTreeZoomViewport";
import type { PrintSettings } from "./familyTreePrintTypes";
import type { RendererId, ThemeId } from "./familyTreeRenderers";
import { supportsZoom } from "./familyTreeRenderers";

type Props = {
  rendererId: RendererId;
  themeId: ThemeId;
  nodes: BalkanNode[];
  members: FamilyMember[];
  treeName?: string;
  selectedMemberId?: number | null;
  onSelectMember?: (memberId: number) => void;
  graphHeight?: number | string;
  className?: string;
  domScale?: number;
  domContainerRef?: RefObject<HTMLDivElement | null>;
  domContentRef?: RefObject<HTMLDivElement | null>;
  cytoscapeRef?: RefObject<CytoscapeViewHandle | null>;
  onCytoscapeZoomChange?: (scale: number) => void;
  printSettings?: PrintSettings;
};

export function FamilyTreeRendererContent({
  rendererId,
  themeId,
  nodes,
  members,
  treeName = "Gia phả",
  selectedMemberId,
  onSelectMember,
  graphHeight = 520,
  className,
  domScale = 1,
  domContainerRef,
  domContentRef,
  cytoscapeRef,
  onCytoscapeZoomChange,
  printSettings,
}: Props) {
  const internalDomContainerRef = useRef<HTMLDivElement>(null);
  const internalDomContentRef = useRef<HTMLDivElement>(null);
  const containerRef = domContainerRef ?? internalDomContainerRef;
  const contentRef = domContentRef ?? internalDomContentRef;

  const domView = (
    <FamilyTreeDomView
      members={members}
      themeId={themeId}
      selectedMemberId={selectedMemberId}
      onSelectMember={onSelectMember}
    />
  );

  return (
    <div className={className ?? "family-tree-visual-content"}>
      {rendererId === "dom-classic" &&
        (supportsZoom(rendererId) ? (
          <FamilyTreeZoomViewport
            scale={domScale}
            maxHeight={graphHeight}
            containerRef={containerRef}
            contentRef={contentRef}
          >
            {domView}
          </FamilyTreeZoomViewport>
        ) : (
          domView
        ))}
      {rendererId === "table" && (
        <FamilyTreeMembersTable members={members} onSelectMember={onSelectMember} />
      )}
      {rendererId === "cytoscape-dagre" && (
        <FamilyTreeCytoscapeView
          ref={cytoscapeRef}
          nodes={nodes}
          height={graphHeight}
          selectedMemberId={selectedMemberId}
          onSelectMember={onSelectMember}
          onZoomChange={onCytoscapeZoomChange}
        />
      )}
      {rendererId === "print-preview" && printSettings && (
        <FamilyTreePrintPreview
          treeName={treeName}
          members={members}
          memberCount={nodes.length}
          printSettings={printSettings}
        />
      )}
    </div>
  );
}
