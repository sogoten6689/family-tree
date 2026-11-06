/** Phần dùng chung của lớp phủ và chế độ sửa ô: màu ô, phóng to, tính toán toạ độ ô chữ. */
import { useEffect, type Dispatch, type RefObject, type SetStateAction } from "react";

import type { KhungTrang } from "@/lib/doiChieuApi";

export type OChu = KhungTrang["chu"][number];
export type Hop = OChu["b"];
export type Diem = [number, number];

const BOX = "#1677ff";
const BOX_ESTIMATED = "#d46b08";
const BOX_HUMAN = "#389e0d";

export const ACTIVE_FILL = "rgba(22, 119, 255, 0.28)";
export const ACTIVE_STROKE = "#0050b3";

export interface RowLabel {
  n: number;
  key: number;
  x: number;
  y: number;
}

export const numberSize = (width: number) => width / 50;

/** Số dòng đặt ngay trên chữ đầu tiên của dòng đó. */
export const rowLabels = (cells: { b: Hop }[], width: number, rowKeys: (number | null)[], numbers: Map<number, number>): RowLabel[] => {
  const seen = new Set<number>();
  const labels: RowLabel[] = [];
  rowKeys.forEach((key, i) => {
    const n = key !== null && numbers.get(key);
    if (key === null || !n || seen.has(key)) return;
    seen.add(key);
    const [x0, y0, x1] = cells[i].b;
    const size = numberSize(width);
    // Dòng sát mép trên thì giữ số trong khung ảnh, chấp nhận đè lên chữ.
    labels.push({ n, key, x: (x0 + x1) / 2, y: Math.max(size, y0 - size * 0.25) });
  });
  return labels;
};

/**
 * Vị trí nhãn "Bản tâm": trên ô cao nhất của cột, hai hàng chữ để không đè lên số của các dòng hai bên.
 * Trả về đường chân của hàng dưới; trang không có ô bản tâm thì null.
 */
export const gutterLabel = (cells: { b: Hop }[], width: number): { x: number; y: number } | null => {
  if (!cells.length) return null;
  const top = cells.reduce((a, c) => (c.b[1] < a.b[1] ? c : a));
  const size = numberSize(width);
  return { x: (top.b[0] + top.b[2]) / 2, y: Math.max(size * 2, top.b[1] - size * 0.25) };
};

export const boxColor = ({ u, n }: Pick<OChu, "u" | "n">) => (n ? BOX_HUMAN : u ? BOX_ESTIMATED : BOX);

export const MIN_ZOOM = 1;
export const MAX_ZOOM = 5;
export const ZOOM_STEP = 1.25;
export const clampZoom = (z: number) => Math.min(MAX_ZOOM, Math.max(MIN_ZOOM, z));

/** Giữ Ctrl (hoặc chụm hai ngón trên bàn di chuột) rồi cuộn để phóng to. React gắn wheel ở chế độ không chặn được, nên gắn tay. */
export const useWheelZoom = (panes: RefObject<(HTMLDivElement | null)[]>, setZoom: Dispatch<SetStateAction<number>>, resetKey?: unknown) => {
  useEffect(() => {
    const zoomByWheel = (e: WheelEvent) => {
      if (!e.ctrlKey) return;
      e.preventDefault();
      setZoom((z) => clampZoom(z * Math.exp(-e.deltaY * 0.01)));
    };
    const nodes = panes.current.filter((n): n is HTMLDivElement => !!n);
    nodes.forEach((n) => n.addEventListener("wheel", zoomByWheel, { passive: false }));
    return () => nodes.forEach((n) => n.removeEventListener("wheel", zoomByWheel));
  }, [panes, setZoom, resetKey]);
};

const clamp = (v: number, low: number, high: number) => Math.min(high, Math.max(low, v));

/** Ô có hai góc đối nhau là `a`, `b`, nằm trọn trong ảnh, toạ độ nguyên, mỗi chiều ít nhất 1 điểm ảnh. */
export const boxFrom = (a: Diem, b: Diem, width: number, height: number): Hop => {
  const x0 = Math.round(clamp(Math.min(a[0], b[0]), 0, width - 1));
  const y0 = Math.round(clamp(Math.min(a[1], b[1]), 0, height - 1));
  const x1 = Math.round(clamp(Math.max(a[0], b[0]), 0, width));
  const y1 = Math.round(clamp(Math.max(a[1], b[1]), 0, height));
  return [x0, y0, Math.max(x1, x0 + 1), Math.max(y1, y0 + 1)];
};

/** Dời ô, giữ nguyên kích thước và không cho ra khỏi ảnh. */
export const moveBox = ([x0, y0, x1, y1]: Hop, dx: number, dy: number, width: number, height: number): Hop => {
  const nx = Math.round(clamp(x0 + dx, 0, width - (x1 - x0)));
  const ny = Math.round(clamp(y0 + dy, 0, height - (y1 - y0)));
  return [nx, ny, nx + (x1 - x0), ny + (y1 - y0)];
};

const middle = ([x0, y0, x1, y1]: Hop): Diem => [(x0 + x1) / 2, (y0 + y1) / 2];

/**
 * Vị trí chèn ô mới vào danh sách theo thứ tự đọc: cột từ phải sang trái, mỗi cột từ trên xuống. Thứ tự này quan
 * trọng vì chữ được dóng với dòng soát theo thứ tự ô, chèn sai chỗ thì chữ phục dựng hiện lệch.
 */
export const insertIndex = (cells: { b: Hop }[], box: Hop): number => {
  const [x, y] = middle(box);
  const sameColumn = (b: Hop) => b[0] <= x && x <= b[2];
  let above = -1;
  cells.forEach((cell, i) => {
    if (sameColumn(cell.b) && middle(cell.b)[1] <= y) above = i;
  });
  if (above >= 0) return above + 1;
  const next = cells.findIndex((cell) => sameColumn(cell.b) || middle(cell.b)[0] < x);
  return next >= 0 ? next : cells.length;
};
