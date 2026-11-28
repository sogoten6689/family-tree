import { describe, expect, it } from "vitest";

import type { LlmAnswer, LlmSample } from "@/lib/llmSoatApi";

import { addInverse, checkAnswer, filterSamples, inferGenerations, removePerson, renamePerson } from "./check";

const P = (name: string, gender: "male" | "female" | null = "male", generation: number | null = 1) => ({
  name,
  birth: null,
  death: null,
  generation,
  gender,
});
const TEXT = "Ông Lê Văn An lấy bà Trần Thị Bình, sinh con trai Lê Văn Cường.";
const FAMILY: LlmAnswer = {
  persons: [P("Lê Văn An"), P("Trần Thị Bình", "female"), P("Lê Văn Cường", "male", null)],
  relations: [
    { from: "Lê Văn An", to: "Trần Thị Bình", type: "spouse" },
    { from: "Lê Văn An", to: "Lê Văn Cường", type: "father" },
  ],
};

describe("checkAnswer", () => {
  it("báo thiếu mẹ khi cha chỉ có một vợ, và thiếu quan hệ ngược", () => {
    const w = checkAnswer(FAMILY, TEXT);
    expect(w.some((x) => x.includes("thiếu quan hệ mẹ"))).toBe(true);
    expect(w.some((x) => x.includes("Thiếu quan hệ ngược Lê Văn Cường → Lê Văn An (son)"))).toBe(true);
  });

  it("báo tên không có trong văn bản, tên cụt và giới tính sai vai", () => {
    const a: LlmAnswer = {
      persons: [P("Nguyễn Văn Dậu"), P("Bình", "female")],
      relations: [{ from: "Bình", to: "Nguyễn Văn Dậu", type: "father" }],
    };
    const w = checkAnswer(a, TEXT);
    expect(w).toContain('"Nguyễn Văn Dậu" không có nguyên văn trong văn bản');
    expect(w).toContain('Tên chưa đủ họ tên: "Bình"');
    expect(w).toContain('father: "Bình" phải là nam');
  });

  it("nhãn đủ thì không cảnh báo", () => {
    const full = addInverse({
      ...FAMILY,
      relations: [...FAMILY.relations, { from: "Trần Thị Bình", to: "Lê Văn Cường", type: "mother" }],
    });
    expect(checkAnswer(full, TEXT)).toEqual([]);
  });
});

describe("sửa nhãn", () => {
  it("đổi tên kéo theo quan hệ; xoá người xoá luôn quan hệ", () => {
    const r = renamePerson(FAMILY, 0, "Lê Văn Ân");
    expect(r.relations.every((x) => x.from !== "Lê Văn An")).toBe(true);
    expect(removePerson(FAMILY, 0).relations).toEqual([]);
  });

  it("thêm quan hệ ngược không trùng", () => {
    const once = addInverse(FAMILY);
    expect(once.relations).toContainEqual({ from: "Lê Văn Cường", to: "Lê Văn An", type: "son" });
    expect(addInverse(once).relations.length).toBe(once.relations.length);
  });

  it("suy đời từ quan hệ", () => {
    expect(inferGenerations(FAMILY).get("Lê Văn Cường")).toBe(2);
  });
});

describe("filterSamples", () => {
  const s = (key: string, answer: LlmAnswer, status?: "da") =>
    ({ idx: 0, key, input: TEXT, answer, meta: null, error: null, review: status ? { status, note: null, answer: null, updated_at: "" } : null }) as LlmSample;
  const list = [s("a", FAMILY, "da"), s("b", { persons: [], relations: [] })];
  it("lọc theo trạng thái, quan hệ, chữ", () => {
    expect(filterSamples(list, { st: "da" }).map((x) => x.key)).toEqual(["a"]);
    expect(filterSamples(list, { st: "chua" }).map((x) => x.key)).toEqual(["b"]);
    expect(filterSamples(list, { rel: "0" }).map((x) => x.key)).toEqual(["b"]);
    expect(filterSamples(list, { q: "cường" }).map((x) => x.key)).toEqual(["a", "b"]);
    expect(filterSamples(list, { warn: "1" }).map((x) => x.key)).toEqual(["a"]);
  });
});
