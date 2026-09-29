#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Bảng tra cứu CHÍNH THỨC cho mã định danh F-code, chép nguyên từ nguồn đã
chốt với thầy — KHÔNG tự thêm/sửa giá trị nào ở đây khi chưa có xác nhận mới.

Nguồn:
  - Bảng chữ cái A-V (Quy mô × Hình thức): family-tree/docs/lab/note_meeting_weekly/
    31_08_2026/31_08_2026.md (thầy gửi ảnh chụp bảng gốc, xác nhận lại 06/09)
  - Bảng mã Họ 2 chữ (12/12 đã duyệt): family-tree/docs/lab/note_meeting_weekly/
    31_08_2026/huong_dan_gia_pha_han_nom.md mục "Bảng mã Họ 2 chữ — ĐÃ DUYỆT 07/09"

Cấu trúc mã đầy đủ (ví dụ đã chốt): F-B-PN-GiaThien-001-1930
  F              cố định (Family)
  B              chữ A-V, tra HINH_THUC_LETTER[(quy_mo, hinh_thuc)]
  PN             mã Họ 2 chữ, tra HO_CODE[ho] (hoặc tự áp quy tắc nếu họ chưa có trong bảng)
  GiaThien       Địa Danh cấp thấp nhất đang có tên, không dấu không cách
  001            ID 3 chữ số, TĂNG DẦN theo thứ tự nhập catalogue — KHÔNG suy đoán,
                 chỉ điền khi có xác nhận thứ tự thật (xem README mục mã định danh)
  1930           năm soạn BẢN GỐC, không phải năm ấn bản/dịch lại
"""
from __future__ import annotations

import re
import unicodedata

# Quy mô × Hình thức -> chữ cái A-V (bỏ P, U). Nguồn: 31_08_2026.md, thầy xác nhận 06/09.
HINH_THUC_LETTER: dict[tuple[str, str], str] = {
    ("Tông phả", "Bộ"): "A", ("Tộc phả", "Bộ"): "B", ("Chi phả", "Bộ"): "C",
    ("Phân phả", "Bộ"): "D", ("Ngọc phả", "Bộ"): "E",
    ("Tông phả", "Đồ"): "F", ("Tộc phả", "Đồ"): "G", ("Chi phả", "Đồ"): "H",
    ("Phân phả", "Đồ"): "I", ("Ngọc phả", "Đồ"): "J",
    ("Tông phả", "Ký"): "K", ("Tộc phả", "Ký"): "L", ("Chi phả", "Ký"): "M",
    ("Phân phả", "Ký"): "N", ("Ngọc phả", "Ký"): "O",
    ("Tông phả", "Điệp"): "Q", ("Tộc phả", "Điệp"): "R", ("Chi phả", "Điệp"): "S",
    ("Phân phả", "Điệp"): "T", ("Ngọc phả", "Điệp"): "V",
}

# Mã Họ 2 chữ — 12/12 ĐÃ DUYỆT 07/09. Nguồn: huong_dan_gia_pha_han_nom.md.
HO_CODE: dict[str, str] = {
    "Nguyễn": "NG", "Trần": "TR", "Vũ": "VU", "Võ": "VU", "Phạm": "PH",
    "Phan": "PN", "Lê": "LE", "Chu": "CH", "Đặng": "DA", "Đoàn": "DO",
    "Giang": "GI", "Là": "LA", "Mai": "MA",
}


def slugify_dia_danh(dia_danh: str) -> str:
    """Không tự đoán 'cấp thấp nhất' từ chuỗi dài — hàm này chỉ chuẩn hoá 1 tên
    địa danh NGẮN đã được người đọc chọn sẵn (vd 'Gia Thiện' -> 'GiaThien')."""
    s = dia_danh.replace("Đ", "D").replace("đ", "d")
    s = unicodedata.normalize("NFKD", s).encode("ascii", "ignore").decode("ascii")
    s = re.sub(r"[^A-Za-z]+", "", s)
    return s


def ho_code_for(ho: str) -> str | None:
    """Tra bảng đã duyệt; nếu chưa có, áp quy tắc đã chốt: 2 chữ đầu tên không
    dấu, viết hoa — người gọi hàm này phải tự kiểm tra không trùng mã đã dùng."""
    if ho in HO_CODE:
        return HO_CODE[ho]
    s = ho.replace("Đ", "D").replace("đ", "d")
    s = unicodedata.normalize("NFKD", s).encode("ascii", "ignore").decode("ascii")
    s = re.sub(r"[^A-Za-z]", "", s).upper()
    return s[:2] if len(s) >= 2 else None


def build_ma_dinh_danh(quy_mo: str, hinh_thuc: str, ho: str, dia_danh_ngan: str,
                        id_seq: int, nam_goc: int) -> str:
    """Ghép mã — KHÔNG tự suy luận id_seq/nam_goc, người gọi phải truyền giá trị
    đã xác nhận (id_seq: thứ tự nhập catalogue thật; nam_goc: năm soạn bản GỐC)."""
    letter = HINH_THUC_LETTER.get((quy_mo, hinh_thuc))
    if letter is None:
        raise ValueError(f"Không có mã chữ cho (quy_mo={quy_mo!r}, hinh_thuc={hinh_thuc!r})")
    ho_code = ho_code_for(ho)
    if ho_code is None:
        raise ValueError(f"Không suy ra được mã Họ cho {ho!r}")
    dia_danh_slug = slugify_dia_danh(dia_danh_ngan)
    return f"F-{letter}-{ho_code}-{dia_danh_slug}-{id_seq:03d}-{nam_goc}"
