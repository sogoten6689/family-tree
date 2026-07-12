import { useMemo } from "react";
import { Typography } from "antd";
import { useTranslation } from "react-i18next";

import type { FamilyMember } from "@/data/familyMockData";

import { FamilyTreeDomView } from "./FamilyTreeDomView";

type Props = {
  treeName: string;
  members: FamilyMember[];
  memberCount: number;
};

export function FamilyTreePrintPreview({ treeName, members, memberCount }: Props) {
  const { t } = useTranslation();
  const printedAt = useMemo(() => new Date().toLocaleDateString("vi-VN"), []);

  return (
    <div className="family-tree-print-root rounded-lg border border-border bg-background p-6">
      <header className="text-center mb-6 border-b border-border pb-4">
        <Typography.Title level={3} className="!mb-1 !font-display">
          {treeName}
        </Typography.Title>
        <Typography.Text type="secondary">
          {t("familyTree.renderer.printHeader", {
            count: memberCount,
            defaultValue: "Gia phả — {{count}} thành viên",
          })}
        </Typography.Text>
      </header>

      <FamilyTreeDomView members={members} themeId="print-a4" />

      <footer className="mt-8 pt-4 border-t border-border text-center text-xs text-muted-foreground">
        <div>
          {t("familyTree.renderer.printFooterDate", {
            date: printedAt,
            defaultValue: "In ngày {{date}}",
          })}
        </div>
        <div>{t("familyTree.renderer.printFooterSource", { defaultValue: "Nguồn dữ liệu: SSOT BalkanNode[]" })}</div>
      </footer>
    </div>
  );
}
