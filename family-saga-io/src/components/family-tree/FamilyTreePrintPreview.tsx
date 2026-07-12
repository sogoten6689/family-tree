import { useLayoutEffect, useMemo, useRef, useState } from "react";
import { Typography } from "antd";
import { useTranslation } from "react-i18next";

import type { FamilyMember } from "@/data/familyMockData";

import { FamilyTreeDomView } from "./FamilyTreeDomView";
import {
  buildPrintPages,
  computePrintScale,
  filterMembersByIds,
} from "./familyTreePrintLayout";
import type { PrintSettings } from "./familyTreePrintTypes";

type Props = {
  treeName: string;
  members: FamilyMember[];
  memberCount: number;
  printSettings: PrintSettings;
};

function PrintPageBlock({
  title,
  members,
  scale,
}: {
  title: string;
  members: FamilyMember[];
  scale?: number;
}) {
  const measureRef = useRef<HTMLDivElement>(null);
  const [computedScale, setComputedScale] = useState(scale);

  useLayoutEffect(() => {
    if (scale != null) {
      setComputedScale(scale);
      return;
    }
    setComputedScale(undefined);
  }, [scale, members]);

  return (
    <section className="print-page mb-8 last:mb-0">
      <Typography.Title level={5} className="!mb-3 text-center">
        {title}
      </Typography.Title>
      <div
        ref={measureRef}
        className="print-page-body"
        style={
          computedScale != null
            ? {
                transform: `scale(${computedScale})`,
                transformOrigin: "top center",
              }
            : undefined
        }
      >
        <FamilyTreeDomView members={members} themeId="print-a4" />
      </div>
    </section>
  );
}

export function FamilyTreePrintPreview({ treeName, members, memberCount, printSettings }: Props) {
  const { t } = useTranslation();
  const printedAt = useMemo(() => new Date().toLocaleDateString("vi-VN"), []);
  const rootRef = useRef<HTMLDivElement>(null);
  const [fitScale, setFitScale] = useState<number | undefined>();

  const pages = useMemo(() => buildPrintPages(members, printSettings), [members, printSettings]);

  useLayoutEffect(() => {
    if (printSettings.mode !== "fit-page" && printSettings.mode !== "fit-width") {
      setFitScale(undefined);
      return;
    }
    const el = rootRef.current?.querySelector(".print-page-body") as HTMLElement | null;
    if (!el) return;
    const scale = computePrintScale(el.scrollWidth, el.scrollHeight, printSettings);
    setFitScale(scale);
  }, [members, printSettings, pages]);

  const orientationClass =
    printSettings.orientation === "landscape" ? "print-orientation-landscape" : "print-orientation-portrait";

  return (
    <div
      ref={rootRef}
      className={`family-tree-print-root rounded-lg border border-border bg-background p-6 ${orientationClass}`}
      data-print-mode={printSettings.mode}
    >
      <header className="text-center mb-6 border-b border-border pb-4 print-page-header">
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

      {pages.map((page) => {
        const pageMembers = filterMembersByIds(members, page.memberIds);
        const pageScale =
          printSettings.mode === "fit-page" || printSettings.mode === "fit-width" ? fitScale : undefined;
        return (
          <PrintPageBlock
            key={page.id}
            title={pages.length > 1 ? page.title : ""}
            members={pageMembers}
            scale={pageScale}
          />
        );
      })}

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
