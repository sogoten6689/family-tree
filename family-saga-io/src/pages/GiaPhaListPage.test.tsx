import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import { beforeEach, describe, expect, it, vi } from "vitest";

import "@/i18n";
import type { GiaPhaListParams } from "@/lib/giaPhaApi";

const ALL = [
  { id: "F-B-PN-GiaThien-001-1930", ma_dinh_danh_pending: false, title: "Phan gia công phả", ho_toc: "Phan", status: "built", updated_at: "2026-10-02" },
  { id: "nom-147", ma_dinh_danh_pending: true, title: "Nguyễn tộc phả", ho_toc: "Nguyễn", status: "pending", updated_at: "2026-10-02" },
];

// Giả lập backend: lọc theo q (không dấu) và cắt trang như API thật.
const api = vi.hoisted(() => ({ listGiaPha: vi.fn(), getGiaPhaSummary: vi.fn() }));
vi.mock("@/lib/giaPhaApi", async (importOriginal) => ({
  ...(await importOriginal<typeof import("@/lib/giaPhaApi")>()),
  ...api,
}));
const fakeBackend = async (params: GiaPhaListParams = {}) => {
  const plain = (s: string) => s.normalize("NFD").replace(/[̀-ͯ]/g, "").replace(/đ/gi, "d").toLowerCase();
  const q = plain(params.q ?? "").trim();
  const matched = ALL.filter((i) => !q || plain(`${i.id} ${i.title} ${i.ho_toc}`).includes(q));
  const size = params.pageSize ?? 0;
  const start = size ? ((params.page ?? 1) - 1) * size : 0;
  return { total: matched.length, total_all: ALL.length, page: params.page ?? 1, page_size: size, items: size ? matched.slice(start, start + size) : matched };
};

if (typeof globalThis.ResizeObserver === "undefined") {
  globalThis.ResizeObserver = class {
    observe() {}
    unobserve() {}
    disconnect() {}
  } as unknown as typeof ResizeObserver;
}

const { default: GiaPhaListPage } = await import("./GiaPhaListPage");

const renderAt = (path: string) =>
  render(
    <QueryClientProvider client={new QueryClient({ defaultOptions: { queries: { retry: false, gcTime: 0 } } })}>
      <MemoryRouter initialEntries={[path]}>
        <GiaPhaListPage scope="admin" />
      </MemoryRouter>
    </QueryClientProvider>,
  );

const lastParams = () => api.listGiaPha.mock.calls.at(-1)?.[0] as GiaPhaListParams;
const searchBox = () => screen.getByRole("searchbox", { name: "Tìm kiếm gia phả" });

describe("GiaPhaListPage (phân trang + tìm kiếm ở backend)", { timeout: 15000 }, () => {
  beforeEach(() => {
    api.listGiaPha.mockReset();
    api.listGiaPha.mockImplementation(fakeBackend);
    api.getGiaPhaSummary.mockReset();
    api.getGiaPhaSummary.mockResolvedValue({
      scope: "admin", total: 2, built: 1, pending: 1, with_code: 1, without_code: 1,
      code_source: { catalogue: 1, gemini: 0, other: 0 }, public_trees: 0, nodes: 0, top_ho_toc: [], pages: null,
      generated_at: "2026-10-09T10:00:00+00:00",
    });
  });

  it("asks the backend for page 1 (size 10) and shows the count", async () => {
    renderAt("/admin/gia-pha");
    await screen.findByText("Phan gia công phả");
    expect(api.listGiaPha).toHaveBeenCalledTimes(1);
    expect(lastParams()).toMatchObject({ page: 1, pageSize: 10, q: "" });
    expect(screen.getByText("2/2 bộ")).toBeInTheDocument();
  });

  it("debounces typing, then searches on the backend (diacritic-insensitive)", async () => {
    renderAt("/admin/gia-pha");
    await screen.findByText("Phan gia công phả");
    fireEvent.change(searchBox(), { target: { value: "ngu" } });
    fireEvent.change(searchBox(), { target: { value: "nguyen" } });
    expect(api.listGiaPha).toHaveBeenCalledTimes(1); // chưa hết 300 ms: chưa gọi thêm
    await waitFor(() => expect(lastParams().q).toBe("nguyen"));
    expect(api.listGiaPha).toHaveBeenCalledTimes(2); // chỉ 1 lần cho cả "ngu" + "nguyen"
    expect(await screen.findByText("Nguyễn tộc phả")).toBeInTheDocument();
    expect(screen.queryByText("Phan gia công phả")).toBeNull();
    expect(screen.getByText("1/2 bộ")).toBeInTheDocument();
  });

  it("reads the query from the URL and sends it to the backend", async () => {
    renderAt("/admin/gia-pha?q=phan");
    await screen.findByText("Phan gia công phả");
    expect(lastParams().q).toBe("phan");
    expect(screen.queryByText("Nguyễn tộc phả")).toBeNull();
  });

  it("shows a no-match message instead of the empty-list message", async () => {
    renderAt("/admin/gia-pha?q=zzz");
    expect(await screen.findByText("Không có bộ nào khớp tìm kiếm/bộ lọc")).toBeInTheDocument();
  });

  it("shows 'Xoá bộ lọc' only when a filter is active and resets everything", async () => {
    renderAt("/admin/gia-pha?q=nguyen");
    await screen.findByText("Nguyễn tộc phả");
    expect(screen.queryByText("Phan gia công phả")).toBeNull();
    fireEvent.click(screen.getByRole("button", { name: /Xoá bộ lọc/ }));
    await screen.findByText("Phan gia công phả"); // đủ 2 dòng trở lại
    expect(lastParams()).toMatchObject({ q: "", page: 1 });
    expect((searchBox() as HTMLInputElement).value).toBe("");
    expect(screen.queryByRole("button", { name: /Xoá bộ lọc/ })).toBeNull(); // hết lọc → ẩn nút
  });

  it("shows the summary on top of the list (compact tiles) with its own request", async () => {
    renderAt("/admin/gia-pha");
    expect(await screen.findByText("Tổng số bộ gia phả")).toBeInTheDocument();
    expect(api.getGiaPhaSummary).toHaveBeenCalledTimes(1);
    expect(screen.queryByText("Họ tộc nhiều bộ nhất")).toBeNull(); // chế độ gọn
  });

  it("does not show the clear button when nothing is filtered", async () => {
    renderAt("/admin/gia-pha");
    await screen.findByText("Phan gia công phả");
    expect(screen.queryByRole("button", { name: /Xoá bộ lọc/ })).toBeNull();
  });

  it("changing page asks the backend for that page", async () => {
    api.listGiaPha.mockImplementation(async (params: GiaPhaListParams = {}) => ({
      total: 25,
      total_all: 25,
      page: params.page ?? 1,
      page_size: params.pageSize ?? 10,
      items: [{ ...ALL[0], id: `row-${params.page ?? 1}`, title: `Dòng của trang ${params.page ?? 1}` }],
    }));
    renderAt("/admin/gia-pha");
    await screen.findByText("Dòng của trang 1");
    fireEvent.click(await screen.findByTitle("2"));
    expect(await screen.findByText("Dòng của trang 2")).toBeInTheDocument();
    expect(lastParams()).toMatchObject({ page: 2, pageSize: 10 });
  });

  it("'Tải lại' bypasses the server cache", async () => {
    renderAt("/admin/gia-pha");
    await screen.findByText("Phan gia công phả");
    fireEvent.click(screen.getByRole("button", { name: /Tải lại/ }));
    await waitFor(() => expect(api.listGiaPha).toHaveBeenCalledTimes(2));
    expect(lastParams().refresh).toBe(true);
  });
});
