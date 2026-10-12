import { fireEvent, render, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";

import "@/i18n";
import { PageZoomModal, ZoomableImage } from "./ZoomableImage";

const modalProps = {
  open: true,
  onClose: () => {},
  imageUrl: "/p1.jpg",
  alt: "Trang 1",
  position: "1/3",
  hasPrev: false,
  hasNext: true,
  onPrev: () => {},
  onNext: () => {},
};

describe("ZoomableImage", () => {
  it("is a thumbnail that asks to open the zoom view (click or Enter)", () => {
    const onOpen = vi.fn();
    render(<ZoomableImage imageUrl="/p1.jpg" alt="Trang 1" onOpen={onOpen} />);
    fireEvent.click(screen.getByRole("button", { name: /Phóng to/ }));
    fireEvent.keyDown(screen.getByRole("button", { name: /Phóng to/ }), { key: "Enter" });
    expect(onOpen).toHaveBeenCalledTimes(2);
  });
});

describe("PageZoomModal", () => {
  it("opens in fit mode, toggles to full by clicking the image or the selector", async () => {
    render(<PageZoomModal {...modalProps} />);
    const body = await screen.findByTestId("zoom-body");
    expect(body).toHaveAttribute("data-mode", "screen");
    expect(body.querySelector("img")).toHaveStyle({ maxHeight: "78vh" });
    fireEvent.click(body);
    expect(screen.getByTestId("zoom-body")).toHaveAttribute("data-mode", "natural");
    expect(screen.getByTestId("zoom-body").querySelector("img")).toHaveStyle({ maxWidth: "none" });
    fireEvent.click(screen.getByText("Vừa"));
    expect(screen.getByTestId("zoom-body")).toHaveAttribute("data-mode", "screen");
  });

  it("shows the position and previous/next buttons (disabled at the ends)", async () => {
    const onNext = vi.fn();
    render(<PageZoomModal {...modalProps} onNext={onNext} />);
    expect(await screen.findByTestId("zoom-position")).toHaveTextContent("1/3");
    expect(screen.getByRole("button", { name: /Trang trước/ })).toBeDisabled();
    fireEvent.click(screen.getByRole("button", { name: /Trang sau/ }));
    expect(onNext).toHaveBeenCalledTimes(1);
  });

  it("arrow keys go to the previous / next page, but not while typing in a field", async () => {
    const onPrev = vi.fn();
    const onNext = vi.fn();
    render(
      <div>
        <input aria-label="gõ" />
        <PageZoomModal {...modalProps} hasPrev hasNext onPrev={onPrev} onNext={onNext} />
      </div>,
    );
    await screen.findByTestId("zoom-body");
    fireEvent.keyDown(window, { key: "ArrowRight" });
    fireEvent.keyDown(window, { key: "ArrowLeft" });
    expect(onNext).toHaveBeenCalledTimes(1);
    expect(onPrev).toHaveBeenCalledTimes(1);
    fireEvent.keyDown(screen.getByLabelText("gõ"), { key: "ArrowRight" });
    expect(onNext).toHaveBeenCalledTimes(1); // đang gõ chữ: không chuyển trang
  });

  it("ignores arrows at the ends and shows a notice (not a crash) for a page without an image", async () => {
    const onPrev = vi.fn();
    render(<PageZoomModal {...modalProps} imageUrl={null} hasPrev={false} onPrev={onPrev} />);
    expect(await screen.findByText("Chưa có ảnh cho trang này")).toBeInTheDocument();
    fireEvent.keyDown(window, { key: "ArrowLeft" });
    expect(onPrev).not.toHaveBeenCalled();
  });

  it("works for the text-box image too (draws the boxes)", async () => {
    const bbox = [{ order: 1, bbox_xyxy: [10, 20, 60, 90] as [number, number, number, number], han: "大" }];
    render(<PageZoomModal {...modalProps} alt="Trang 1 có khung chữ" bbox={bbox} showOrder />);
    expect(await screen.findByTestId("zoom-body")).toBeInTheDocument();
  });
});
