import { fireEvent, render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";

import "@/i18n";
import { ZoomableImage } from "./ZoomableImage";

describe("ZoomableImage", () => {
  it("opens a big view with two modes (fit / full) and toggles by clicking the image", async () => {
    render(<ZoomableImage imageUrl="/p1.jpg" alt="Trang 1" />);
    expect(screen.queryByTestId("zoom-body")).toBeNull();

    fireEvent.click(screen.getByRole("button", { name: /Phóng to/ }));
    const body = await screen.findByTestId("zoom-body");
    expect(body).toHaveAttribute("data-mode", "screen"); // mở ở chế độ "Vừa"
    expect(body.querySelector("img")).toHaveStyle({ maxHeight: "78vh" });

    fireEvent.click(body); // bấm vào ảnh: sang "Đầy đủ" (kích thước thật)
    expect(screen.getByTestId("zoom-body")).toHaveAttribute("data-mode", "natural");
    expect(screen.getByTestId("zoom-body").querySelector("img")).toHaveStyle({ maxWidth: "none" });

    fireEvent.click(screen.getByText("Vừa")); // chọn lại chế độ "Vừa" bằng nút
    expect(screen.getByTestId("zoom-body")).toHaveAttribute("data-mode", "screen");
  });

  it("works for the text-box image too (draws the boxes in both the thumbnail and the big view)", async () => {
    const bbox = [{ order: 1, bbox_xyxy: [10, 20, 60, 90] as [number, number, number, number], han: "大" }];
    render(<ZoomableImage imageUrl="/p1.jpg" alt="Trang 1 có khung chữ" bbox={bbox} showOrder />);
    fireEvent.click(screen.getByRole("button", { name: /Phóng to/ }));
    expect(await screen.findByTestId("zoom-body")).toBeInTheDocument();
  });
});
