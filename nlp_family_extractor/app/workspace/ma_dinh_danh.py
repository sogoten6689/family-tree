from __future__ import annotations

"""Mã định danh F-code cho "bộ gia phả" — port nguyên từ
hannom-bilingual-dataset/scripts/ma_dinh_danh_tables.py (nguồn chính thức đã
chốt với thầy). KHÔNG tự thêm/sửa giá trị bảng tra cứu ở đây khi chưa có xác
nhận mới từ repo nguồn.

Cấu trúc mã đầy đủ (ví dụ đã chốt): F-B-PN-GiaThien-001-1930
  F              cố định (Family)
  B              chữ A-V, tra HINH_THUC_LETTER[(quy_mo, hinh_thuc)]
  PN             mã Họ 2 chữ, tra HO_CODE[ho] (hoặc tự áp quy tắc nếu họ chưa có trong bảng)
  GiaThien       Địa Danh cấp thấp nhất đang có tên, không dấu không cách
  001            ID 3 chữ số, TĂNG DẦN theo thứ tự nhập catalogue — KHÔNG suy đoán
  1930           năm soạn BẢN GỐC, không phải năm ấn bản/dịch lại
"""

import re
import unicodedata

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

HO_CODE: dict[str, str] = {
    "Nguyễn": "NG", "Trần": "TR", "Vũ": "VU", "Võ": "VU", "Phạm": "PH",
    "Phan": "PN", "Lê": "LE", "Chu": "CH", "Đặng": "DA", "Đoàn": "DO",
    "Giang": "GI", "Là": "LA", "Mai": "MA",
}


def slugify_dia_danh(dia_danh: str) -> str:
    s = dia_danh.replace("Đ", "D").replace("đ", "d")
    s = unicodedata.normalize("NFKD", s).encode("ascii", "ignore").decode("ascii")
    s = re.sub(r"[^A-Za-z]+", "", s)
    return s


def ho_code_for(ho: str) -> str | None:
    if ho in HO_CODE:
        return HO_CODE[ho]
    s = ho.replace("Đ", "D").replace("đ", "d")
    s = unicodedata.normalize("NFKD", s).encode("ascii", "ignore").decode("ascii")
    s = re.sub(r"[^A-Za-z]", "", s).upper()
    return s[:2] if len(s) >= 2 else None


def build_ma_dinh_danh(
    quy_mo: str, hinh_thuc: str, ho: str, dia_danh_ngan: str, id_seq: int, nam_goc: int
) -> str:
    letter = HINH_THUC_LETTER.get((quy_mo, hinh_thuc))
    if letter is None:
        raise ValueError(f"Không có mã chữ cho (quy_mo={quy_mo!r}, hinh_thuc={hinh_thuc!r})")
    ho_code = ho_code_for(ho)
    if ho_code is None:
        raise ValueError(f"Không suy ra được mã Họ cho {ho!r}")
    dia_danh_slug = slugify_dia_danh(dia_danh_ngan)
    return f"F-{letter}-{ho_code}-{dia_danh_slug}-{id_seq:03d}-{nam_goc}"


# F-{chữ}-{họ 2 chữ}-{địa danh}-{3 số}-{năm} — để nhận diện mã ĐÃ CHỐT trong
# catalogue nghiên cứu (chép nguyên văn khi import, không tính lại).
MA_DINH_DANH_PATTERN = re.compile(r"^F-([A-V])-([A-Z]{2})-([A-Za-z]+)-(\d{3})-(\d{3,4})$")


def corpus_identifier_fields(record: dict) -> tuple[dict, list[str]]:
    """Trường định danh từ 1 record hannom-bilingual-dataset để ghi vào
    UserScan. `ma_dinh_danh` chỉ lấy khi đúng cấu trúc; năm soạn gốc lấy từ
    đoạn cuối của mã (đã được chốt), KHÔNG đọc từ văn mô tả `nien_dai`.
    Trả về (fields, cảnh báo)."""
    fields: dict = {}
    warnings: list[str] = []
    for src, dst in (("quy_mo", "quy_mo"), ("hinh_thuc", "hinh_thuc"), ("ho", "ho_toc")):
        value = record.get(src)
        if isinstance(value, str) and value.strip():
            fields[dst] = value.strip()
    dia_danh = record.get("dia_danh")
    if isinstance(dia_danh, str) and dia_danh.strip():
        fields["dia_danh"] = dia_danh.strip()[:512]
    nien_dai = record.get("nien_dai")
    if isinstance(nien_dai, str) and nien_dai.strip():
        fields["nien_dai_mo_ta"] = nien_dai.strip()
    code = record.get("ma_dinh_danh")
    if isinstance(code, str) and code.strip():
        match = MA_DINH_DANH_PATTERN.match(code.strip())
        if match:
            fields["ma_dinh_danh"] = code.strip()
            fields["nam_soan_goc"] = int(match.group(5))
        else:
            warnings.append(f"ma_dinh_danh {code!r} sai cấu trúc F-code — bỏ qua, không ghi.")
    return fields, warnings
