import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { fireEvent, render, screen } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import { afterEach, describe, expect, it, vi } from "vitest";

import { markChangedChars, sampleLines, summarize, toCsv } from "./doiChieuGrading";
import { alignToAnchors, draftChars } from "./lopPhu";
import { boxColor, boxFrom, insertIndex, moveBox } from "./oChu";
import { countSubmittable, mergeWithNext, splitRow, stripKeys, suspectOf, toggleMark, withKeys, type EditRow } from "./soatRows";
import SoatOverlay from "./SoatOverlay";

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

describe("đánh dấu dòng", () => {
  const row = (over: Partial<EditRow>): EditRow => ({ key: 1, trang: "001", han: "公回", viet: "Ông về", bo: false, ...over });

  it("nhận ra dòng chưa dịch, lẫn chữ Hán, chưa chắc, chữ không đọc được", () => {
    expect(suspectOf(row({}))).toBeNull();
    expect(suspectOf(row({ viet: "  " }))?.reason).toBe("Chưa có bản dịch");
    expect(suspectOf(row({ viet: "lầu蜃" }))?.reason).toBe("Bản dịch lẫn chữ Hán");
    expect(suspectOf(row({ viet: "Ông về (không chắc)" }))?.reason).toBe("Bản dịch có chỗ chưa chắc");
    expect(suspectOf(row({ han: "公[?]" }))).toEqual({ kind: "ocr", reason: "Chữ Hán có chỗ không đọc được" });
    expect(suspectOf(row({ viet: "", bo: true }))).toBeNull();
    expect(suspectOf(row({ han: "", viet: "" }))).toBeNull();
  });

  it("bấm lại đúng loại thì tắt, mã giữ nguyên", () => {
    const on = toggleMark(row({}), "ocr");
    expect(on.danh_dau).toBe("ocr");
    expect(on.ma).toBeTruthy();
    expect(toggleMark(row({ danh_dau: "ocr", ma: "a1" }), "ocr").danh_dau).toBeUndefined();
    expect(toggleMark(row({ danh_dau: "ocr", ma: "a1" }), "chua_dich")).toEqual({ danh_dau: "chua_dich", ma: "a1" });
  });

  it("ghép giữ dấu của dòng sau; tách cho mỗi nửa một mã riêng", () => {
    const merged = mergeWithNext([row({ key: 1 }), row({ key: 2, danh_dau: "ocr", ma: "b2", ghi_chu: "mờ" })], 1);
    expect(merged[0]).toMatchObject({ danh_dau: "ocr", ma: "b2", ghi_chu: "mờ" });
    const split = splitRow([row({ danh_dau: "ocr", ma: "a1" })], 1, 1, 2);
    expect(split[0].ma).toBe("a1");
    expect(split[1].danh_dau).toBe("ocr");
    expect(split[1].ma).toBeTruthy();
    expect(split[1].ma).not.toBe("a1");
    expect(splitRow([row({})], 1, 1, 2)[1].ma).toBeUndefined();
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

describe("tính toán ô chữ", () => {
  const cells = [
    { b: [80, 10, 90, 20] },
    { b: [80, 30, 90, 40] },
    { b: [50, 10, 60, 20] },
    { b: [50, 30, 60, 40] },
  ] as { b: [number, number, number, number] }[];

  it("chèn ô mới đúng thứ tự đọc: cột phải sang trái, trên xuống dưới", () => {
    expect(insertIndex(cells, [80, 21, 90, 29])).toBe(1);
    expect(insertIndex(cells, [80, 50, 90, 60])).toBe(2);
    expect(insertIndex(cells, [50, 1, 60, 8])).toBe(2);
    expect(insertIndex(cells, [95, 10, 99, 20])).toBe(0);
    expect(insertIndex(cells, [65, 10, 75, 20])).toBe(2);
    expect(insertIndex(cells, [10, 10, 20, 20])).toBe(4);
    expect(insertIndex([], [10, 10, 20, 20])).toBe(0);
  });

  it("ô luôn nằm trong ảnh, toạ độ nguyên, không ngược và không rỗng", () => {
    expect(boxFrom([30.4, 40.6], [10.2, 20.1], 100, 100)).toEqual([10, 20, 30, 41]);
    expect(boxFrom([-5, -5], [200, 200], 100, 100)).toEqual([0, 0, 100, 100]);
    expect(boxFrom([100, 100], [100, 100], 100, 100)).toEqual([99, 99, 100, 100]);
    expect(boxFrom([5, 5], [5, 5], 100, 100)).toEqual([5, 5, 6, 6]);
  });

  it("dời ô giữ nguyên cỡ và dừng ở mép ảnh", () => {
    expect(moveBox([10, 10, 30, 20], 5, -3, 100, 100)).toEqual([15, 7, 35, 17]);
    expect(moveBox([10, 10, 30, 20], 500, -500, 100, 100)).toEqual([80, 0, 100, 10]);
  });

  it("ô người chỉnh có màu riêng", () => {
    expect(boxColor({ n: "sua" })).toBe(boxColor({ n: "them", u: 1 }));
    expect(boxColor({ n: "sua" })).not.toBe(boxColor({ u: 1 }));
    expect(boxColor({ u: 1 })).not.toBe(boxColor({}));
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

  const open = (banTam?: unknown, goiY?: unknown, han = "公回", viet = "Ông về", extra: object = {}, khungExtra: object = {}) => {
    const calls: { method: string; url: string; body?: string }[] = [];
    vi.stubGlobal(
      "fetch",
      vi.fn(async (url: string, init?: RequestInit) => {
        const method = init?.method ?? "GET";
        calls.push({ method, url, body: init?.body as string | undefined });
        if (url.includes("/soat/khung/")) {
          const machine = { rong: 100, cao: 100, chu: [{ c: "公", b: [10, 10, 30, 30] }, { c: "回", b: [10, 30, 30, 50] }], thieu: 3, ban_tam: banTam };
          if (method === "PUT") {
            const sent = JSON.parse(init?.body as string);
            return json({ ...machine, chu: sent.chu, da_sua: true, phien_ban: sent.phien_ban + 1 });
          }
          return json(method === "DELETE" ? machine : { ...machine, ...khungExtra });
        }
        if (url.endsWith("/soat/nop")) return json({ nop: true, so_cap: 1, loi: [], ly_do: null, tsv: "nom-1_parallel.tsv" });
        if (url.endsWith("/soat") && method === "PUT") return json({ ...JSON.parse(init?.body as string), phien_ban: 1 });
        if (url.endsWith("/soat")) return json({ rows: [{ trang: "001", han, viet, bo: false, ...extra }], da_soat: [], phien_ban: 0, goi_y: goiY ?? {} });
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

  describe("sửa ô chữ", () => {
    const mouse = (el: Element, type: string, x: number, y: number) =>
      fireEvent(el, new MouseEvent(type, { bubbles: true, clientX: x, clientY: y }));

    const openEditor = async (khungExtra: object = {}, banTam?: unknown) => {
      auth.isAdmin = true;
      const calls = open(banTam, undefined, "公回", "Ông về", {}, khungExtra);
      fireEvent.click(await screen.findByRole("tab", { name: "Soát" }));
      fireEvent.click(await screen.findByRole("button", { name: "Sửa ô chữ" }));
      const svg = await screen.findByTestId("vung-sua-o");
      svg.getBoundingClientRect = () => ({ left: 0, top: 0, width: 100, height: 100 }) as DOMRect;
      return { calls, svg };
    };
    const drag = (start: Element, svg: Element, from: [number, number], to: [number, number]) => {
      mouse(start, "pointerdown", ...from);
      mouse(svg, "pointermove", ...to);
      mouse(svg, "pointerup", ...to);
    };
    const saved = (calls: { method: string; url: string; body?: string }[]) => {
      const put = calls.filter((c) => c.method === "PUT" && c.url.includes("/soat/khung/001"));
      return JSON.parse(put[put.length - 1].body as string);
    };
    const saveBoxes = async () => {
      fireEvent.click(screen.getByRole("button", { name: "Lưu ô chữ" }));
      await screen.findByRole("button", { name: "Đã lưu ô chữ" });
    };

    it("vẽ ô mới, gõ chữ rồi lưu, ô được chèn đúng thứ tự đọc", async () => {
      const { calls, svg } = await openEditor();
      drag(svg, svg, [50, 10], [70, 30]);
      fireEvent.change(screen.getByLabelText("Chữ trong ô"), { target: { value: "歸" } });
      await saveBoxes();
      expect(saved(calls)).toEqual({
        chu: [{ c: "歸", b: [50, 10, 70, 30], n: "them" }, { c: "公", b: [10, 10, 30, 30] }, { c: "回", b: [10, 30, 30, 50] }],
        phien_ban: 0,
      });
    }, 20000);

    it("ô mới chưa có chữ thì không lưu; bấm nhầm ở chỗ trống không sinh ô", async () => {
      const { calls, svg } = await openEditor();
      drag(svg, svg, [60, 60], [61, 61]);
      expect(screen.getAllByTestId("o-sua")).toHaveLength(2);
      drag(svg, svg, [50, 10], [70, 30]);
      expect(screen.getAllByTestId("o-sua")).toHaveLength(3);
      fireEvent.click(screen.getByRole("button", { name: "Lưu ô chữ" }));
      expect(await screen.findByText(/Còn ô chưa có chữ/)).toBeTruthy();
      expect(calls.some((c) => c.method === "PUT")).toBe(false);
    }, 20000);

    it("kéo để dời, kéo góc để đổi cỡ, ô được đánh dấu người chỉnh và bỏ dấu ước lượng", async () => {
      const { calls, svg } = await openEditor({ chu: [{ c: "公", b: [10, 10, 30, 30], u: 1 }, { c: "回", b: [10, 30, 30, 50] }] });
      drag(screen.getAllByTestId("o-sua")[0], svg, [20, 20], [25, 15]);
      drag(screen.getAllByTestId("goc-o")[2], svg, [35, 25], [50, 60]);
      await saveBoxes();
      expect(saved(calls).chu[0]).toEqual({ c: "公", b: [15, 5, 50, 60], n: "sua" });
      expect(saved(calls).chu[1]).toEqual({ c: "回", b: [10, 30, 30, 50] });
    }, 20000);

    it("xoá bằng nút và phím Delete, hoàn tác lấy lại, phím Delete trong ô gõ chữ không xoá ô", async () => {
      const { svg } = await openEditor();
      const boxes = () => screen.getAllByTestId("o-sua");
      mouse(boxes()[0], "pointerdown", 20, 20);
      mouse(svg, "pointerup", 20, 20);
      fireEvent.keyDown(screen.getByLabelText("Chữ trong ô"), { key: "Delete" });
      expect(boxes()).toHaveLength(2);
      fireEvent.keyDown(window, { key: "Delete" });
      expect(boxes()).toHaveLength(1);
      fireEvent.click(screen.getByRole("button", { name: "Hoàn tác" }));
      expect(boxes()).toHaveLength(2);
      mouse(boxes()[1], "pointerdown", 20, 40);
      mouse(svg, "pointerup", 20, 40);
      fireEvent.click(screen.getByRole("button", { name: "Xoá ô" }));
      expect(boxes()).toHaveLength(1);
    }, 20000);

    it("khoá đổi trang khi đang sửa; thoát khi chưa lưu phải xác nhận", async () => {
      const { svg } = await openEditor();
      expect(screen.getByLabelText("Chọn trang").closest(".ant-select-disabled")).toBeTruthy();
      drag(svg, svg, [50, 10], [70, 30]);
      fireEvent.click(screen.getByRole("button", { name: "Thoát sửa ô" }));
      expect(screen.getByTestId("sua-o-chu")).toBeTruthy();
      fireEvent.click(await screen.findByRole("button", { name: "Bỏ thay đổi" }));
      expect(screen.queryByTestId("sua-o-chu")).toBeNull();
      expect(screen.getAllByTestId("o-chu")).toHaveLength(2);
    }, 20000);

    it("khôi phục ô máy gửi đúng phiên bản và hiện lại ô máy", async () => {
      const { calls } = await openEditor({ da_sua: true, phien_ban: 2, chu: [{ c: "公", b: [1, 1, 5, 5], n: "sua" }] });
      expect(screen.getAllByTestId("o-sua")).toHaveLength(1);
      fireEvent.click(screen.getByRole("button", { name: "Khôi phục ô máy" }));
      fireEvent.click(await screen.findByRole("button", { name: "Khôi phục" }));
      await vi.waitFor(() => expect(screen.getAllByTestId("o-sua")).toHaveLength(2));
      const del = calls.find((c) => c.method === "DELETE");
      expect(del?.url).toContain("/soat/khung/001?phien_ban=2");
      expect(screen.queryByRole("button", { name: "Khôi phục ô máy" })).toBeNull();
    }, 20000);

    it("ô vẽ trong khoảng cột bản tâm thuộc về bản tâm, không lẫn vào chữ chính", async () => {
      const banTam = { text: "鄂氏", chu: [{ c: "鄂", b: [50, 10, 60, 20] }, { c: "氏", b: [50, 40, 60, 50] }], thieu: 0 };
      const { calls, svg } = await openEditor({}, banTam);
      drag(svg, svg, [51, 25], [59, 35]);
      fireEvent.change(screen.getByLabelText("Chữ trong ô"), { target: { value: "宗" } });
      await saveBoxes();
      const body = saved(calls);
      expect(body.chu).toHaveLength(2);
      expect(body.ban_tam_chu.map((c: { c: string }) => c.c)).toEqual(["鄂", "宗", "氏"]);
    }, 20000);
  });

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
    await screen.findByRole("img", { name: "Chữ phục dựng trang 001" });
    const glyphs = () => screen.getAllByTestId("chu").map((t) => t.textContent).join("");
    expect(glyphs()).toBe("公回");
    fireEvent.change(han, { target: { value: "公歸" } });
    expect(glyphs()).toBe("公歸");
    expect(screen.getByText(/Còn 3 chữ chưa định vị được/)).toBeTruthy();
    fireEvent.click(screen.getByText("Xem song song"));
    expect(screen.queryByTestId("duong-chia")).toBeNull();
    expect(screen.getByRole("img", { name: "Chữ phục dựng trang 001" })).toBeTruthy();
  }, 20000);

  it("ảnh gốc có ô từng chữ và số dòng, tắt được", async () => {
    auth.isAdmin = true;
    open();
    fireEvent.click(await screen.findByRole("tab", { name: "Soát" }));
    await screen.findByLabelText("Hán dòng 1");
    expect(await screen.findAllByTestId("o-chu")).toHaveLength(2);
    expect(screen.getAllByTestId("so-dong").map((t) => t.textContent)).toEqual(["1"]);
    fireEvent.click(screen.getByRole("checkbox", { name: "Hiện ô chữ và số dòng" }));
    expect(screen.queryByTestId("o-chu")).toBeNull();
    expect(screen.queryByTestId("so-dong")).toBeNull();
  }, 20000);

  it("kéo bản dịch hiện dòng ngang có số, đổi theo ô Việt, bấm dòng tới ô đó", async () => {
    auth.isAdmin = true;
    open();
    fireEvent.click(await screen.findByRole("tab", { name: "Soát" }));
    const viet = await screen.findByLabelText("Việt dòng 1");
    fireEvent.click(screen.getByText("Kéo bản dịch"));
    expect(await screen.findByTestId("duong-chia")).toBeTruthy();
    const line = () => screen.getByTestId("dong-dich");
    expect(line().textContent).toBe("1Ông về");
    fireEvent.change(viet, { target: { value: "" } });
    expect(line().textContent).toBe("1(chưa có bản dịch)");
    fireEvent.click(line());
    expect(document.activeElement).toBe(viet);
  }, 20000);

  it("bản tâm có ô và chữ riêng, sửa được, lưu riêng, không có số dòng", async () => {
    auth.isAdmin = true;
    const calls = open({ text: "鄂氏", chu: [{ c: "鄂", b: [50, 10, 70, 30] }, { c: "氏", b: [50, 30, 70, 50], u: 1 }], thieu: 0 });
    fireEvent.click(await screen.findByRole("tab", { name: "Soát" }));
    const gutter = (await screen.findByLabelText("Bản tâm")) as HTMLTextAreaElement;
    expect(gutter.value).toBe("鄂氏");
    expect(await screen.findAllByTestId("o-chu")).toHaveLength(4);
    expect(screen.getAllByTestId("so-dong").map((t) => t.textContent)).toEqual(["1"]);
    fireEvent.click(screen.getByText("Xem song song"));
    const glyphs = () => screen.getAllByTestId("chu").map((t) => t.textContent).join("");
    expect(glyphs()).toBe("公回鄂氏");
    fireEvent.change(gutter, { target: { value: "鄂民" } });
    expect(glyphs()).toBe("公回鄂民");
    fireEvent.click(screen.getAllByTestId("chu")[3]);
    expect(document.activeElement).toBe(gutter);
    fireEvent.click(screen.getByRole("button", { name: "Lưu nháp" }));
    await screen.findByRole("button", { name: "Đã lưu" });
    const put = calls.find((c) => c.method === "PUT");
    expect(JSON.parse(put?.body ?? "{}").ban_tam).toEqual({ "001": "鄂民" });
    expect(JSON.parse(put?.body ?? "{}").rows).toHaveLength(1);
  }, 20000);

  it("phóng to, thu nhỏ, về 100%, ở mọi chế độ giữ nguyên mức đã chọn", async () => {
    auth.isAdmin = true;
    open();
    fireEvent.click(await screen.findByRole("tab", { name: "Soát" }));
    await screen.findByLabelText("Hán dòng 1");
    const width = () => screen.getAllByTestId("noi-dung-xem")[0].style.width;
    const zoomOut = await screen.findByRole("button", { name: "Thu nhỏ" });
    expect(width()).toBe("100%");
    expect((zoomOut as HTMLButtonElement).disabled).toBe(true);
    fireEvent.click(screen.getByRole("button", { name: "Phóng to" }));
    expect(width()).toBe("125%");
    fireEvent.click(screen.getByText("Xem song song"));
    expect(screen.getAllByTestId("noi-dung-xem").map((n) => n.style.width)).toEqual(["125%", "125%"]);
    fireEvent.click(screen.getByRole("button", { name: "125%" }));
    expect(width()).toBe("100%");
    for (let i = 0; i < 12; i++) {
      const more = screen.getByRole("button", { name: "Phóng to" }) as HTMLButtonElement;
      if (!more.disabled) fireEvent.click(more);
    }
    expect(width()).toBe("500%");
  }, 20000);

  it("xem song song: cuộn một bên thì bên kia cuộn theo", async () => {
    auth.isAdmin = true;
    open();
    fireEvent.click(await screen.findByRole("tab", { name: "Soát" }));
    await screen.findByLabelText("Hán dòng 1");
    fireEvent.click(await screen.findByText("Xem song song"));
    fireEvent.click(await screen.findByRole("button", { name: "Phóng to" }));
    const [left, right] = screen.getAllByTestId("khung-xem");
    left.scrollLeft = 40;
    left.scrollTop = 25;
    fireEvent.scroll(left);
    expect([right.scrollLeft, right.scrollTop]).toEqual([40, 25]);
  }, 20000);

  it("kéo từ nút giữa làn đỏ cũng di chuyển đường chia", async () => {
    auth.isAdmin = true;
    open();
    fireEvent.click(await screen.findByRole("tab", { name: "Soát" }));
    await screen.findByLabelText("Hán dòng 1");
    fireEvent.click(await screen.findByText("Kéo so sánh"));
    const line = await screen.findByTestId("duong-chia");
    const area = line.parentElement as HTMLElement;
    area.getBoundingClientRect = () => ({ left: 0, width: 200, top: 0, height: 100, right: 200, bottom: 100, x: 0, y: 0, toJSON: () => ({}) });
    // jsdom chưa có PointerEvent nên dùng MouseEvent mang đúng tên sự kiện để giữ clientX.
    const drag = (type: string, clientX: number) =>
      fireEvent(screen.getByTestId("nut-keo"), new MouseEvent(type, { bubbles: true, clientX, buttons: 1 }));
    drag("pointerdown", 50);
    expect(line.style.left).toBe("calc(25% - 7px)");
    drag("pointermove", 150);
    expect(line.style.left).toBe("calc(75% - 7px)");
  }, 20000);

  it("đánh dấu dòng: tô ô trên ảnh, có ghi chú, lưu vào nháp, bấm lại thì tắt", async () => {
    auth.isAdmin = true;
    const calls = open();
    fireEvent.click(await screen.findByRole("tab", { name: "Soát" }));
    await screen.findByLabelText("Hán dòng 1");
    await screen.findAllByTestId("o-chu");
    expect(document.querySelectorAll("[data-danh-dau]")).toHaveLength(0);
    fireEvent.click(screen.getByRole("button", { name: "OCR không rõ" }));
    expect(document.querySelectorAll("[data-danh-dau]")).toHaveLength(2);
    expect(screen.getByTestId("danh-sach-danh-dau").textContent).toContain("Đã đánh dấu 1 dòng");
    fireEvent.change(screen.getByLabelText("Ghi chú dòng 1"), { target: { value: "chữ thứ hai mờ" } });
    fireEvent.click(screen.getByRole("button", { name: "Lưu nháp" }));
    await screen.findByRole("button", { name: "Đã lưu" });
    const row = JSON.parse(calls.find((c) => c.method === "PUT")?.body ?? "{}").rows[0];
    expect(row).toMatchObject({ danh_dau: "ocr", ghi_chu: "chữ thứ hai mờ" });
    expect(row.ma).toMatch(/^[A-Za-z0-9_-]{1,40}$/);
    fireEvent.click(screen.getByRole("button", { name: "OCR không rõ" }));
    expect(document.querySelectorAll("[data-danh-dau]")).toHaveLength(0);
    expect(screen.queryByLabelText("Ghi chú dòng 1")).toBeNull();
  }, 20000);

  it("máy nghi dòng chưa dịch, đánh dấu cả loạt được", async () => {
    auth.isAdmin = true;
    open(undefined, undefined, "公回", "");
    fireEvent.click(await screen.findByRole("tab", { name: "Soát" }));
    await screen.findByLabelText("Hán dòng 1");
    expect(screen.getByText("Máy nghi: Chưa có bản dịch", { selector: "[data-testid='dong-soat'] *" })).toBeTruthy();
    fireEvent.click(screen.getByRole("button", { name: "Đánh dấu cả 1 dòng máy nghi" }));
    expect(screen.getByRole("button", { name: "Chưa dịch" }).getAttribute("aria-pressed")).toBe("true");
  }, 20000);

  it("gợi ý không tự ghi đè; nhận thì điền vào ô và tắt dấu; bỏ thì ẩn", async () => {
    auth.isAdmin = true;
    open(undefined, { a1: { han: "公歸", viet: "Ông trở về", lan: 2 } }, "公回", "Ông về", { danh_dau: "ocr", ma: "a1" });
    fireEvent.click(await screen.findByRole("tab", { name: "Soát" }));
    const han = (await screen.findByLabelText("Hán dòng 1")) as HTMLTextAreaElement;
    expect(screen.getByTestId("goi-y").textContent).toContain("公歸");
    expect(han.value).toBe("公回");
    fireEvent.click(screen.getByRole("button", { name: "Dùng chữ Hán này" }));
    expect(han.value).toBe("公歸");
    expect(screen.getByRole("button", { name: "OCR không rõ" }).getAttribute("aria-pressed")).toBe("false");
    expect(screen.getByTestId("goi-y").textContent).not.toContain("公歸");
    fireEvent.click(screen.getByRole("button", { name: "Bỏ gợi ý" }));
    expect(screen.queryByTestId("goi-y")).toBeNull();
    expect((screen.getByLabelText("Việt dòng 1") as HTMLTextAreaElement).value).toBe("Ông về");
  }, 20000);

  it("gợi ý đã bỏ không hiện lại, trừ khi có lần chạy mới", async () => {
    auth.isAdmin = true;
    open(undefined, { a1: { viet: "Mới", lan: 1 } }, "公回", "Ông về", { ma: "a1", bo_goi_y: 1 });
    fireEvent.click(await screen.findByRole("tab", { name: "Soát" }));
    await screen.findByLabelText("Hán dòng 1");
    expect(screen.queryByTestId("goi-y")).toBeNull();
  }, 20000);

  it("trang không có bản tâm thì không có ô sửa bản tâm", async () => {
    auth.isAdmin = true;
    open();
    fireEvent.click(await screen.findByRole("tab", { name: "Soát" }));
    await screen.findByLabelText("Hán dòng 1");
    await screen.findAllByTestId("o-chu");
    expect(screen.queryByLabelText("Bản tâm")).toBeNull();
  }, 20000);

  it("trang chưa có vị trí chữ vẫn kéo được bản dịch, không có ô và số trên ảnh", () => {
    render(
      <SoatOverlay
        mode="dich"
        imageUrl="/anh.jpg"
        khung={null}
        banTam=""
        draft={[]}
        rows={[
          { key: 7, viet: "Ông về", bo: false },
          { key: 8, viet: "R.42", bo: true },
          { key: 9, viet: "Đổi họ", bo: false },
        ]}
        marks
        page="001"
        onPick={() => {}}
        onPickTranslation={() => {}}
      />,
    );
    expect(screen.queryByTestId("o-chu")).toBeNull();
    // Dòng bỏ không hiện nhưng vẫn giữ số, để số khớp với số ở phần soát.
    expect(screen.getAllByTestId("dong-dich").map((d) => d.textContent)).toEqual(["1Ông về", "3Đổi họ"]);
    expect(screen.getByTestId("duong-chia")).toBeTruthy();
  });

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
