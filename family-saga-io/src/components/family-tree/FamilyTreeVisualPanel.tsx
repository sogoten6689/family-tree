import { useMemo, useState } from "react";
import { Select, Space, Typography } from "antd";
import { useTranslation } from "react-i18next";

import type { FamilyMember } from "@/data/familyMockData";
import type { BalkanNode } from "@/lib/familyTreeApi";
import { toFamilyMembers } from "@/lib/familyTreeUtils";

import { FamilyTreeDomView } from "./FamilyTreeDomView";
import { FamilyTreeMembersTable } from "./FamilyTreeMembersTable";
import {
  DEFAULT_RENDERER_ID,
  FAMILY_TREE_RENDERERS,
  type RendererId,
  RENDERER_IDS,
  loadRendererId,
  saveRendererId,
} from "./familyTreeRenderers";

type Props = {
  nodes: BalkanNode[];
  members?: FamilyMember[];
  selectedMemberId?: number | null;
  onSelectMember?: (memberId: number) => void;
};

export function FamilyTreeVisualPanel({
  nodes,
  members: membersProp,
  selectedMemberId,
  onSelectMember,
}: Props) {
  const { t } = useTranslation();
  const [rendererId, setRendererId] = useState<RendererId>(() => loadRendererId());

  const members = useMemo(
    () => membersProp ?? toFamilyMembers(nodes),
    [membersProp, nodes],
  );

  const handleRendererChange = (nextId: RendererId) => {
    setRendererId(nextId);
    saveRendererId(nextId);
  };

  const selectOptions = RENDERER_IDS.map((id) => {
    const meta = FAMILY_TREE_RENDERERS[id];
    return {
      value: id,
      label: t(meta.labelKey, { defaultValue: meta.labelDefault }),
      disabled: !meta.enabled,
    };
  });

  const activeMeta = FAMILY_TREE_RENDERERS[rendererId];

  return (
    <div>
      <div className="flex flex-wrap items-center justify-between gap-3 mb-4">
        <Space wrap>
          <Typography.Text type="secondary">
            {t("familyTree.renderer.styleLabel", { defaultValue: "Kiểu sơ đồ" })}:
          </Typography.Text>
          <Select<RendererId>
            value={rendererId}
            onChange={handleRendererChange}
            options={selectOptions}
            style={{ minWidth: 200 }}
            optionRender={(option) => {
              const id = option.value as RendererId;
              const meta = FAMILY_TREE_RENDERERS[id];
              if (meta.enabled) return option.label;
              return (
                <span>
                  {option.label}{" "}
                  <Typography.Text type="secondary" className="text-xs">
                    ({t("familyTree.renderer.comingSoon", { defaultValue: "Sắp có" })})
                  </Typography.Text>
                </span>
              );
            }}
          />
        </Space>
        <Typography.Text type="secondary" className="text-sm">
          {t("familyTree.renderer.dataHint", {
            count: nodes.length,
            renderer: t(activeMeta.labelKey, { defaultValue: activeMeta.labelDefault }),
            defaultValue: "{{count}} thành viên · Cùng nguồn SSOT · {{renderer}}",
          })}
        </Typography.Text>
      </div>

      {rendererId === "dom-classic" && (
        <FamilyTreeDomView
          members={members}
          selectedMemberId={selectedMemberId}
          onSelectMember={onSelectMember}
        />
      )}
      {rendererId === "table" && (
        <FamilyTreeMembersTable members={members} onSelectMember={onSelectMember} />
      )}
      {rendererId === "cytoscape" && (
        <Typography.Text type="secondary">
          {t("familyTree.renderer.cytoscapeHint", {
            defaultValue: "Graph tương tác sẽ có trong bản cập nhật sau.",
          })}
        </Typography.Text>
      )}
    </div>
  );
}

export { DEFAULT_RENDERER_ID };
