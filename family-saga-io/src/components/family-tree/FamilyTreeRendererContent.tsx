import type { FamilyMember } from "@/data/familyMockData";
import type { BalkanNode } from "@/lib/familyTreeApi";

import { FamilyTreeCytoscapeView } from "./FamilyTreeCytoscapeView";
import { FamilyTreeDomView } from "./FamilyTreeDomView";
import { FamilyTreeMembersTable } from "./FamilyTreeMembersTable";
import { FamilyTreePrintPreview } from "./FamilyTreePrintPreview";
import type { RendererId, ThemeId } from "./familyTreeRenderers";

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
}: Props) {
  return (
    <div className={className ?? "family-tree-visual-content"}>
      {rendererId === "dom-classic" && (
        <FamilyTreeDomView
          members={members}
          themeId={themeId}
          selectedMemberId={selectedMemberId}
          onSelectMember={onSelectMember}
        />
      )}
      {rendererId === "table" && (
        <FamilyTreeMembersTable members={members} onSelectMember={onSelectMember} />
      )}
      {rendererId === "cytoscape-dagre" && (
        <FamilyTreeCytoscapeView
          nodes={nodes}
          height={graphHeight}
          selectedMemberId={selectedMemberId}
          onSelectMember={onSelectMember}
        />
      )}
      {rendererId === "print-preview" && (
        <FamilyTreePrintPreview treeName={treeName} members={members} memberCount={nodes.length} />
      )}
    </div>
  );
}
