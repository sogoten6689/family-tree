import crypto from "node:crypto";
import fs from "node:fs";
import path from "node:path";
import { Answer, DatasetInfo, Review, Sample } from "./types";

/**
 * Nguồn dữ liệu:
 * - DATA_DIRS (biến môi trường, ngăn bằng ":") nếu có;
 * - mặc định: ../data_train và <repo dữ liệu>/03_derived/llm_sft (quét 2 cấp).
 * Mọi file *.jsonl có dạng {"text": "### Instruction ... ### Response ..."} đều tự hiện.
 * Nhãn soát lưu ở <file>.reviews.json cạnh file gốc; file gốc không bị sửa.
 */
const PROJECT = path.resolve(process.cwd(), "..");

function findDataRepo(): string | null {
  if (process.env.DATA_REPO) return process.env.DATA_REPO;
  let p = PROJECT;
  for (;;) {
    if (fs.existsSync(path.join(p, "data", "03_derived", "gia_pha"))) return path.join(p, "data");
    const up = path.dirname(p);
    if (up === p) return null;
    p = up;
  }
}

export const DATA_REPO = findDataRepo();

function roots(): string[] {
  if (process.env.DATA_DIRS) return process.env.DATA_DIRS.split(":").filter(Boolean);
  const r = [path.join(PROJECT, "data_train")];
  if (DATA_REPO) r.push(path.join(DATA_REPO, "03_derived", "llm_sft"));
  return r;
}

function walk(dir: string, depth: number, acc: string[]) {
  let ents: fs.Dirent[];
  try {
    ents = fs.readdirSync(dir, { withFileTypes: true });
  } catch {
    return;
  }
  for (const e of ents) {
    const p = path.join(dir, e.name);
    if (e.isDirectory() && depth > 0 && !e.name.startsWith(".") && e.name !== "node_modules") walk(p, depth - 1, acc);
    else if (e.isFile() && e.name.endsWith(".jsonl") && !e.name.endsWith(".reviewed.jsonl")) acc.push(p);
  }
}

function firstLineIsAlpaca(p: string): boolean {
  try {
    const fd = fs.openSync(p, "r");
    const buf = Buffer.alloc(4096);
    const n = fs.readSync(fd, buf, 0, 4096, 0);
    fs.closeSync(fd);
    const head = buf.subarray(0, n).toString("utf8");
    return head.startsWith('{"text"') && head.includes("### Instruction");
  } catch {
    return false;
  }
}

export const idOf = (p: string) => crypto.createHash("sha1").update(p).digest("hex").slice(0, 10);

export function listDatasets(): DatasetInfo[] {
  const out: DatasetInfo[] = [];
  for (const root of roots()) {
    const files: string[] = [];
    walk(root, 2, files);
    for (const f of files.sort()) {
      if (!firstLineIsAlpaca(f)) continue;
      const st = fs.statSync(f);
      const rel = path.relative(root, f);
      out.push({
        id: idOf(f),
        path: f,
        label: rel,
        group: root.includes("llm_sft") ? "VGP (văn xuôi thật)" : "Tổng hợp",
        mtimeMs: st.mtimeMs,
        size: st.size,
      });
    }
  }
  return out;
}

export function getDataset(id: string): DatasetInfo | undefined {
  return listDatasets().find((d) => d.id === id);
}

const M_INSTR = "### Instruction:\n";
const M_INPUT = "### Input:\n";
const M_RESP = "### Response:\n";

function parseRecord(line: string, idx: number): Sample {
  let rec: { text?: string; meta?: Record<string, unknown> };
  try {
    rec = JSON.parse(line);
  } catch (e) {
    return { idx, key: `line-${idx}`, input: line.slice(0, 400), instruction: "", answer: null, parseError: `JSON lỗi: ${e}` };
  }
  const t = rec.text ?? "";
  const i1 = t.indexOf(M_INPUT);
  const i2 = t.indexOf(M_RESP);
  const input = i1 >= 0 && i2 > i1 ? t.slice(i1 + M_INPUT.length, i2).trim() : t;
  const instruction = i1 >= 0 ? t.slice(M_INSTR.length, i1).trim() : "";
  const key = crypto.createHash("sha1").update(input).digest("hex").slice(0, 16);
  let answer: Answer | null = null;
  let parseError: string | undefined;
  try {
    answer = JSON.parse(t.slice(i2 + M_RESP.length));
  } catch (e) {
    parseError = `Response lỗi: ${e}`;
  }
  return { idx, key, input, instruction, answer, parseError, meta: rec.meta };
}

const cache = new Map<string, { mtimeMs: number; samples: Sample[] }>();

export function loadSamples(ds: DatasetInfo): Sample[] {
  const c = cache.get(ds.path);
  if (c && c.mtimeMs === ds.mtimeMs) return c.samples;
  const lines = fs.readFileSync(ds.path, "utf8").split("\n");
  const samples = lines.filter((l) => l.trim()).map((l, i) => parseRecord(l, i));
  cache.set(ds.path, { mtimeMs: ds.mtimeMs, samples });
  return samples;
}

export const reviewPath = (ds: DatasetInfo) => ds.path.replace(/\.jsonl$/, ".reviews.json");

export function loadReviews(ds: DatasetInfo): Record<string, Review> {
  try {
    return JSON.parse(fs.readFileSync(reviewPath(ds), "utf8")).items ?? {};
  } catch {
    return {};
  }
}

export function saveReview(ds: DatasetInfo, key: string, review: Review | null) {
  const items = loadReviews(ds);
  if (review) items[key] = review;
  else delete items[key];
  const file = reviewPath(ds);
  const tmp = file + ".tmp";
  fs.writeFileSync(tmp, JSON.stringify({ version: 1, dataset: path.basename(ds.path), items }, null, 1), "utf8");
  fs.renameSync(tmp, file);
}

/** Dấu vân tay để client biết có gì đổi (file mới, file sửa, soát mới). */
export function versionStamp(): string {
  const parts = listDatasets().map((d) => {
    let r = 0;
    try {
      r = fs.statSync(reviewPath(d)).mtimeMs;
    } catch {}
    return `${d.id}:${d.mtimeMs}:${d.size}:${r}`;
  });
  return crypto.createHash("sha1").update(parts.join("|")).digest("hex").slice(0, 12);
}

/** Dòng trong pha_he.txt (sơ đồ gốc) có chứa một trong các tên. */
export function phaHeLines(treeId: number, names: string[]): { lines: string[]; total: number } | null {
  if (!DATA_REPO) return null;
  const f = path.join(DATA_REPO, "03_derived", "gia_pha", String(treeId), "pha_he.txt");
  if (!fs.existsSync(f)) return null;
  const all = fs.readFileSync(f, "utf8").normalize("NFC").split("\n").filter(Boolean);
  const low = names.map((n) => n.toLowerCase());
  return { lines: all.filter((l) => low.some((n) => l.toLowerCase().includes(n))), total: all.length };
}

export function exportReviewed(ds: DatasetInfo): { path: string; count: number; edited: number } {
  const reviews = loadReviews(ds);
  const lines = fs.readFileSync(ds.path, "utf8").split("\n").filter((l) => l.trim());
  let edited = 0;
  const out = lines.map((l, i) => {
    const s = parseRecord(l, i);
    const rv = reviews[s.key];
    const rec = JSON.parse(l);
    if (rv?.answer) {
      const t: string = rec.text;
      rec.text = t.slice(0, t.indexOf(M_RESP) + M_RESP.length) + JSON.stringify(rv.answer);
      edited++;
    }
    rec.meta = { ...(rec.meta ?? {}), review_status: rv?.status ?? "chua", review_note: rv?.note || undefined };
    return JSON.stringify(rec);
  });
  const p = ds.path.replace(/\.jsonl$/, ".reviewed.jsonl");
  fs.writeFileSync(p, out.join("\n") + "\n", "utf8");
  return { path: p, count: out.length, edited };
}
