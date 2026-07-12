import { useCallback } from "react";

export function usePrintFamilyTree() {
  const print = useCallback(() => {
    document.body.classList.add("family-tree-printing");
    const cleanup = () => {
      document.body.classList.remove("family-tree-printing");
      window.removeEventListener("afterprint", cleanup);
    };
    window.addEventListener("afterprint", cleanup);
    window.print();
  }, []);

  return { print };
}
