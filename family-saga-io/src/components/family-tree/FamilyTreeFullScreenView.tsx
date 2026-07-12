import { Modal, Typography } from "antd";
import { useTranslation } from "react-i18next";

import type { FamilyMember } from "@/data/familyMockData";
import type { BalkanNode } from "@/lib/familyTreeApi";

import { FamilyTreeRendererContent } from "./FamilyTreeRendererContent";
import type { RendererId, ThemeId } from "./familyTreeRenderers";

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
}: Props) {
  const { t } = useTranslation();

  return (
    <Modal
      open={open}
      onCancel={onClose}
      footer={null}
      width="100vw"
      destroyOnClose
      className="family-tree-fullscreen-modal"
      title={
        <Typography.Text>
          {t("familyTree.renderer.fullScreenTitle", {
            renderer: rendererLabel,
            count: nodes.length,
            defaultValue: "{{renderer}} · {{count}} thành viên",
          })}
        </Typography.Text>
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
      />
    </Modal>
  );
}
