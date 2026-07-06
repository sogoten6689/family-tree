import { useEffect, useMemo, useRef, useState } from "react";
import { Alert, Spin } from "antd";
import FamilyTree from "@balkangraph/familytree.js";

export type BalkanNode = Record<string, unknown>;

function toFamilyTreeNodes(raw: BalkanNode[]): object[] {
  return raw.map((n) => {
    const rawId = n.id ?? n.node_id;
    const idNum =
      typeof rawId === "number" && Number.isFinite(rawId) ? rawId : Number(rawId);
    const row: Record<string, unknown> = {
      ...n,
      id: Number.isFinite(idNum) ? idNum : rawId,
      name: typeof n.name === "string" ? n.name : `Node ${rawId ?? "?"}`,
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
  treeId?: string;
  className?: string;
  height?: number;
};

export function BalkanFamilyTreeView({
  nodes,
  treeId,
  className = "",
  height = 520,
}: Props) {
  const containerRef = useRef<HTMLDivElement>(null);
  const [error, setError] = useState<string | null>(null);
  const [ready, setReady] = useState(false);
  const nodesKey = useMemo(() => JSON.stringify(nodes), [nodes]);

  useEffect(() => {
    const el = containerRef.current;
    if (!el || nodes.length === 0) {
      setReady(false);
      setError(null);
      return undefined;
    }

    setError(null);
    setReady(false);
    el.innerHTML = "";

    let chart: FamilyTree | null = null;
    let cancelled = false;

    const timer = window.setTimeout(() => {
      if (cancelled || !containerRef.current) return;

      try {
        chart = new FamilyTree(containerRef.current, {
          template: "hugo",
          nodeBinding: {
            field_0: "name",
            field_1: "birthYear",
          },
        });
        chart.on("render", () => {
          if (!cancelled) setReady(true);
        });
        chart.load(toFamilyTreeNodes(nodes));
        if (!cancelled) setReady(true);
      } catch (err) {
        const message = err instanceof Error ? err.message : "Unknown error";
        setError(message);
        setReady(false);
      }
    }, 0);

    return () => {
      cancelled = true;
      window.clearTimeout(timer);
      if (chart) {
        try {
          chart.destroy();
        } catch (e) {
          console.warn("Error destroying FamilyTree chart:", e);
        }
      }
    };
  }, [nodesKey, nodes.length, treeId]);

  if (nodes.length === 0) {
    return null;
  }

  return (
    <div className={`relative w-full ${className}`}>
      {!ready && !error && (
        <div
          className="absolute inset-0 z-10 flex items-center justify-center rounded-xl border border-border bg-card/80 backdrop-blur-sm"
          style={{ minHeight: height }}
        >
          <Spin size="large" />
        </div>
      )}
      {error && (
        <Alert
          type="error"
          showIcon
          className="mb-3"
          message="Không thể hiển thị cây gia phả"
          description={error}
        />
      )}
      <div
        ref={containerRef}
        key={treeId ?? nodesKey}
        className="w-full rounded-xl border border-border bg-card overflow-auto"
        style={{ minHeight: height, height }}
      />
    </div>
  );
}
