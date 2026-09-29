#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Sinh 17 file khung Track 1 (toàn Hán Nôm, chờ OCR) + 4 file Track 3 (Việt thuần).

Dữ liệu lấy từ family-tree/books_catalog.json + các fact đã đọc trực tiếp trong
phiên làm việc trước (không suy đoán mới). Track 1 chỉ có metadata + đường dẫn
ảnh trang — L1/L2/L3/pairs để null, chờ chạy vote_ocr.py + build_record.py thật.
"""
import json
from pathlib import Path

from _repo_paths import DATA_REPO_ROOT, FAMILY_TREE

ROOT = Path(__file__).resolve().parents[1]

catalog = json.loads((FAMILY_TREE / "data/00_raw/hannom/books_catalog.json").read_text(encoding="utf-8"))
BOOKS = {b["book_id"]: b for b in catalog["books"]}

# ---- ghi chú tay cho các trường chưa có trong books_catalog.json (quy_mo/hinh_thuc/dia_danh/nien_dai) ----
# Chỉ điền khi ĐÃ xác nhận (đọc nội dung) hoặc đánh dấu rõ "ứng viên"/"chưa phân loại" như trong
# Catalogue_Gia_Pha_Han_Nom.xlsx của family-tree — KHÔNG bịa thêm gì mới ở đây.
TRACK1_NOTES = {
    "nom-84": dict(quy_mo="Phân phả (suy luận — nội dung là tiểu sử 1 cá nhân)", hinh_thuc="Ký (khớp tên gọi + nội dung, đọc trực tiếp trang 1)",
                   ghi_chu="Đã xem ảnh trang 1: tiêu đề khớp catalog, văn xuôi cổ điển kể tiểu sử Nguyễn Văn Đạt. SUY LUẬN TỪ ẢNH, chưa chuyên gia xác nhận."),
    "nom-147": dict(quy_mo="Chưa phân loại", hinh_thuc="Chưa phân loại", ghi_chu="Chưa đọc nội dung."),
    "nom-207": dict(quy_mo="Tộc phả (theo tên gọi, chưa đọc để xác nhận)", hinh_thuc="Chưa phân loại", ghi_chu="Chưa đọc nội dung."),
    "nom-208": dict(quy_mo="Tộc phả (theo tên gọi, chưa xác nhận)", hinh_thuc="Chưa phân loại", ghi_chu="Chưa đọc nội dung. Địa danh Đông Trù chưa xác minh huyện/tỉnh."),
    "nom-429": dict(quy_mo="Chưa phân loại", hinh_thuc="Chưa phân loại", ghi_chu="page_count=0 trong nguồn crawl — cần kiểm tra lại file gốc trước khi OCR."),
    "nom-557": dict(quy_mo="Tộc phả/Đại tộc phả", hinh_thuc="Bia (NGOẠI LỆ — không thuộc 4 cột Bộ/Đồ/Ký/Điệp)",
                     ghi_chu="XÁC NHẬN qua đọc trực tiếp trang 2: lời tựa có câu 勒石 (khắc lên đá) — đúng là bia phả. Trang 3 lại là sơ đồ phả hệ theo đời — ranh giới Bia/Đồ ở tư liệu này không rõ ràng. Cần hỏi thầy xếp hình thức này vào đâu."),
    "nom-563": dict(quy_mo="Chưa phân loại", hinh_thuc="Chưa phân loại", ghi_chu="Chưa đọc nội dung. Nhân vật tiêu biểu: một vị Trạng nguyên hiệu Hu Liêu tiên sinh, chưa tra được tên huý."),
    "nom-833": dict(quy_mo="Chưa phân loại", hinh_thuc="Chưa phân loại",
                     ghi_chu="Địa danh 'Mộ Trạch' trong tên gọi CHƯA xác minh — Mộ Trạch nổi tiếng gắn với họ Vũ (đã xác nhận qua tìm kiếm web), cần kiểm tra vì sao đây lại là họ Lê trước khi tin theo tên gọi."),
    "nom-854": dict(quy_mo="Phân phả (suy luận)", hinh_thuc="Bộ (nghiêng về, chưa chắc)",
                     ghi_chu="Đã đọc bìa: '雙西就社阮堂家譜' (Song Tây Tựu xã Nguyễn đường gia phả), niên hiệu Khải Định Nhâm Tuất=1921 (có chú thích bút chì '1921' trùng khớp — độ tin cậy cao riêng phần niên đại). Người chép: cháu đời 9, hiệu Bính Chi. LƯU Ý: bìa ghi 家譜 (gia phả) không phải 譜記 (phả ký) như tên crawl — 2 nguồn không khớp nhau. Mới đọc 1/80 trang."),
    "nom-855": dict(quy_mo="Chưa phân loại", hinh_thuc="Chưa phân loại", ghi_chu="Chưa đọc nội dung."),
    "nom-865": dict(quy_mo="Phân phả (suy luận)", hinh_thuc="Ký (suy luận) — nội dung gần Trạch điền bạ/Hương tự bạ hơn phả ký thuần",
                     ghi_chu="Đã đọc trang 1-2: bìa khớp catalog (譜記廟墓), nội dung là lệ cúng giỗ + lập phả từ mộ Thủy tổ. Địa danh có thể đọc là 'Gia Viễn' (nay Ninh Bình) — ĐỘ TIN CẬY TRUNG BÌNH, chữ viết tay khó đọc, cần chuyên gia xác nhận lại."),
    "nom-1158": dict(quy_mo="Chưa phân loại", hinh_thuc="Chưa phân loại", ghi_chu="Chưa đọc nội dung."),
    "nom-1255": dict(quy_mo="Chưa phân loại (12 trang, quy mô nhỏ, có thể Phân phả)", hinh_thuc="Chưa phân loại", ghi_chu="Chưa đọc nội dung."),
    "nom-1256": dict(quy_mo="Tộc phả/Đại tộc phả (theo 'đại tông', chưa xác nhận)", hinh_thuc="Chưa phân loại", ghi_chu="Chưa đọc nội dung."),
    "pdf-1000-mai": dict(quy_mo="Tông phả", hinh_thuc="Bộ",
                          ghi_chu="XÁC NHẬN qua đọc phiên âm trang 11: 'mai thị tông phổ tứ biên' = Mai thị tông phổ, biên lần 4. Niên đại đọc được ở trang 2: Càn Long năm 56 (1791) — NIÊN HIỆU NHÀ THANH, có thể là gia phả gốc Hoa, cần xác minh thêm. Chỉ có phiên âm Hán-Việt (Paddle+Kim Hán Nôm lab), CHƯA có dịch nghĩa."),
    "pdf-1001-la": dict(quy_mo="Tông phả", hinh_thuc="Bộ",
                         ghi_chu="XÁC NHẬN qua đọc phiên âm trang 17: nhắc 'tông phả' và tổ 'La Phục công'. Chỉ có phiên âm, CHƯA có dịch nghĩa."),
    "pdf-1005-tran": dict(quy_mo="Tông phả", hinh_thuc="Bộ",
                           ghi_chu="XÁC NHẬN MẠNH qua đọc phiên âm trang 13 (mục lục đầy đủ '陳氏重修宗譜目錄' = Trần thị trùng tu tông phả mục lục, gồm thế huấn thuật, mộ điền, tế kí, thế mộ khảo...). Địa danh 'Kinh Giang' nhắc tới, chưa rõ nay ở đâu. Chỉ có phiên âm, CHƯA có dịch nghĩa."),
}

TRACK3_NOTES = {
    "pdf-nguyen-phuc-the-pha": dict(
        ten_han_viet="Nguyễn Phúc tộc thế phả (Thủy Tổ Phả - Vương Phả - Đế Phả)",
        quy_mo="Ngọc phả / Tôn phả", hinh_thuc="Bộ",
        dia_danh=None,
        nien_dai="Soạn 1990-1993 (hoàn thành bản thảo cuối 1993), in 1995, Nxb Thuận Hóa - Huế",
        ghi_chu="Đọc trực tiếp bìa + lời giới thiệu + lời nói đầu (PDF 477 trang, không lớp text, dùng PyMuPDF). ĐỘ TIN CẬY CAO vì viết hoàn toàn bằng Quốc ngữ, không cần suy đoán chữ Hán. Đây là BIÊN SOẠN MỚI bằng Quốc ngữ (tự nhận 'cuốn phả đầy đủ chép bằng Việt ngữ đầu tiên' của dòng họ), không dịch từ 1 bản Hán cổ nào — nên co_ban_han=false đúng bản chất, không phải vì thiếu sót. Thủy Tổ riêng nhánh Nguyễn Phúc: Nguyễn Kim (Triệu Tổ Tĩnh Hoàng Đế). Còn thiếu: quê quán cụ thể của Thủy Tổ (chưa đọc hết phần Thủy Tổ Phả)."),
    "docx-pham-1876": dict(
        ten_han_viet="Gia phả + Phó ý họ Phạm (biên dịch 2018)",
        quy_mo="Tộc phả", hinh_thuc="Bộ",
        dia_danh="Tiên Lã (mộ liệt tổ, xứ Chi Phong), xã An Trung",
        nien_dai="Năm Long Phi Tự Đức 30 = 1876 (ghi rõ trong lời tựa) — bản dịch lại 2018",
        ghi_chu="Word chỉ còn 4 ký tự CJK trên 53.012 ký tự — gần như chỉ còn bản dịch/phiên âm Quốc ngữ, KHÔNG có ảnh scan gốc trong repo để đối chiếu Hán. co_ban_han=false vì không còn bản Hán khả dụng, dù văn bản gốc dùng chữ Hán từng tồn tại (1876)."),
    "docx-tran-200": dict(
        ten_han_viet="Gia phả họ Trần — Thanh Thủy Thượng, Hương Thủy, TT-Huế",
        quy_mo="Tộc phả", hinh_thuc="Bộ",
        dia_danh="Thanh Thủy Thượng, phường Thủy Dương, TX Hương Thủy, tỉnh Thừa Thiên-Huế",
        nien_dai="Tu phổ tháng 2 Thành Thái 2 = 1890 — bản dịch lại 05/2018",
        ghi_chu="Chỉ 5 ký tự CJK trên 20.091 ký tự (vài chữ chú thích). KHÔNG có ảnh scan gốc ký hiệu GSL HN.2011.11.200 trong repo. co_ban_han=false."),
    "nguyen-ke-gia-pha": dict(
        ten_han_viet="Nguyễn Kế gia phả — ảnh Quốc ngữ viết tay (+ bằng khoán Diên Khánh)",
        quy_mo="Chưa phân loại", hinh_thuc="Chưa phân loại",
        dia_danh="Diên Khánh (chưa rõ tỉnh/thành hiện nay)",
        nien_dai=None,
        ghi_chu="Ảnh chụp tay bằng chữ Quốc ngữ (không phải Hán) — CHƯA transcribe (đã gỡ OCR nhầm trước đó theo inventory.md gốc). Cần transcribe (đọc chữ viết tay Quốc ngữ) trước khi có l3_dich_nghia thật, không cần OCR Hán."),
}


def page_stub(book):
    root = (book.get("paths") or {}).get("root")
    n = book.get("page_count") or 0
    if not root or n == 0:
        return []
    # Chỉ liệt kê vài trang đại diện (đầu / giữa / cuối) làm khung — không liệt kê hết
    # hàng trăm trang nếu volume lớn; danh sách đầy đủ sinh khi chạy OCR thật.
    sample_idx = sorted(set([1, max(1, n // 2), n]))
    pages = []
    for i in sample_idx:
        pages.append({
            "page_id": f"{i:03d}",
            "l0_image": f"{root}/{i:03d}.jpg" if not root.endswith(".pdf") else root,
            "l1_ocr": None,
            "l2_phien_am": None,
            "l3_dich_nghia": None,
            "pairs": []
        })
    return pages


def build_track1():
    out_dir = DATA_REPO_ROOT / "data" / "track1_hannom_only"
    manifest = json.loads((ROOT / "manifest" / "classification.json").read_text(encoding="utf-8"))
    ids = [e["doc_id"] for e in manifest["entries"] if e["track"] == 1]
    for bid in ids:
        book = BOOKS[bid]
        note = TRACK1_NOTES.get(bid, {})
        record = {
            "doc_id": bid,
            "track": 1,
            "co_ban_han": True,
            "ten_goc_han": book.get("title_han") or None,
            "ten_han_viet": book.get("title_vn") or bid,
            "ho": None,
            "quy_mo": note.get("quy_mo", "Chưa phân loại"),
            "hinh_thuc": note.get("hinh_thuc", "Chưa phân loại"),
            "dia_danh": note.get("dia_danh"),
            "nien_dai": note.get("nien_dai"),
            "nguon": {
                "duong_dan_goc": (book.get("paths") or {}).get("root") or "",
                "loai_tu_lieu": "pdf_anh_scan" if bid.startswith("pdf-") else "anh_scan",
            },
            "pages": page_stub(book),
            "status": "draft",
            "ghi_chu": note.get("ghi_chu", "Chưa OCR — chờ chạy scripts/vote_ocr.py."),
            "provenance": {"created_at": "2026-09-08", "pipeline_version": "v0.1", "reviewed_by": None},
        }
        (out_dir / f"{bid}.json").write_text(json.dumps(record, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"Track 1: đã ghi {len(ids)} file vào {out_dir}")


def build_track3():
    out_dir = DATA_REPO_ROOT / "data" / "track3_viet_only"
    manifest = json.loads((ROOT / "manifest" / "classification.json").read_text(encoding="utf-8"))
    ids = [e["doc_id"] for e in manifest["entries"] if e["track"] == 3]
    for bid in ids:
        book = BOOKS[bid]
        note = TRACK3_NOTES[bid]
        record = {
            "doc_id": bid,
            "track": 3,
            "co_ban_han": False,
            "ten_goc_han": None,
            "ten_han_viet": note["ten_han_viet"],
            "ho": None,
            "quy_mo": note["quy_mo"],
            "hinh_thuc": note["hinh_thuc"],
            "dia_danh": note["dia_danh"],
            "nien_dai": note["nien_dai"],
            "nguon": {
                "duong_dan_goc": (book.get("paths") or {}).get("root") or "",
                "loai_tu_lieu": "docx" if bid.startswith("docx-") else ("pdf_anh_scan" if bid.startswith("pdf-") else "anh_chup_quoc_ngu"),
            },
            "pages": [],
            "status": "draft",
            "ghi_chu": note["ghi_chu"],
            "provenance": {"created_at": "2026-09-08", "pipeline_version": "v0.1", "reviewed_by": None},
        }
        (out_dir / f"{bid}.json").write_text(json.dumps(record, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"Track 3: đã ghi {len(ids)} file vào {out_dir}")


if __name__ == "__main__":
    build_track1()
    build_track3()
