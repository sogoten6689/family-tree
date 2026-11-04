import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { fireEvent, render, screen } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import { afterEach, describe, expect, it, vi } from "vitest";

import { markChangedChars, sampleLines, summarize, toCsv } from "./doiChieuGrading";
import { alignToAnchors, draftChars } from "./lopPhu";
import { countSubmittable, mergeWithNext, splitRow, stripKeys, withKeys } from "./soatRows";

const auth = vi.hoisted(() => ({ isAdmin: false }));
vi.mock("@/contexts/AuthContext", () => ({ useAuth: () => auth }));

if (typeof globalThis.ResizeObserver === "undefined") {
  globalThis.ResizeObserver = class {
    observe() {}
    unobserve() {}
    disconnect() {}
  } as unknown as typeof ResizeObserver;
}

const { default: DoiChieuPage } = await import("./DoiChieuPage");

describe("chấm mẫu", () => {
  const lines = Array.from({ length: 1000 }, (_, i) => i + 1);

  it("lấy 5% (tối thiểu 20), cố định theo khoá, không trùng", () => {
    const a = sampleLines(lines, "sv/nom-1");
    expect(a).toHaveLength(50);
    expect(new Set(a).size).toBe(50);
    expect(sampleLines(lines, "sv/nom-1")).toEqual(a);
    expect(sampleLines(lines, "sv/nom-2")).not.toEqual(a);
    expect(sampleLines(lines.slice(0, 100), "k")).toHaveLength(20);
    expect(sampleLines(lines.slice(0, 7), "k")).toHaveLength(7);
  });

  it("tỷ lệ lỗi = cặp lỗi / cặp đã chấm", () => {
    const s = summarize({ 1: "dung", 2: "OMISSION", 3: "ADDITION", 4: "dung" });
    expect(s).toMatchObject({ checked: 4, errors: 2, rate: 0.5, byType: { OMISSION: 1, ADDITION: 1, MISSING: 0 } });
    expect(summarize({}).rate).toBeNull();
  });

  it("CSV có BOM và bao ô có dấu phẩy", () => {
    const csv = toCsv([{ line: 1, han: "公回", viet: "Ông về, lánh đi", verdict: "dung" }]);
    expect(csv.startsWith("﻿dong,han,viet,nhan\n")).toBe(true);
    expect(csv).toContain('"Ông về, lánh đi"');
  });

  it("tô chữ Hán không có trong OCR, bỏ qua dấu câu", () => {
    const marks = markChangedChars("改姓名，", "改性名");
    expect(marks.filter((m) => m.changed).map((m) => m.ch)).toEqual(["姓"]);
  });
});

describe("trang đối chiếu", () => {
  afterEach(() => vi.unstubAllGlobals());

  const renderPage = (url = "/nghien-cuu/doi-chieu") =>
    render(
      <QueryClientProvider client={new QueryClient({ defaultOptions: { queries: { retry: false } } })}>
        <MemoryRouter initialEntries={[url]}>
          <DoiChieuPage />
        </MemoryRouter>
      </QueryClientProvider>,
    );

  it("hiện tiến độ từng sinh viên không cần đăng nhập", async () => {
    const fetchMock = vi.fn().mockResolvedValue(
      new Response(
        JSON.stringify({
          target: 2000,
          error_threshold: 0.3,
          students: [
            {
              id: "sv-a",
              ten: "Sinh viên A",
              books: [
                {
                  id: "nom-1",
                  ten: "Đoàn tộc phả",
                  link: "https://drive.google.com/file/d/x/view",
                  tsv: "nom-1_parallel.tsv",
                  pairs: 10,
                  valid: 9,
                  format_errors: 1,
                  machine_rows: 20,
                  machine_pages: 2,
                  ocr_coverage: 0.5,
                  image_pages: 2,
                },
              ],
              valid: 1500,
              pairs: 1600,
              format_errors: 3,
              submitted: 2,
            },
          ],
        }),
        { status: 200 },
      ),
    );
    vi.stubGlobal("fetch", fetchMock);
    renderPage();
    expect(await screen.findByText("Sinh viên A")).toBeTruthy();
    expect(screen.getByText("1.500")).toBeTruthy();
    const headers = new Headers(fetchMock.mock.calls[0][1].headers);
    expect(headers.has("Authorization")).toBe(false);
    fireEvent.click(screen.getByRole("button", { name: /expand row/i }));
    expect(await screen.findByText("Đoàn tộc phả")).toBeTruthy();
    expect(screen.getByRole("link", { name: /Bản gốc/ }).getAttribute("href")).toBe("https://drive.google.com/file/d/x/view");
  });

  it("cuốn chưa có bản máy thì xem lần lượt ảnh trang", async () => {
    const detail = {
      student: "sv-a",
      book: "hxh-1",
      ten: "Ngô gia thế phả",
      link: null,
      tsv: null,
      pairs: [],
      missing: [],
      pages: ["001", "002"],
      stats: { pairs: 0, valid: 0, format_errors: 0, machine_rows: 0, machine_pages: 0, ocr_coverage: null },
    };
    vi.stubGlobal("fetch", vi.fn().mockResolvedValue(new Response(JSON.stringify(detail), { status: 200 })));
    renderPage("/nghien-cuu/doi-chieu?sv=sv-a&cuon=hxh-1");
    expect(await screen.findByText("Trang 001")).toBeTruthy();
    expect(screen.getByRole("img", { name: "Trang 001" }).getAttribute("src")).toContain("/sv-a/hxh-1/anh/001");
    fireEvent.click(screen.getByTitle("Next Page"));
    expect(await screen.findByText("Trang 002")).toBeTruthy();
  });

  it("báo khi máy chủ chưa có dữ liệu", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn().mockResolvedValue(new Response(JSON.stringify({ target: 2000, error_threshold: 0.3, students: [] }), { status: 200 })),
    );
    renderPage();
    expect(await screen.findByText("Chưa có bài nộp nào")).toBeTruthy();
  });
});

describe("thao tác dòng soát", () => {
  const rows = () =>
    withKeys([
      { trang: "001", han: "公回改", viet: "Ông về đổi", bo: false },
      { trang: "002", han: "姓名", viet: "họ tên", bo: false },
    ]);

  it("ghép với dòng kế tiếp, kể cả sang trang sau, giữ trang đầu", () => {
    const r = rows();
    expect(stripKeys(mergeWithNext(r, r[0].key))).toEqual([{ trang: "001", han: "公回改姓名", viet: "Ông về đổi họ tên", bo: false }]);
    expect(mergeWithNext(r, r[1].key)).toBe(r);
  });

  it("tách tại con trỏ của từng ô", () => {
    const r = rows();
    const out = stripKeys(splitRow(r, r[0].key, 2, 6));
    expect(out[0]).toMatchObject({ han: "公回", viet: "Ông về" });
    expect(out[1]).toMatchObject({ trang: "001", han: "改", viet: "đổi" });
    expect(out).toHaveLength(3);
  });

  it("chỉ đếm dòng thuộc trang đã xác nhận, không bị bỏ, không rỗng", () => {
    const list = [
      { trang: "001", han: "公", viet: "Ông", bo: false },
      { trang: "001", han: "R.42", viet: "", bo: true },
      { trang: "001", han: " ", viet: "", bo: false },
      { trang: "002", han: "改", viet: "Đổi", bo: false },
    ];
    expect(countSubmittable(list, ["001"])).toBe(1);
    expect(countSubmittable(list, [])).toBe(0);
  });
});

describe("đặt chữ lên lớp phủ", () => {
  const draft = (text: string, trang = "001", rowKey = 1) => Array.from(text).map((ch) => ({ ch, rowKey, trang }));
  const shown = (r: ReturnType<typeof alignToAnchors>) => r.map((p) => p?.ch ?? "_").join("");

  it("chữ sửa nằm đúng vị trí và được đánh dấu", () => {
    const out = alignToAnchors(Array.from("三條嶺憲之七中"), draft("三條嶺卷之七中"), "001");
    expect(shown(out)).toBe("三條嶺卷之七中");
    expect(out.map((p) => p!.changed)).toEqual([false, false, false, true, false, false, false]);
  });

  it("bỏ dấu câu do người soát thêm", () => {
    const chars = draftChars([{ key: 1, trang: "001", han: "公回，改姓。", viet: "", bo: false }]);
    expect(chars.map((c) => c.ch).join("")).toBe("公回改姓");
    expect(draftChars([{ key: 2, trang: "001", han: "R.42 漢", viet: "", bo: true }])).toEqual([]);
  });

  it("dòng đã xoá chữ thì vị trí đó để trống", () => {
    expect(shown(alignToAnchors(Array.from("公回改姓"), draft("公姓"), "001"))).toBe("公__姓");
  });

  it("câu ghép qua trang: lấy đúng phần có trên ảnh, không kéo chữ trang kề vào", () => {
    const rows = [...draft("前頁文字", "001"), ...draft("公回改姓", "001"), ...draft("後頁文字", "003")];
    expect(shown(alignToAnchors(Array.from("公回改姓"), rows, "002"))).toBe("公回改姓");
    expect(shown(alignToAnchors(Array.from("甲回改丙"), [...draft("前頁", "001"), ...draft("回改", "002"), ...draft("後頁", "003")], "002"))).toBe("_回改_");
  });
});

describe("thẻ Soát", () => {
  afterEach(() => {
    vi.unstubAllGlobals();
    auth.isAdmin = false;
  });

  const book = {
    student: "sv-a",
    book: "nom-1",
    ten: "Cuốn một",
    link: null,
    tsv: null,
    pairs: [],
    missing: [],
    pages: ["001"],
    stats: { pairs: 0, valid: 0, format_errors: 0, machine_rows: 1, machine_pages: 1, ocr_coverage: 0 },
  };
  const json = (body: unknown) => new Response(JSON.stringify(body), { status: 200, headers: { "Content-Type": "application/json" } });

  const open = () => {
    const calls: { method: string; url: string; body?: string }[] = [];
    vi.stubGlobal(
      "fetch",
      vi.fn(async (url: string, init?: RequestInit) => {
        const method = init?.method ?? "GET";
        calls.push({ method, url, body: init?.body as string | undefined });
        if (url.includes("/soat/khung/")) return json({ rong: 100, cao: 100, chu: [{ c: "公", b: [10, 10, 30, 30] }, { c: "回", b: [10, 30, 30, 50] }], thieu: 3 });
        if (url.endsWith("/soat/nop")) return json({ nop: true, so_cap: 1, loi: [], ly_do: null, tsv: "nom-1_parallel.tsv" });
        if (url.endsWith("/soat") && method === "PUT") return json({ ...JSON.parse(init?.body as string), phien_ban: 1 });
        if (url.endsWith("/soat")) return json({ rows: [{ trang: "001", han: "公回", viet: "Ông về", bo: false }], da_soat: [], phien_ban: 0 });
        return json(book);
      }),
    );
    render(
      <QueryClientProvider client={new QueryClient({ defaultOptions: { queries: { retry: false } } })}>
        <MemoryRouter initialEntries={["/nghien-cuu/doi-chieu?sv=sv-a&cuon=nom-1"]}>
          <DoiChieuPage />
        </MemoryRouter>
      </QueryClientProvider>,
    );
    return calls;
  };

  it("không hiện với người chưa phải admin", async () => {
    open();
    await screen.findByRole("tab", { name: /Ảnh trang/ });
    expect(screen.queryByRole("tab", { name: "Soát" })).toBeNull();
  });

  it("lớp phủ hiện chữ đang sửa, có đường chia, và xem song song", async () => {
    auth.isAdmin = true;
    open();
    fireEvent.click(await screen.findByRole("tab", { name: "Soát" }));
    const han = await screen.findByLabelText("Hán dòng 1");
    fireEvent.click(screen.getByText("Kéo so sánh"));
    expect(await screen.findByTestId("duong-chia")).toBeTruthy();
    const svg = await screen.findByRole("img", { name: "Chữ phục dựng trang 001" });
    expect(svg.textContent).toBe("公回");
    fireEvent.change(han, { target: { value: "公歸" } });
    expect(svg.textContent).toBe("公歸");
    expect(screen.getByText(/Còn 3 chữ chưa định vị được/)).toBeTruthy();
    fireEvent.click(screen.getByText("Xem song song"));
    expect(screen.queryByTestId("duong-chia")).toBeNull();
    expect(screen.getByRole("img", { name: "Chữ phục dựng trang 001" })).toBeTruthy();
  }, 20000);

  it("admin xác nhận trang, lưu nháp rồi mới nộp", async () => {
    auth.isAdmin = true;
    const calls = open();
    fireEvent.click(await screen.findByRole("tab", { name: "Soát" }));
    const han = await screen.findByLabelText("Hán dòng 1");
    expect(screen.getByRole("button", { name: /Nộp 0 cặp/ }).hasAttribute("disabled")).toBe(true);

    fireEvent.change(han, { target: { value: "公回。" } });
    fireEvent.click(screen.getByRole("checkbox", { name: /đã soát xong trang này/ }));
    fireEvent.click(screen.getByRole("button", { name: /Nộp 1 cặp/ }));
    fireEvent.click(await screen.findByRole("button", { name: "Nộp" }));

    await screen.findByText("Đã nộp 1 cặp vào nom-1_parallel.tsv.");
    const writes = calls.filter((c) => c.method !== "GET");
    expect(writes.map((c) => c.method)).toEqual(["PUT", "POST"]);
    expect(JSON.parse(writes[0].body!)).toMatchObject({ da_soat: ["001"], phien_ban: 0, rows: [{ han: "公回。" }] });
  }, 20000); // nhiều thành phần antd trong jsdom: ~2 giây khi chạy riêng, vượt 5 giây khi cả bộ test chạy song song
});
