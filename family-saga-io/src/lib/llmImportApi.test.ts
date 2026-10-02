import { describe, expect, it } from "vitest";

import { parseImportFile } from "./llmImportApi";

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
