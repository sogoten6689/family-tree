import type { FamilyMember } from "@/data/familyMockData";

import type { PrintPage, PrintSettings } from "./familyTreePrintTypes";

const A4_WIDTH_MM = 210;
const A4_HEIGHT_MM = 297;
const MM_TO_PX = 3.78;

export function getPrintPageSizePx(orientation: PrintSettings["orientation"]) {
  const widthMm = orientation === "landscape" ? A4_HEIGHT_MM : A4_WIDTH_MM;
  const heightMm = orientation === "landscape" ? A4_WIDTH_MM : A4_HEIGHT_MM;
  const marginMm = 12;
  return {
    width: (widthMm - marginMm * 2) * MM_TO_PX,
    height: (heightMm - marginMm * 2) * MM_TO_PX,
  };
}

function membersForGenerations(
  members: FamilyMember[],
  minGen: number,
  maxGen: number,
): FamilyMember[] {
  const inRange = members.filter((m) => m.generation >= minGen && m.generation <= maxGen);
  const ids = new Set(inRange.map((m) => m.id));
  return members.filter((m) => {
    if (ids.has(m.id)) return true;
    if (m.parentId && ids.has(m.parentId)) return true;
    return false;
  });
}

export function buildPrintPages(members: FamilyMember[], settings: PrintSettings): PrintPage[] {
  if (members.length === 0) return [];

  if (settings.mode === "split-generation") {
    const generations = [...new Set(members.map((m) => m.generation))].sort((a, b) => a - b);
    const perPage = Math.max(1, settings.generationsPerPage);
    const pages: PrintPage[] = [];

    for (let i = 0; i < generations.length; i += perPage) {
      const chunk = generations.slice(i, i + perPage);
      const minGen = chunk[0];
      const maxGen = chunk[chunk.length - 1];
      const pageMembers = membersForGenerations(members, minGen, maxGen);
      pages.push({
        id: `gen-${minGen}-${maxGen}`,
        title: minGen === maxGen ? `Đời ${minGen}` : `Đời ${minGen}–${maxGen}`,
        memberIds: pageMembers.map((m) => m.id),
      });
    }
    return pages;
  }

  return [
    {
      id: "all",
      title: "Toàn bộ",
      memberIds: members.map((m) => m.id),
    },
  ];
}

export function computePrintScale(
  contentWidth: number,
  contentHeight: number,
  settings: PrintSettings,
): number | undefined {
  if (settings.mode !== "fit-page" && settings.mode !== "fit-width") return undefined;
  const { width, height } = getPrintPageSizePx(settings.orientation);
  if (contentWidth <= 0 || contentHeight <= 0) return 1;

  if (settings.mode === "fit-width") {
    return Math.min(1, width / contentWidth);
  }

  return Math.min(1, width / contentWidth, height / contentHeight);
}

export function filterMembersByIds(members: FamilyMember[], ids: string[]): FamilyMember[] {
  const idSet = new Set(ids);
  return members.filter((m) => idSet.has(m.id));
}
