import { useCallback, useEffect, useRef } from "react";
import cytoscape, { type Core } from "cytoscape";
// @ts-expect-error cytoscape-dagre has no bundled types
import dagre from "cytoscape-dagre";

import type { BalkanNode } from "@/lib/familyTreeApi";

import { balkanNodesToGraph } from "./familyTreeGraphAdapter";

cytoscape.use(dagre);

type Props = {
  nodes: BalkanNode[];
  height?: number | string;
  selectedMemberId?: number | null;
  onSelectMember?: (memberId: number) => void;
};

export function FamilyTreeCytoscapeView({
  nodes,
  height = 520,
  selectedMemberId,
  onSelectMember,
}: Props) {
  const containerRef = useRef<HTMLDivElement>(null);
  const cyRef = useRef<Core | null>(null);

  const mountGraph = useCallback(() => {
    if (!containerRef.current || nodes.length === 0) return;

    const { nodes: graphNodes, edges } = balkanNodesToGraph(nodes);
    cyRef.current?.destroy();

    const cy = cytoscape({
      container: containerRef.current,
      elements: [
        ...graphNodes.map((node) => ({
          data: {
            id: node.id,
            label: node.label,
            gender: node.gender,
          },
        })),
        ...edges.map((edge) => ({
          data: {
            id: edge.id,
            source: edge.source,
            target: edge.target,
            kind: edge.kind,
          },
        })),
      ],
      style: [
        {
          selector: "node",
          style: {
            label: "data(label)",
            "text-valign": "center",
            "text-halign": "center",
            "font-size": 10,
            "background-color": "#c9a227",
            color: "#1a1a1a",
            width: 72,
            height: 36,
            shape: "round-rectangle",
            "text-wrap": "ellipsis",
            "text-max-width": 64,
          },
        },
        {
          selector: 'node[gender = "female"]',
          style: {
            "background-color": "#8b3a3a",
            color: "#fff",
          },
        },
        {
          selector: "edge[kind = 'parent']",
          style: {
            width: 2,
            "line-color": "#9a7b2f",
            "target-arrow-color": "#9a7b2f",
            "target-arrow-shape": "triangle",
            "curve-style": "bezier",
          },
        },
        {
          selector: "edge[kind = 'spouse']",
          style: {
            width: 1.5,
            "line-color": "#94a3b8",
            "line-style": "dashed",
            "curve-style": "bezier",
          },
        },
        {
          selector: "node:selected",
          style: {
            "border-width": 3,
            "border-color": "#1677ff",
          },
        },
      ],
      layout: {
        name: "dagre",
        rankDir: "TB",
        spacingFactor: 1.1,
        nodeSep: 28,
        rankSep: 56,
      },
      minZoom: 0.2,
      maxZoom: 2.5,
      wheelSensitivity: 0.2,
    });

    cy.on("tap", "node", (event) => {
      const id = Number(event.target.id());
      if (!Number.isNaN(id)) {
        onSelectMember?.(id);
      }
    });

    cyRef.current = cy;
  }, [nodes, onSelectMember]);

  useEffect(() => {
    mountGraph();
    return () => {
      cyRef.current?.destroy();
      cyRef.current = null;
    };
  }, [mountGraph]);

  useEffect(() => {
    const cy = cyRef.current;
    if (!cy) return;
    cy.nodes().unselect();
    if (selectedMemberId != null) {
      const node = cy.getElementById(String(selectedMemberId));
      if (node.nonempty()) {
        node.select();
        cy.animate({ center: { eles: node }, zoom: 1 }, { duration: 200 });
      }
    }
  }, [selectedMemberId]);

  useEffect(() => {
    const handleResize = () => cyRef.current?.resize();
    window.addEventListener("resize", handleResize);
    return () => window.removeEventListener("resize", handleResize);
  }, []);

  return (
    <div
      ref={containerRef}
      className="w-full rounded-xl border border-border bg-card"
      style={{ height }}
    />
  );
}
