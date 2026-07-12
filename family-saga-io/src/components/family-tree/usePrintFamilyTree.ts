import { useCallback } from "react";

import type { PrintSettings } from "./familyTreePrintTypes";

const PRINT_STYLE_ID = "family-tree-print-page-style";

export function usePrintFamilyTree(printSettings?: PrintSettings) {
  const print = useCallback(() => {
    document.body.classList.add("family-tree-printing");

    const existing = document.getElementById(PRINT_STYLE_ID);
    existing?.remove();

    const style = document.createElement("style");
    style.id = PRINT_STYLE_ID;
    const orientation = printSettings?.orientation === "landscape" ? "landscape" : "portrait";
    style.textContent = `@page { size: A4 ${orientation}; margin: 12mm; }`;
    document.head.appendChild(style);

    const cleanup = () => {
      document.body.classList.remove("family-tree-printing");
      document.getElementById(PRINT_STYLE_ID)?.remove();
      window.removeEventListener("afterprint", cleanup);
    };
    window.addEventListener("afterprint", cleanup);
    window.print();
  }, [printSettings?.orientation]);

  return { print };
}
