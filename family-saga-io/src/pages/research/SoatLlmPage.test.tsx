import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import { beforeEach, describe, expect, it, vi } from "vitest";

import type { LlmDataset, LlmDatasetList } from "@/lib/llmSoatApi";

if (typeof globalThis.ResizeObserver === "undefined") {
  globalThis.ResizeObserver = class {
    observe() {}
    unobserve() {}
    disconnect() {}
  } as unknown as typeof ResizeObserver;
}
if (!window.matchMedia) {
  window.matchMedia = ((q: string) => ({
    matches: false, media: q, onchange: null, addListener() {}, removeListener() {},
    addEventListener() {}, removeEventListener() {}, dispatchEvent: () => false,
  })) as unknown as typeof window.matchMedia;
}

const auth = vi.hoisted(() => ({ isAdmin: true }));
vi.mock("@/contexts/AuthContext", () => ({ useAuth: () => auth }));

const api = vi.hoisted(() => ({
  getLlmDatasets: vi.fn(),
  getLlmDataset: vi.fn(),
  getLlmPhaHe: vi.fn(),
  putLlmReview: vi.fn(),
  deleteLlmReview: vi.fn(),
  exportLlmReviewed: vi.fn(),
}));
vi.mock("@/lib/llmSoatApi", async (orig) => ({ ...(await orig<typeof import("@/lib/llmSoatApi")>()), ...api }));

import SoatLlmPage from "./SoatLlmPage";

const LIST: LlmDatasetList = {
  version: "v1",
  co_du_lieu: true,
  datasets: [
    { id: "aaaaaaaaaa", label: "giapha_test.jsonl", group: "Tổng hợp", path: "/x/giapha_test.jsonl", mtime: 0, mau: 1, co_quan_he: 1, nguoi_tb: 2, da_soat: 0, xem_lai: 0, da_sua: 0 },
    { id: "bbbbbbbbbb", label: "v3_persons/test.jsonl", group: "VGP (văn xuôi thật)", path: "/x/test.jsonl", mtime: 0, mau: 0, co_quan_he: 0, nguoi_tb: 0, da_soat: 0, xem_lai: 0, da_sua: 0 },
  ],
};
const P = (name: string, gender: "male" | "female") => ({ name, birth: null, death: null, generation: 1, gender });
const DS: LlmDataset = {
  id: "aaaaaaaaaa",
  label: "giapha_test.jsonl",
  group: "Tổng hợp",
  path: "/x/giapha_test.jsonl",
  samples: [
    {
      idx: 0,
      key: "0123456789abcdef",
      input: "Ông Lê Văn An lấy bà Trần Thị Bình.",
      answer: { persons: [P("Lê Văn An", "male"), P("Trần Thị Bình", "female")], relations: [{ from: "Lê Văn An", to: "Trần Thị Bình", type: "spouse" }] },
      meta: null,
      error: null,
      review: null,
    },
  ],
};

const renderAt = (url: string) =>
  render(
    <QueryClientProvider client={new QueryClient({ defaultOptions: { queries: { retry: false } } })}>
      <MemoryRouter initialEntries={[url]}>
        <SoatLlmPage />
      </MemoryRouter>
    </QueryClientProvider>,
  );

describe("SoatLlmPage", () => {
  beforeEach(() => {
    auth.isAdmin = true;
    Object.values(api).forEach((f) => f.mockReset());
    api.getLlmDatasets.mockResolvedValue(LIST);
    api.getLlmDataset.mockResolvedValue(DS);
    api.putLlmReview.mockResolvedValue({ review: { status: "da", note: null, answer: null, updated_at: "t" } });
  });

  it("đòi admin", () => {
    auth.isAdmin = false;
    renderAt("/nghien-cuu/soat-llm");
    expect(screen.getByText("Trang này cần đăng nhập tài khoản admin.")).toBeInTheDocument();
    expect(api.getLlmDatasets).not.toHaveBeenCalled();
  });

  it("liệt kê bộ dữ liệu theo nhóm", async () => {
    renderAt("/nghien-cuu/soat-llm");
    expect(await screen.findByText("giapha_test.jsonl")).toBeInTheDocument();
    expect(screen.getByText("v3_persons/test.jsonl")).toBeInTheDocument();
    expect(screen.getByText("VGP (văn xuôi thật)")).toBeInTheDocument();
  });

  it("mở một mẫu, tô tên, vẽ cây và lưu đã soát", async () => {
    renderAt("/nghien-cuu/soat-llm?bo=aaaaaaaaaa&mau=0");
    expect(await screen.findByRole("img", { name: "Cây gia phả của mẫu" })).toBeInTheDocument();
    expect(screen.getAllByTitle("Lê Văn An").length).toBeGreaterThan(0);
    fireEvent.click(screen.getByRole("button", { name: /Đã soát, sang mẫu sau/ }));
    await waitFor(() => expect(api.putLlmReview).toHaveBeenCalledWith("aaaaaaaaaa", "0123456789abcdef", { status: "da", note: null, answer: null }));
  });
});
