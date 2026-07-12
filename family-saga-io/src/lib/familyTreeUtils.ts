import type { FamilyMember } from "@/data/familyMockData";
import type { BalkanNode, Gender } from "@/lib/familyTreeApi";

export const inferGenderFromName = (name: string): Gender => {
  return /\bThị\b/i.test(name) ? "female" : "male";
};

export const normalizeGender = (gender: string | null | undefined, name: string): Gender => {
  const raw = (gender ?? "").toLowerCase();
  if (raw === "female" || raw === "f" || raw === "nữ" || raw === "nu") return "female";
  if (raw === "male" || raw === "m" || raw === "nam") return "male";
  return inferGenderFromName(name);
};

export const toFamilyMembers = (nodes: BalkanNode[]): FamilyMember[] => {
  const personMap = new Map<string, BalkanNode>();
  const childrenMap = new Map<string, Set<string>>();
  const parentMap = new Map<string, string>();
  const spouseMap = new Map<string, Set<string>>();

  nodes.forEach((node) => {
    personMap.set(String(node.id), node);
  });

  nodes.forEach((node) => {
    const nodeId = String(node.id);
    if (typeof node.fid === "number") {
      const parentId = String(node.fid);
      if (!childrenMap.has(parentId)) childrenMap.set(parentId, new Set());
      childrenMap.get(parentId)!.add(nodeId);
      if (!parentMap.has(nodeId)) parentMap.set(nodeId, parentId);
    }
    if (typeof node.mid === "number") {
      const parentId = String(node.mid);
      if (!childrenMap.has(parentId)) childrenMap.set(parentId, new Set());
      childrenMap.get(parentId)!.add(nodeId);
      if (!parentMap.has(nodeId)) parentMap.set(nodeId, parentId);
    }

    if (Array.isArray(node.pids)) {
      node.pids.forEach((spouseIdRaw) => {
        const spouseId = String(spouseIdRaw);
        if (!spouseMap.has(nodeId)) spouseMap.set(nodeId, new Set());
        spouseMap.get(nodeId)!.add(spouseId);
      });
    }
  });

  const childIds = new Set(parentMap.keys());
  const roots = nodes.map((node) => String(node.id)).filter((id) => !childIds.has(id));
  const generationMap = new Map<string, number>();
  const queue: Array<{ id: string; generation: number }> = [];

  roots.forEach((id) => {
    generationMap.set(id, 1);
    queue.push({ id, generation: 1 });
  });

  while (queue.length > 0) {
    const current = queue.shift()!;
    const childIdsOfCurrent = childrenMap.get(current.id) ?? new Set<string>();
    childIdsOfCurrent.forEach((childId) => {
      const nextGeneration = current.generation + 1;
      if (!generationMap.has(childId) || nextGeneration < generationMap.get(childId)!) {
        generationMap.set(childId, nextGeneration);
        queue.push({ id: childId, generation: nextGeneration });
      }
    });
  }

  return nodes.map((node) => {
    const nodeId = String(node.id);
    const spouseIds = Array.from(spouseMap.get(nodeId) ?? new Set<string>());
    const spouseName = spouseIds.length > 0 ? personMap.get(spouseIds[0])?.name : undefined;
    const parentId = parentMap.get(nodeId);

    return {
      id: nodeId,
      name: node.name,
      birthYear: typeof node.birthYear === "number" ? node.birthYear : 0,
      deathYear: typeof node.deathYear === "number" ? node.deathYear : undefined,
      gender: normalizeGender(node.gender, node.name),
      generation: generationMap.get(nodeId) ?? 1,
      spouseName,
      title: typeof node.title === "string" ? node.title : undefined,
      bio: typeof node.bio === "string" ? node.bio : undefined,
      children: Array.from(childrenMap.get(nodeId) ?? new Set()),
      parentId,
      avatar: typeof node.avatar === "string" ? node.avatar : undefined,
    };
  });
};

export const toTreeStats = (nodes: BalkanNode[]) => {
  const generations = new Set<number>();
  const childIds = new Set<number>();

  nodes.forEach((node) => {
    if (typeof node.fid === "number") childIds.add(node.id);
    if (typeof node.mid === "number") childIds.add(node.id);
  });

  const rootIds = nodes.map((node) => node.id).filter((id) => !childIds.has(id));
  const generationMap = new Map<number, number>();
  const queue: Array<{ id: number; generation: number }> = [];

  rootIds.forEach((id) => {
    generationMap.set(id, 1);
    queue.push({ id, generation: 1 });
  });

  while (queue.length > 0) {
    const current = queue.shift()!;
    generations.add(current.generation);

    nodes
      .filter((node) => node.fid === current.id || node.mid === current.id)
      .forEach((child) => {
        const nextGeneration = current.generation + 1;
        if (!generationMap.has(child.id) || nextGeneration < generationMap.get(child.id)!) {
          generationMap.set(child.id, nextGeneration);
          queue.push({ id: child.id, generation: nextGeneration });
        }
      });
  }

  if (generations.size === 0 && nodes.length > 0) {
    generations.add(1);
  }

  const birthYears = nodes
    .map((node) => (typeof node.birthYear === "number" ? node.birthYear : undefined))
    .filter((year): year is number => typeof year === "number" && year > 0);

  return {
    totalMembers: nodes.length,
    totalGenerations: Math.max(1, generations.size || 1),
    established: birthYears.length > 0 ? Math.min(...birthYears) : 0,
  };
};

export const getFamilyTreePublicUrl = (treeId: string) =>
  `${window.location.origin}/gia-pha/${encodeURIComponent(treeId)}`;

export const getFamilyTreeExternalUrl = (tree: {
  id: string;
  external_url?: string | null;
}) => tree.external_url?.trim() || getFamilyTreePublicUrl(tree.id);

export const formatTreeDate = (value: string) => {
  const parsed = new Date(value);
  if (Number.isNaN(parsed.getTime())) return value;
  return parsed.toLocaleDateString("vi-VN");
};

/** Bridge FamilyMember[] → BalkanNode[] for visual panel (mock / legacy paths). */
export const membersToBalkanNodes = (members: FamilyMember[]): BalkanNode[] => {
  return members.map((member) => {
    const node: BalkanNode = {
      id: Number(member.id),
      name: member.name,
      gender: member.gender,
      birthYear: member.birthYear,
    };
    if (member.deathYear != null) node.deathYear = member.deathYear;
    if (member.title) node.title = member.title;
    if (member.bio) node.bio = member.bio;
    if (member.parentId) node.fid = Number(member.parentId);
    return node;
  });
};
