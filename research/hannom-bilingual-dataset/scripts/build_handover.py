#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Đóng gói dữ liệu giao cho sinh viên theo một tệp phân công (manifest/phan_cong_*.json).

Mỗi sinh viên một thư mục, chia theo loại việc (xem biên bản họp 26/10/2026):
  soat/<doc_id>/      cặp câu Hán – bản dịch máy để soát (cap_cau.csv + .jsonl), ngữ cảnh từng trang, ảnh
  ocr/<doc_id>/       ảnh trang cần OCR
  dich_may/<doc_id>/  đã OCR, chưa dịch máy: chữ Hán từng trang + ảnh
  dich_nguoi/<doc_id>/ cuốn có bản dịch người: tệp dịch hoặc ảnh trang dịch; phần ở máy Windows ghi CHO_DU_LIEU.md
Ảnh lớn được nén lại (cạnh dài ≤ MAX_EDGE, JPEG chất lượng 85) để gửi nhẹ hơn; ảnh gốc không bị sửa.

Chỉ đọc dữ liệu, chỉ ghi vào --out (mặc định family-tree/data/05_ops/ban_giao/<đợt>/, đã gitignore).
Không gọi OCR/dịch máy, không gửi gì đi.

  python3 scripts/build_handover.py --config manifest/phan_cong_2026-10-26.json \
      --family-tree /path/to/family-tree [--zip]
"""
from __future__ import annotations

import argparse
import csv
import json
import shutil
import sys
from pathlib import Path

from PIL import Image

sys.path.insert(0, str(Path(__file__).resolve().parent))
from _repo_paths import DATA_REPO_ROOT  # noqa: E402
from ocr_adapters.base import first_existing_file, paddle_dir_candidates  # noqa: E402
from ocr_adapters.paddle_v6 import boxes_from_json, column_order_indices  # noqa: E402

MAX_EDGE = 2400
EDGE_TOLERANCE = 8  # như export_page_bbox.py: Paddle làm tròn / nới khung vài pixel
VERTICAL_RATIO = 1.5  # PPOCRLabel xoay ảnh crop 90° khi cao/rộng ≥ 1.5 (cột chữ dọc)
RECOMPRESS_ABOVE = 1_500_000  # byte
CSV_COLS = ["id", "trang", "dong", "han", "viet_may", "viet_sua", "trang_thai", "ghi_chu",
            "align_method", "confidence"]
B0_COLS = ["doc_id", "ten", "viec", "so_trang_du_kien", "dang_tu_lieu", "so_trang_thuc",
           "co_ban_dich", "co_phien_am", "chat_luong_anh", "trang_thieu_hoac_trung", "ghi_chu"]
TITLES = {"soat": "Soát cặp câu", "ocr": "OCR", "dich_may": "Dịch máy rồi soát", "dich_nguoi": "Dóng hàng với bản dịch người"}


def load_records() -> dict[str, dict]:
    recs = {}
    for f in sorted((DATA_REPO_ROOT / "data").glob("track*/*.json")):
        d = json.loads(f.read_text(encoding="utf-8"))
        recs[d["doc_id"]] = d
    return recs


def title(rec: dict) -> str:
    return rec.get("ten_han_viet") or rec.get("ten_goc_han") or rec["doc_id"]


def copy_image(src: Path, dst: Path) -> int:
    dst.parent.mkdir(parents=True, exist_ok=True)
    if src.stat().st_size <= RECOMPRESS_ABOVE:
        shutil.copy2(src, dst)
    else:
        with Image.open(src) as im:
            im = im.convert("RGB")
            im.thumbnail((MAX_EDGE, MAX_EDGE))
            im.save(dst.with_suffix(".jpg"), "JPEG", quality=85, optimize=True)
            dst = dst.with_suffix(".jpg")
    return dst.stat().st_size


def page_images(rec: dict, ft: Path, out: Path) -> tuple[dict[str, Path], int]:
    """Chép ảnh trang vào out/anh/; trả {page_id: ảnh trong gói} và tổng dung lượng."""
    images, size = {}, 0
    for p in rec["pages"]:
        if not p.get("l0_image"):
            continue
        src = ft / p["l0_image"]
        if src.exists():
            dst = out / "anh" / f"{p['page_id']}{src.suffix.lower()}"
            size += copy_image(src, dst)
            images[p["page_id"]] = dst if dst.exists() else dst.with_suffix(".jpg")
    return images, size


def crop_quad(im: Image.Image, quad: list[list[float]]) -> Image.Image:
    """Cắt vùng tứ giác về hình chữ nhật, xoay 90° nếu là cột dọc — giống PPOCRLabel."""
    (x0, y0), (x1, y1), (x2, y2), (x3, y3) = quad  # trên-trái, trên-phải, dưới-phải, dưới-trái
    w = max(2, round(max(((x1 - x0) ** 2 + (y1 - y0) ** 2) ** 0.5, ((x2 - x3) ** 2 + (y2 - y3) ** 2) ** 0.5)))
    h = max(2, round(max(((x3 - x0) ** 2 + (y3 - y0) ** 2) ** 0.5, ((x2 - x1) ** 2 + (y2 - y1) ** 2) ** 0.5)))
    crop = im.transform((w, h), Image.QUAD, (x0, y0, x3, y3, x2, y2, x1, y1), Image.BICUBIC)
    return crop.rotate(90, expand=True) if h / w >= VERTICAL_RATIO else crop


def write_raw_ppocr(rec: dict, book: dict | None, ft: Path, images: dict[str, Path], out: Path) -> int:
    """raw/ theo định dạng PPOCRLabel từ khung chữ Paddle có sẵn: Label.txt, rec_gt.txt, fileState.txt
    (rỗng: chưa ảnh nào được người xác nhận) và crop_img/. Toạ độ quy về ảnh trong gói (có thể đã nén)."""
    if not book:
        return 0
    raw, crops = out / "raw", out / "crop_img"
    labels, rec_gt, n = [], [], 0
    for p in rec["pages"]:
        img_path = images.get(p["page_id"])
        stem = Path(p.get("l0_image") or "").stem
        js = first_existing_file(paddle_dir_candidates(book, ft), f"{stem}-paddleocr.json") if stem else None
        boxes = boxes_from_json(js) if js else None
        if not boxes or img_path is None:
            continue
        with Image.open(ft / p["l0_image"]) as orig:
            ow, oh = orig.size
        with Image.open(img_path) as im:
            im = im.convert("RGB")
            scale = im.width / ow
            if any(max(float(pt[0]) for pt in poly) > ow + EDGE_TOLERANCE or
                   max(float(pt[1]) for pt in poly) > oh + EDGE_TOLERANCE for poly, _, _ in boxes):
                print(f"[{rec['doc_id']}] trang {p['page_id']}: khung vượt ảnh {ow}x{oh} — bỏ", file=sys.stderr)
                continue
            shapes = []
            for i in column_order_indices(boxes):
                poly, text, _ = boxes[i]
                quad = [[min(max(round(float(x) * scale), 0), im.width), min(max(round(float(y) * scale), 0), im.height)]
                        for x, y in poly[:4]]
                name = f"{img_path.stem}_crop_{len(shapes)}.jpg"
                crops.mkdir(parents=True, exist_ok=True)
                crop_quad(im, quad).save(crops / name, "JPEG", quality=90)
                shapes.append({"transcription": text.strip(), "points": quad, "difficult": False})
                rec_gt.append(f"crop_img/{name}\t{text.strip()}")
            labels.append(f"anh/{img_path.name}\t{json.dumps(shapes, ensure_ascii=False)}")
            n += len(shapes)
    if labels:
        raw.mkdir(parents=True, exist_ok=True)
        (raw / "Label.txt").write_text("\n".join(labels) + "\n", encoding="utf-8")
        (raw / "rec_gt.txt").write_text("\n".join(rec_gt) + "\n", encoding="utf-8")
        (raw / "fileState.txt").write_text("", encoding="utf-8")
    return n


def page_context(rec: dict, out: Path) -> None:
    """Toàn văn từng trang (OCR, phiên âm, dịch máy) để đọc ngữ cảnh khi soát."""
    with (out / "trang.jsonl").open("w", encoding="utf-8") as f:
        for p in rec["pages"]:
            l1 = p.get("l1_ocr") or {}
            f.write(json.dumps({"trang": p["page_id"], "han": l1.get("voted_text"),
                                "phien_am": p.get("l2_phien_am"), "viet_may": p.get("l3_dich_nghia")},
                               ensure_ascii=False) + "\n")


def write_pairs(rec: dict, out: Path, slug: str) -> int:
    rows = []
    for p in rec["pages"]:
        for i, q in enumerate(p.get("pairs") or [], 1):
            rows.append({"id": f"{rec['doc_id']}:{p['page_id']}:{i:03d}", "trang": p["page_id"], "dong": i,
                         "han": q.get("han", ""), "viet_may": q.get("viet", ""), "viet_sua": "",
                         "trang_thai": "chua_soat", "ghi_chu": "",
                         "align_method": q.get("align_method", ""), "confidence": q.get("confidence", "")})
    # CSV có BOM để mở thẳng bằng Excel/Google Sheets; JSONL là bản chuẩn để nộp lại.
    with (out / "cap_cau.csv").open("w", encoding="utf-8-sig", newline="") as f:
        w = csv.DictWriter(f, fieldnames=CSV_COLS)
        w.writeheader()
        w.writerows(rows)
    with (out / "cap_cau.jsonl").open("w", encoding="utf-8") as f:
        for r in rows:
            f.write(json.dumps({"doc_id": rec["doc_id"], **r, "nguon_dich": "may", "nguoi_soat": slug},
                               ensure_ascii=False) + "\n")
    return len(rows)


def render_pdf_pages(pdf: Path, first: int, last: int, out: Path) -> int:
    import pymupdf  # chỉ cần cho cuốn có bản dịch in trong PDF

    out.mkdir(parents=True, exist_ok=True)
    n = 0
    with pymupdf.open(pdf) as doc:
        for i in range(first - 1, min(last, doc.page_count)):
            doc[i].get_pixmap(dpi=150).save(out / f"pdf_{i + 1:03d}.png")
            n += 1
    return n


def build_student(sv: dict, recs: dict, catalog: dict, ft: Path, root: Path) -> dict:
    base = root / sv["slug"]
    summary = {"ho_ten": sv["ho_ten"], "viec": [], "kich_thuoc": 0}
    b0 = []
    for kind in ("soat", "ocr", "dich_may"):
        for doc_id in sv.get(kind, []):
            rec = recs[doc_id]
            out = base / kind / doc_id
            out.mkdir(parents=True, exist_ok=True)
            images, size = page_images(rec, ft, out)
            item = {"loai": kind, "doc_id": doc_id, "ten": title(rec), "trang": len(rec["pages"]), "anh": len(images)}
            if kind == "soat":
                item["cap_cau"] = write_pairs(rec, out, sv["slug"])
                page_context(rec, out)
            elif kind == "dich_may":
                page_context(rec, out)
            if kind != "ocr":
                item["khung_raw"] = write_raw_ppocr(rec, catalog.get(doc_id), ft, images, out)
                if (out / "crop_img").exists():
                    size += sum(f.stat().st_size for f in (out / "crop_img").iterdir())
            summary["viec"].append(item)
            summary["kich_thuoc"] += size
            b0.append({"doc_id": doc_id, "ten": title(rec), "viec": TITLES[kind], "so_trang_du_kien": len(rec["pages"])})
    for spec in sv.get("dich_nguoi", []):
        out = base / "dich_nguoi" / spec["doc_id"]
        out.mkdir(parents=True, exist_ok=True)
        item = {"loai": "dich_nguoi", "doc_id": spec["doc_id"], "ten": spec["ten"]}
        rec = recs.get(spec["doc_id"])
        if rec and rec["pages"]:  # Track 3 (chỉ có bản Việt) chưa có trang nào để ghép
            images, size = page_images(rec, ft, out)
            item["anh"] = len(images)
            item["cap_cau"] = write_pairs(rec, out, sv["slug"])
            page_context(rec, out)
            item["khung_raw"] = write_raw_ppocr(rec, catalog.get(spec["doc_id"]), ft, images, out)
            summary["kich_thuoc"] += size
        for rel in spec.get("tep_local", []):
            src = ft / rel
            if src.exists():
                shutil.copy2(src, out / src.name)
                summary["kich_thuoc"] += src.stat().st_size
        if spec.get("pdf_local"):
            a, b = spec["trang_ban_dich_pdf"]
            item["trang_ban_dich"] = render_pdf_pages(ft / spec["pdf_local"], a, b, out / "anh_ban_dich")
            summary["kich_thuoc"] += sum(p.stat().st_size for p in (out / "anh_ban_dich").iterdir())
        if spec.get("cho_windows"):
            (out / "CHO_DU_LIEU.md").write_text(
                f"# {spec['ten']}\n\nPhần này còn nằm trên máy Windows của lab: `{spec['cho_windows']}`.\n"
                "Sẽ gửi bổ sung khi được phép chép ra. Trong lúc chờ, làm các phần khác trước.\n", encoding="utf-8")
            item["cho_windows"] = spec["cho_windows"]
        summary["viec"].append(item)
        b0.append({"doc_id": spec["doc_id"], "ten": spec["ten"], "viec": TITLES["dich_nguoi"],
                   "so_trang_du_kien": (len(rec["pages"]) if rec else "")})
    with (base / "phieu_B0.csv").open("w", encoding="utf-8-sig", newline="") as f:
        w = csv.DictWriter(f, fieldnames=B0_COLS)
        w.writeheader()
        w.writerows(b0)
    (base / "README.md").write_text(student_readme(sv, summary), encoding="utf-8")
    return summary


def student_readme(sv: dict, s: dict) -> str:
    lines = [f"# Phần việc của {sv['ho_ten']}", "",
             "Đọc `../HUONG_DAN.md` trước. Điền `phieu_B0.csv` cho mọi cuốn trước khi bắt đầu.", "",
             "| Việc | doc_id | Tên | Trang | Ảnh | Cặp câu | Khung raw |", "|---|---|---|--:|--:|--:|--:|"]
    for it in s["viec"]:
        lines.append(f"| {TITLES[it['loai']]} | `{it['doc_id']}` | {it['ten']} | {it.get('trang', '')} | "
                     f"{it.get('anh', '')} | {it.get('cap_cau', '')} | {it.get('khung_raw') or ''} |")
    boxes = sum(it.get("khung_raw", 0) for it in s["viec"])
    lines += ["", f"Tổng khung chữ có sẵn trong `raw/`: {boxes}. Cách sửa thành `final/`: xem mục PPOCRLabel trong `HUONG_DAN.md`."]
    waits = [it for it in s["viec"] if it.get("cho_windows")]
    if waits:
        lines += ["", "Chờ dữ liệu từ máy Windows: " + ", ".join(f"`{it['doc_id']}`" for it in waits) + "."]
    return "\n".join(lines) + "\n"


GUIDE = """# Hướng dẫn chung — {de_tai}

Đợt giao: {dot}. Căn cứ: biên bản họp 26/10/2026.

## Quy trình mỗi cuốn
- **B0** Điền `phieu_B0.csv`: dạng tư liệu, số trang thật, có bản dịch hay phiên âm không, chất lượng ảnh, trang thiếu hoặc trùng.
- **B1** `ocr/`: chạy OCR nhiều công cụ có bỏ phiếu của lab, rồi soát nhanh trang có nhiều ký tự không chắc. Chỉ chạy khi đã được cấp quyền và hạn mức.
- **B2** `dich_may/`: đã có chữ Hán, cần dịch máy, sau đó soát như B3.
- **B3** `soat/`: mở `cap_cau.csv` (Excel hoặc Google Sheets). Mỗi dòng là một cặp câu Hán – bản dịch máy. Đối chiếu với ảnh trong `anh/` và ngữ cảnh trong `trang.jsonl`.
  - Bản dịch đúng: để trống `viet_sua`, đặt `trang_thai` = `da_soat`.
  - Bản dịch sai hoặc thiếu: ghi bản đúng vào `viet_sua`, đặt `trang_thai` = `da_soat`.
  - Câu ghép sai (một câu Hán bị cắt đôi, hai câu bị gộp): ghi vào `ghi_chu`, đặt `trang_thai` = `lech_nghia`.
  - Không chắc nghĩa: đặt `trang_thai` = `can_hoi`, không tự đoán.
- **B4** `dich_nguoi/`: ghép câu Hán với câu trong bản dịch người (không phải bản dịch máy). Ghi `nguon_dich` = `nguoi`.

## Khung chữ và ảnh crop: raw/ → final/ (định dạng PPOCRLabel)
Cuốn nào đã có khung chữ Paddle thì thư mục cuốn có sẵn:
- `raw/Label.txt`: khung tự động, mỗi dòng `anh/<trang>.jpg<TAB>[{{"transcription": ..., "points": [[x,y]×4], "difficult": false}}, ...]`, xếp theo thứ tự đọc (cột phải sang trái, trong cột trên xuống dưới). Toạ độ tính trên ảnh trong `anh/`.
- `raw/rec_gt.txt`: `crop_img/<trang>_crop_<i>.jpg<TAB><chữ OCR>`.
- `crop_img/`: mỗi khung một ảnh; cột chữ dọc đã được xoay 90° giống cách PPOCRLabel tự cắt.
- `raw/fileState.txt` để trống: chưa trang nào được người xác nhận.

Lưu ý: chữ trong `raw/` là chữ do riêng Paddle nhận dạng, có cột sai nặng (ví dụ ra toàn chữ giản thể vô nghĩa). Khi sửa chữ, đối chiếu ảnh với chữ đã bỏ phiếu giữa nhiều công cụ trong `trang.jsonl` (trường `han`), thường đúng hơn. Khung trùng với dấu thư viện, số trang (ví dụ `R.42`, `-57-`) thì xoá.

Cách làm:
1. Chép `raw/Label.txt` vào thư mục `anh/`, mở `anh/` bằng PPOCRLabel (https://github.com/PFCCLab/PPOCRLabel).
2. Sửa khung: thẳng, sát chữ, không thừa nền, không cắt thiếu chữ, mỗi cột (dòng) một khung, không bỏ sót cột.
3. Sửa chữ: chép đúng chữ trên ảnh, giữ chữ dị thể, không đổi sang giản thể, không "sửa lỗi" của bản gốc.
4. Xác nhận từng trang, rồi xuất kết quả nhận dạng (Export Recognition Result).
5. Chép `Label.txt`, `fileState.txt`, `rec_gt.txt` mới vào `final/`, ảnh crop mới vào `final_crop/`. **Không sửa gì trong `raw/`** để còn đo độ chính xác của OCR tự động.
Cuốn chưa có khung (thư mục `ocr/` và vài cuốn khác) thì tự tạo khung bằng PPOCRLabel sau khi OCR, rồi làm tiếp như trên.

## Nộp lại
- `phieu_B0.csv` đã điền, và mỗi cuốn một tệp `cap_cau.csv` đã soát (giữ nguyên cột `id`).
- Khoảng 5% số trang sẽ được một bạn khác soát lại để đo độ đồng thuận.

## Quy tắc
- Không đưa ảnh, PDF hay dữ liệu này lên mạng công khai hoặc git.
- OCR và dịch máy dùng hạn mức của lab; hết hạn mức thì dừng và báo.
- Giữ đúng `doc_id`; không tự đặt mã định danh F.
"""


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--config", type=Path, required=True)
    ap.add_argument("--family-tree", type=Path, required=True, help="checkout family-tree có thư mục data/")
    ap.add_argument("--out", type=Path, default=None)
    ap.add_argument("--zip", action="store_true", help="nén mỗi sinh viên thành một tệp .zip")
    args = ap.parse_args()

    cfg = json.loads(args.config.read_text(encoding="utf-8"))
    ft = args.family_tree.resolve()
    root = (args.out or ft / "data" / "05_ops" / "ban_giao" / cfg["dot"]).resolve()
    if root.exists():
        shutil.rmtree(root)
    root.mkdir(parents=True)
    recs = load_records()
    catalog = {b["book_id"]: b for b in json.loads(
        (ft / "data/00_raw/hannom/books_catalog.json").read_text(encoding="utf-8")).get("books") or []}
    missing = [d for sv in cfg["sinh_vien"] for k in ("soat", "ocr", "dich_may") for d in sv.get(k, []) if d not in recs]
    if missing:
        sys.exit(f"Không có record cho: {missing}")

    (root / "HUONG_DAN.md").write_text(GUIDE.format(**cfg), encoding="utf-8")
    report = {}
    for sv in cfg["sinh_vien"]:
        s = build_student(sv, recs, catalog, ft, root)
        shutil.copy2(root / "HUONG_DAN.md", root / sv["slug"] / "HUONG_DAN.md")
        if args.zip:
            shutil.make_archive(str(root / sv["slug"]), "zip", root, sv["slug"])
            s["zip"] = (root / f"{sv['slug']}.zip").stat().st_size
        report[sv["slug"]] = s
    (root / "tong_hop.json").write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    for slug, s in report.items():
        pages = sum(it.get("trang", 0) or 0 for it in s["viec"])
        pairs = sum(it.get("cap_cau", 0) for it in s["viec"])
        boxes = sum(it.get("khung_raw", 0) for it in s["viec"])
        z = f", zip {s['zip'] / 1e6:.0f} MB" if "zip" in s else ""
        print(f"{slug}: {pages} trang, {pairs} cặp câu, {boxes} khung raw, {s['kich_thuoc'] / 1e6:.0f} MB{z}")
    print(f"Đã ghi: {root}")


if __name__ == "__main__":
    main()
