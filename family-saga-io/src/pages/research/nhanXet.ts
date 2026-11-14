import type { LoaiNhanXet, NhanXet } from "@/lib/doiChieuApi";

export const LOAI_LABEL: Record<LoaiNhanXet, string> = {
  OMISSION: "OMISSION – thiếu ý",
  ADDITION: "ADDITION – thừa ý",
  MISSING: "MISSING – thiếu vế/cặp",
  chu_han: "Chữ Hán / OCR",
  ten_rieng: "Tên riêng",
  dinh_dang: "Định dạng / tệp",
  bao_cao: "Báo cáo",
  khac: "Khác",
};

export const TRANG_THAI_LABEL: Record<NhanXet["trang_thai"], string> = {
  nhap: "Nháp",
  da_duyet: "Đã duyệt, chờ gửi",
  da_gui: "Đã gửi sinh viên",
};

/** Tin nhắn gửi sinh viên: mở đầu, danh sách cần sửa (đánh số, kèm số dòng), lời kết. */
export const buildMessage = (nx: Pick<NhanXet, "mo_dau" | "muc" | "ket">): string => {
  const items = nx.muc
    .filter((m) => m.noi_dung.trim())
    .map((m, i) => `${i + 1}. ${m.dong ? `Dòng ${m.dong}: ` : ""}${m.noi_dung.trim()}`);
  return [nx.mo_dau.trim(), items.length ? `Cần sửa:\n${items.join("\n")}` : "", nx.ket.trim()].filter(Boolean).join("\n\n");
};
