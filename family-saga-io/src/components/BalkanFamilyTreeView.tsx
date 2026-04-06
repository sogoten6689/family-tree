import { useEffect, useMemo, useRef } from "react";
import FamilyTree from "@balkangraph/familytree.js";

export type BalkanNode = Record<string, unknown>;

function toFamilyTreeNodes(raw: BalkanNode[]): object[] {
  return raw.map((n) => {
    const idNum =
      typeof n.id === "number" && Number.isFinite(n.id)
        ? n.id
        : Number(n.id);
    const row: Record<string, unknown> = {
      ...n,
      id: Number.isFinite(idNum) ? idNum : n.id,
    };
    if (Array.isArray(n.pids)) {
      row.pids = n.pids
        .map((x) => (typeof x === "number" ? x : Number(x)))
        .filter((x) => Number.isFinite(x));
    }
    for (const k of ["fid", "mid"] as const) {
      const v = n[k];
      if (v == null) continue;
      const num = typeof v === "number" ? v : Number(v);
      if (Number.isFinite(num)) row[k] = num;
    }
    return row;
  });
}

type Props = {
  nodes: BalkanNode[];
  className?: string;
  height?: number;
};

export function BalkanFamilyTreeView({
  nodes,
  className = "",
  height = 520,
}: Props) {
  const containerRef = useRef<HTMLDivElement>(null);
  const nodesKey = useMemo(() => JSON.stringify(nodes), [nodes]);

  useEffect(() => {
    const el = containerRef.current;
    if (!el || nodes.length === 0) return undefined;

    const chart = new FamilyTree(el, {
      nodeBinding: {
        field_0: "name",
        field_1: "birthYear",
      },
    });
    chart.load(toFamilyTreeNodes(nodes));

    return () => {
      chart.destroy();
    };
  }, [nodesKey, nodes.length]);

  if (nodes.length === 0) return null;

  return (
    <div
      ref={containerRef}
      className={`w-full rounded-xl border border-[hsl(36,30%,80%)] bg-[hsl(39,50%,96%)] overflow-hidden ${className}`}
      style={{ minHeight: Math.min(height, 400), height }}
    />
  );
}
