import { fireEvent, render, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";

import "@/i18n";

const api = vi.hoisted(() => ({ getDocumentNeighbors: vi.fn() }));
vi.mock("@/lib/userWorkspaceApi", async (importOriginal) => ({
  ...(await importOriginal<typeof import("@/lib/userWorkspaceApi")>()),
  ...api,
}));

const { DocumentNeighborNav } = await import("./DocumentNeighborNav");

describe("DocumentNeighborNav", () => {
  it("shows position and goes to the previous / next document", async () => {
    api.getDocumentNeighbors.mockResolvedValue({
      prev: { id: 21, title: "Yên Lãng" },
      next: { id: 23, title: "Họ Phan" },
      position: 3,
      total: 22,
    });
    const onGo = vi.fn();
    render(<DocumentNeighborNav scanId={22} onGo={onGo} />);
    expect(await screen.findByText("3/22")).toBeInTheDocument();
    fireEvent.click(screen.getByRole("button", { name: /Trước/ }));
    expect(onGo).toHaveBeenLastCalledWith(21);
    fireEvent.click(screen.getByRole("button", { name: /Sau/ }));
    expect(onGo).toHaveBeenLastCalledWith(23);
  });

  it("disables the missing side at either end", async () => {
    api.getDocumentNeighbors.mockResolvedValue({ prev: null, next: { id: 2, title: "B" }, position: 1, total: 2 });
    render(<DocumentNeighborNav scanId={1} onGo={() => {}} />);
    await screen.findByText("1/2");
    expect(screen.getByRole("button", { name: /Trước/ })).toBeDisabled();
    expect(screen.getByRole("button", { name: /Sau/ })).toBeEnabled();
  });

  it("renders nothing when there is only one document or the request fails", async () => {
    api.getDocumentNeighbors.mockResolvedValue({ prev: null, next: null, position: 1, total: 1 });
    const { container, rerender } = render(<DocumentNeighborNav scanId={1} onGo={() => {}} />);
    await vi.waitFor(() => expect(api.getDocumentNeighbors).toHaveBeenLastCalledWith(1));
    expect(container).toBeEmptyDOMElement();
    api.getDocumentNeighbors.mockRejectedValue(new Error("403"));
    rerender(<DocumentNeighborNav scanId={2} onGo={() => {}} />);
    await vi.waitFor(() => expect(api.getDocumentNeighbors).toHaveBeenLastCalledWith(2));
    expect(container).toBeEmptyDOMElement();
  });
});
