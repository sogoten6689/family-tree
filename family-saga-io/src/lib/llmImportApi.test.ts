import { describe, expect, it } from "vitest";

import { engineRunStatus, parseImportFile, type ScanVersion } from "./llmImportApi";

const r = { page: 1, cn: "乾坤", sv: "Càn khôn", vi: "Trời đất" };

describe("parseImportFile", () => {
  it("reads a JSON object with metadata", () => {
    const parsed = parseImportFile(JSON.stringify({ source: "gemini-web", model_note: "v1", records: [r] }));
    expect(parsed).toEqual({ records: [r], source: "gemini-web", model_note: "v1" });
  });

  it("reads a bare JSON array", () => {
    expect(parseImportFile(JSON.stringify([r, r])).records).toHaveLength(2);
  });

  it("reads JSONL with an optional header line", () => {
    const text = [JSON.stringify({ source: "chatgpt-web" }), JSON.stringify(r), "", JSON.stringify(r)].join("\n");
    const parsed = parseImportFile(text);
    expect(parsed.source).toBe("chatgpt-web");
    expect(parsed.records).toHaveLength(2);
  });

  it("reads a single-record JSONL file", () => {
    expect(parseImportFile(JSON.stringify(r)).records).toEqual([r]);
  });

  it("reports the bad JSONL line number", () => {
    expect(() => parseImportFile(`${JSON.stringify(r)}\n{oops`)).toThrow("Dòng 2");
  });

  it("rejects empty files", () => {
    expect(() => parseImportFile("  \n")).toThrow("File rỗng");
  });
});

const v = (source: string | null, statuses: string[]): ScanVersion => ({
  version_id: 1,
  version_number: 1,
  is_current: false,
  status: "draft",
  parent_version_id: null,
  source,
  review_status: null,
  note: null,
  created_at: null,
  steps: [
    { step_type: "ocr", status: "done" },
    { step_type: "transliteration", status: statuses[0] },
    { step_type: "translation", status: statuses[1] },
  ],
});

describe("engineRunStatus", () => {
  it("is null for non-engine versions", () => {
    expect(engineRunStatus(v(null, ["done", "done"]))).toBeNull();
    expect(engineRunStatus(v("chatgpt-web", ["imported", "imported"]))).toBeNull();
  });
  it.each([
    [["pending", "pending"], "pending"],
    [["running", "running"], "running"],
    [["done", "done"], "done"],
    [["error", "error"], "error"],
  ])("%j -> %s", (statuses, expected) => {
    expect(engineRunStatus(v("engine-gemini-web", statuses as string[]))).toBe(expected);
  });
});
