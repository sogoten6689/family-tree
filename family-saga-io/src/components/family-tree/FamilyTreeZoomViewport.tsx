import { useRef, type ReactNode } from "react";

type Props = {
  scale: number;
  children: ReactNode;
  maxHeight?: number | string;
  containerRef?: React.RefObject<HTMLDivElement | null>;
  contentRef?: React.RefObject<HTMLDivElement | null>;
};

export function FamilyTreeZoomViewport({
  scale,
  children,
  maxHeight = 560,
  containerRef: containerRefProp,
  contentRef: contentRefProp,
}: Props) {
  const internalContainerRef = useRef<HTMLDivElement>(null);
  const internalContentRef = useRef<HTMLDivElement>(null);
  const containerRef = containerRefProp ?? internalContainerRef;
  const contentRef = contentRefProp ?? internalContentRef;

  return (
    <div
      ref={containerRef}
      className="family-tree-zoom-viewport overflow-auto rounded-xl border border-border bg-card"
      style={{ maxHeight }}
    >
      <div
        ref={contentRef}
        className="family-tree-zoom-content inline-block min-w-full py-4"
        style={{
          transform: `scale(${scale})`,
          transformOrigin: "top center",
        }}
      >
        <div className="flex justify-center">{children}</div>
      </div>
    </div>
  );
}
