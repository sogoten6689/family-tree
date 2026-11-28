import { REL_TYPES, type LlmAnswer, type LlmSample, type RelType } from "@/lib/llmSoatApi";

/** Cảnh báo cho nhãn, giống research/llm_extraction/validate_data.py (chế độ --real). */
export function checkAnswer(a: LlmAnswer | null, input: string): string[] {
  if (!a) return ["Response không phải JSON hợp lệ"];
  const out: string[] = [];
  const genders = new Map<string, Set<string | null>>();
  const text = input.toLowerCase();
  for (const p of a.persons) {
    if (!p.name || p.name.trim().split(/\s+/).length < 2) out.push(`Tên chưa đủ họ tên: "${p.name}"`);
    else if (!text.includes(p.name.toLowerCase())) out.push(`"${p.name}" không có nguyên văn trong văn bản`);
    if (p.birth != null && p.death != null && p.death < p.birth) out.push(`"${p.name}" mất trước khi sinh`);
    if (!genders.has(p.name)) genders.set(p.name, new Set());
    genders.get(p.name)!.add(p.gender);
  }
  const need: Partial<Record<RelType, string>> = { father: "male", son: "male", mother: "female", daughter: "female" };
  const spouses = new Map<string, Set<string>>();
  const parents = new Map<string, { father?: string; mother?: string }>();
  for (const r of a.relations) {
    if (!REL_TYPES.includes(r.type)) out.push(`Loại quan hệ lạ: ${r.type}`);
    for (const n of [r.from, r.to]) if (!genders.has(n)) out.push(`Quan hệ nhắc "${n}" không có trong danh sách người`);
    if (r.from === r.to) out.push(`Quan hệ tự trỏ: ${r.from}`);
    const g = need[r.type];
    if (g && genders.has(r.from) && !genders.get(r.from)!.has(g)) out.push(`${r.type}: "${r.from}" phải là ${g === "male" ? "nam" : "nữ"}`);
    if (r.type === "spouse") {
      for (const [x, y] of [[r.from, r.to], [r.to, r.from]]) {
        if (!spouses.has(x)) spouses.set(x, new Set());
        spouses.get(x)!.add(y);
      }
    }
    if (r.type === "father" || r.type === "mother") parents.set(r.to, { ...parents.get(r.to), [r.type]: r.from });
  }
  const rel = new Set(a.relations.map((r) => `${r.from}|${r.to}|${r.type}`));
  for (const [child, p] of parents) {
    if (p.father && !p.mother && spouses.get(p.father)?.size === 1) {
      out.push(`"${p.father}" là cha của "${child}" và chỉ có một vợ "${[...spouses.get(p.father)!][0]}" — thiếu quan hệ mẹ`);
    }
    const gs = genders.get(child);
    const inv = gs?.has("male") ? "son" : gs?.has("female") ? "daughter" : null;
    for (const par of [p.father, p.mother]) {
      if (par && inv && !rel.has(`${child}|${par}|${inv}`)) out.push(`Thiếu quan hệ ngược ${child} → ${par} (${inv})`);
    }
  }
  return [...new Set(out)];
}

/** Nhãn đang dùng: bản đã sửa khi soát, nếu không thì nhãn gốc. */
export const currentAnswer = (s: LlmSample): LlmAnswer | null => s.review?.answer ?? s.answer;

export interface SampleFilter {
  q?: string;
  st?: string;
  rel?: string;
  warn?: string;
}

export function filterSamples(samples: LlmSample[], f: SampleFilter): LlmSample[] {
  const q = (f.q ?? "").trim().toLowerCase();
  return samples.filter((s) => {
    const a = currentAnswer(s);
    if (q && !s.input.toLowerCase().includes(q) && !a?.persons.some((p) => p.name.toLowerCase().includes(q))) return false;
    if (f.st && (s.review?.status ?? "chua") !== f.st) return false;
    if (f.rel === "1" && !a?.relations.length) return false;
    if (f.rel === "0" && a?.relations.length) return false;
    if (f.warn === "1" && !checkAnswer(a, s.input).length) return false;
    return true;
  });
}

/** Thêm son/daughter ngược từ father/mother khi biết giới tính của con. */
export function addInverse(a: LlmAnswer): LlmAnswer {
  const g = new Map(a.persons.map((p) => [p.name, p.gender]));
  const have = new Set(a.relations.map((r) => `${r.from}|${r.to}|${r.type}`));
  const extra = a.relations
    .filter((r) => r.type === "father" || r.type === "mother")
    .flatMap((r) => {
      const cg = g.get(r.to);
      if (!cg) return [];
      const t: RelType = cg === "male" ? "son" : "daughter";
      const k = `${r.to}|${r.from}|${t}`;
      if (have.has(k)) return [];
      have.add(k);
      return [{ from: r.to, to: r.from, type: t }];
    });
  return { ...a, relations: [...a.relations, ...extra] };
}

/** Đổi tên một người, kéo theo mọi quan hệ nhắc tên cũ. */
export function renamePerson(a: LlmAnswer, i: number, name: string): LlmAnswer {
  const old = a.persons[i].name;
  return {
    persons: a.persons.map((p, k) => (k === i ? { ...p, name } : p)),
    relations: a.relations.map((r) => ({ ...r, from: r.from === old ? name : r.from, to: r.to === old ? name : r.to })),
  };
}

/** Xoá một người và các quan hệ của người đó. */
export function removePerson(a: LlmAnswer, i: number): LlmAnswer {
  const n = a.persons[i].name;
  return { persons: a.persons.filter((_, k) => k !== i), relations: a.relations.filter((r) => r.from !== n && r.to !== n) };
}

/** Suy đời cho người thiếu đời từ quan hệ (để vẽ cây); vẫn không suy được thì không có trong map. */
export function inferGenerations(a: LlmAnswer): Map<string, number> {
  const gen = new Map<string, number>();
  for (const p of a.persons) if (p.generation != null) gen.set(p.name, p.generation);
  for (let it = 0; it < 6; it++) {
    for (const r of a.relations) {
      const x = gen.get(r.from);
      const y = gen.get(r.to);
      const d = r.type === "spouse" ? 0 : r.type === "father" || r.type === "mother" ? 1 : -1;
      if (x != null && y == null) gen.set(r.to, x + d);
      if (y != null && x == null) gen.set(r.from, y - d);
    }
  }
  return gen;
}
