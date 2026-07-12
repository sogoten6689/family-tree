import type { BalkanNode } from "@/lib/familyTreeApi";
import { normalizeGender } from "@/lib/familyTreeUtils";

export type GraphNode = {
  id: string;
  label: string;
  gender: "male" | "female";
};

export type GraphEdge = {
  id: string;
  source: string;
  target: string;
  kind: "parent" | "spouse";
};

export function balkanNodesToGraph(nodes: BalkanNode[]): {
  nodes: GraphNode[];
  edges: GraphEdge[];
} {
  const graphNodes: GraphNode[] = nodes.map((node) => ({
    id: String(node.id),
    label: node.name,
    gender: normalizeGender(node.gender, node.name),
  }));

  const edges: GraphEdge[] = [];
  const edgeKeys = new Set<string>();

  const addEdge = (source: string, target: string, kind: GraphEdge["kind"], suffix: string) => {
    if (source === target) return;
    const key = kind === "spouse" ? [source, target].sort().join("|") : `${source}->${target}`;
    if (edgeKeys.has(key)) return;
    edgeKeys.add(key);
    edges.push({ id: `${kind}-${source}-${target}-${suffix}`, source, target, kind });
  };

  nodes.forEach((node) => {
    const nodeId = String(node.id);
    if (typeof node.fid === "number") {
      addEdge(String(node.fid), nodeId, "parent", "f");
    }
    if (typeof node.mid === "number") {
      addEdge(String(node.mid), nodeId, "parent", "m");
    }
    if (Array.isArray(node.pids)) {
      node.pids.forEach((spouseId) => {
        addEdge(nodeId, String(spouseId), "spouse", "s");
      });
    }
  });

  return { nodes: graphNodes, edges };
}
