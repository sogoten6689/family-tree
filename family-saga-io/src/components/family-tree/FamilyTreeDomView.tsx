import { useMemo, type ReactNode } from "react";

import FamilyTreeNode from "@/components/FamilyTreeNode";
import type { FamilyMember } from "@/data/familyMockData";

import type { ThemeId } from "./familyTreeRenderers";

type Props = {
  members: FamilyMember[];
  themeId?: ThemeId | "print-a4";
  selectedMemberId?: number | null;
  onSelectMember?: (memberId: number) => void;
};

export function FamilyTreeDomView({
  members,
  themeId = "default",
  selectedMemberId,
  onSelectMember,
}: Props) {
  const roots = useMemo(() => {
    const withoutParent = members.filter((member) => !member.parentId);
    if (withoutParent.length > 0) return withoutParent;
    return members.length > 0 ? [members[0]] : [];
  }, [members]);

  const getChildren = (parentId: string) => members.filter((member) => member.parentId === parentId);

  const handleSelect = (member: FamilyMember) => {
    onSelectMember?.(Number(member.id));
  };

  const renderTree = (member: FamilyMember): ReactNode => {
    const children = getChildren(member.id);
    const isSelected = selectedMemberId != null && Number(member.id) === selectedMemberId;

    return (
      <div key={member.id} className="flex flex-col items-center">
        <FamilyTreeNode member={member} onSelect={handleSelect} isSelected={isSelected} />
        {children.length > 0 && (
          <>
            <div className="tree-connector-v h-6" />
            <div className="flex gap-4 relative">
              {children.length > 1 && (
                <div
                  className="tree-connector-h absolute top-0"
                  style={{
                    width: "calc(100% - 180px)",
                    left: "90px",
                  }}
                />
              )}
              {children.map((child) => (
                <div key={child.id} className="flex flex-col items-center">
                  <div className="tree-connector-v h-6" />
                  {renderTree(child)}
                </div>
              ))}
            </div>
          </>
        )}
      </div>
    );
  };

  if (roots.length === 0) {
    return null;
  }

  return (
    <div className={`family-tree-dom family-tree-theme-${themeId} overflow-x-auto py-4`}>
      <div className="flex flex-wrap justify-center gap-12 min-w-max mx-auto">
        {roots.map((root) => (
          <div key={root.id} className="flex flex-col items-center">
            {renderTree(root)}
          </div>
        ))}
      </div>
    </div>
  );
}
