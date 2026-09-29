from __future__ import annotations

# Bảng 25 họ A-Y theo tần suất trên corpus VietnamGiaPha (2.152 cây, 08/2026).
# Nguồn: docs/lab/note_meeting_weekly/28_08_2026/bang_ma_ho_A_Y.md
# Không gộp Hoàng/Huỳnh, Vũ/Võ — khớp đúng chữ viết trên phả.
LINEAGE_SURNAME_CODES: list[tuple[str, str]] = [
    ("A", "Nguyễn"),
    ("B", "Trần"),
    ("C", "Lê"),
    ("D", "Phạm"),
    ("E", "Vũ"),
    ("F", "Phan"),
    ("G", "Hoàng"),
    ("H", "Bùi"),
    ("I", "Ngô"),
    ("J", "Đỗ"),
    ("K", "Đặng"),
    ("L", "Trương"),
    ("M", "Huỳnh"),
    ("N", "Đoàn"),
    ("O", "Đinh"),
    ("P", "Võ"),
    ("Q", "Dương"),
    ("R", "Mai"),
    ("S", "Đào"),
    ("T", "Hà"),
    ("U", "Lương"),
    ("V", "Trịnh"),
    ("W", "Lưu"),
    ("X", "Lâm"),
    ("Y", "Hồ"),
]

_SURNAME_TO_LETTER = {name.lower(): letter for letter, name in LINEAGE_SURNAME_CODES}

_PREFIXES_TO_STRIP = ("dòng họ ", "chi tộc ", "tộc phả ", "gia phả ", "phả hệ ", "họ ")


def extract_surname(tree_name: str) -> str:
    """Suy ra họ từ tên cây (lineage_name), bỏ tiền tố mô tả thường gặp.

    Cùng phương pháp đã dùng khi đếm bảng mã họ A-Y (xem file nguồn ở trên):
    khớp đầu chuỗi sau khi bỏ tiền tố Họ / Dòng họ / Chi tộc / Gia phả / ...
    """
    normalized = (tree_name or "").strip()
    # Bóc lặp: "Gia phả họ Vũ" có 2 lớp tiền tố chồng nhau ("gia phả " rồi
    # "họ ") — bóc 1 lần rồi dừng sẽ để sót "họ" thành họ giả.
    stripped_any = True
    while stripped_any:
        stripped_any = False
        lowered = normalized.lower()
        for prefix in _PREFIXES_TO_STRIP:
            if lowered.startswith(prefix):
                normalized = normalized[len(prefix):].strip()
                stripped_any = True
                break
    parts = normalized.split()
    return parts[0] if parts else ""


def surname_letter_code(surname: str) -> str:
    """A-Y nếu khớp đúng 1 trong 25 họ (không phân biệt hoa/thường), Z nếu không."""
    return _SURNAME_TO_LETTER.get(surname.strip().lower(), "Z")


def build_lineage_code(tree_name: str, sequence: int) -> str:
    """Công thức: F-{A...Y|Z}-{NNN}. `sequence` là số thứ tự trong mã họ đó."""
    letter = surname_letter_code(extract_surname(tree_name))
    return f"F-{letter}-{sequence:03d}"
