import { Answer, REL_TYPES } from "./types";

/** Kiểm tra nhãn giống validate_data.py; trả về danh sách cảnh báo (chuỗi). */
export function checkAnswer(a: Answer | null, input: string): string[] {
  if (!a) return ["Response không phải JSON hợp lệ"];
  const out: string[] = [];
  const names = new Map<string, Set<string | null>>();
  for (const p of a.persons) {
    if (!p.name || p.name.trim().split(/\s+/).length < 2) out.push(`Tên chưa đủ họ tên: "${p.name}"`);
    else if (!input.toLowerCase().includes(p.name.toLowerCase()))
      out.push(`"${p.name}" không có nguyên văn trong văn bản`);
    if (p.birth != null && p.death != null && p.death < p.birth) out.push(`"${p.name}" mất trước khi sinh`);
    if (!names.has(p.name)) names.set(p.name, new Set());
    names.get(p.name)!.add(p.gender);
  }
  const need: Record<string, string> = { father: "male", son: "male", mother: "female", daughter: "female" };
  const spouses = new Map<string, Set<string>>();
  const parents = new Map<string, { father?: string; mother?: string }>();
  for (const r of a.relations) {
    if (!REL_TYPES.includes(r.type)) out.push(`Loại quan hệ lạ: ${r.type}`);
    for (const n of [r.from, r.to]) if (!names.has(n)) out.push(`Quan hệ nhắc "${n}" không có trong persons`);
    if (r.from === r.to) out.push(`Quan hệ tự trỏ: ${r.from}`);
    const g = need[r.type];
    if (g && names.has(r.from) && !names.get(r.from)!.has(g as "male"))
      out.push(`${r.type}: "${r.from}" cần giới tính ${g}`);
    if (r.type === "spouse") {
      for (const [x, y] of [[r.from, r.to], [r.to, r.from]]) {
        if (!spouses.has(x)) spouses.set(x, new Set());
        spouses.get(x)!.add(y);
      }
    }
    if (r.type === "father" || r.type === "mother") {
      const p = parents.get(r.to) ?? {};
      p[r.type] = r.from;
      parents.set(r.to, p);
    }
  }
  const relSet = new Set(a.relations.map((r) => `${r.from}|${r.to}|${r.type}`));
  for (const [child, p] of parents) {
    if (p.father && !p.mother && spouses.get(p.father)?.size === 1) {
      const wife = [...spouses.get(p.father)!][0];
      out.push(`"${p.father}" là cha của "${child}" và chỉ có một vợ "${wife}" — thiếu quan hệ mẹ`);
    }
    const gs = names.get(child);
    const inv = gs?.has("male") ? "son" : gs?.has("female") ? "daughter" : null;
    for (const par of [p.father, p.mother]) {
      if (par && inv && !relSet.has(`${child}|${par}|${inv}`)) out.push(`Thiếu quan hệ ngược ${child} → ${par} (${inv})`);
    }
  }
  return [...new Set(out)];
}
