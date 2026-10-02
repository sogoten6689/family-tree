import { describe, expect, it } from "vitest";

import type { GiaPhaItem } from "./giaPhaApi";
import { EMPTY_FILTERS, filterGiaPha, normalizeForSearch } from "./giaPhaSearch";

const item = (over: Partial<GiaPhaItem>): GiaPhaItem => ({
  id: "x",
  ma_dinh_danh_pending: true,
  title: "",
  status: "pending",
  updated_at: "2026-10-02",
  ...over,
});

const ITEMS = [
  item({ id: "F-B-PN-GiaThien-001-1930", ma_dinh_danh_pending: false, ma_dinh_danh_nguon: "catalogue", title: "Phan gia công phả (Gia Thiện – Hà Tĩnh)", ho_toc: "Phan", status: "built" }),
  item({ id: "F-B-DO-DongTru-007-1845", ma_dinh_danh_pending: false, ma_dinh_danh_nguon: "catalogue", title: "Đoàn tộc phả", ho_toc: "Đoàn" }),
  item({ id: "F-B-NG-XaA-009-1890", ma_dinh_danh_pending: false, ma_dinh_danh_nguon: "gemini", title: "Nguyễn tộc phả", ho_toc: "Nguyễn" }),
  item({ id: "hxh-129", title: "Yên Lãng thượng thư công gia phả 安朗尚書公家譜", ho_toc: "Nguyễn" }),
];

const ids = (filters = {}) => filterGiaPha(ITEMS, { ...EMPTY_FILTERS, ...filters }).map((i) => i.id);

describe("normalizeForSearch", () => {
  it("strips Vietnamese diacritics and maps đ", () => {
    expect(normalizeForSearch("  Đoàn Tộc PHẢ ")).toBe("doan toc pha");
  });
  it("keeps Han characters", () => {
    expect(normalizeForSearch("家譜")).toBe("家譜");
  });
});

describe("filterGiaPha", () => {
  it("returns everything with empty filters", () => {
    expect(ids()).toHaveLength(4);
  });
  it("matches title without diacritics", () => {
    expect(ids({ q: "phan gia" })).toEqual(["F-B-PN-GiaThien-001-1930"]);
  });
  it("matches identifier and surname", () => {
    expect(ids({ q: "dongtru" })).toEqual(["F-B-DO-DongTru-007-1845"]);
    expect(ids({ q: "doan" })).toEqual(["F-B-DO-DongTru-007-1845"]);
  });
  it("requires every term to match", () => {
    expect(ids({ q: "nguyen toc" })).toEqual(["F-B-NG-XaA-009-1890"]);
  });
  it("matches Han text", () => {
    expect(ids({ q: "家譜" })).toEqual(["hxh-129"]);
  });
  it("filters by status, code and source", () => {
    expect(ids({ status: "built" })).toEqual(["F-B-PN-GiaThien-001-1930"]);
    expect(ids({ code: "none" })).toEqual(["hxh-129"]);
    expect(ids({ code: "has", source: "gemini" })).toEqual(["F-B-NG-XaA-009-1890"]);
  });
});
