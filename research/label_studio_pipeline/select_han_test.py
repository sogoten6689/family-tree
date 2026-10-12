"""Chọn tập TEST nhỏ (mặc định 15 trang) từ nhãn máy Hán để NGƯỜI soát tay làm chân trị.

Nguyên tắc: mỗi sách tối đa 1 trang (đại diện nhiều sách); loại trang có ký tự ngoài BMP (tránh rủi ro lệch offset
UTF-16/code point khi nhập Label Studio); trang phải đủ thực thể và có tên người; chọn trang có số thực thể gần mức
trung vị (đại diện độ khó thường gặp, không chọn trang dễ nhất). Xác định, không ngẫu nhiên.

Đầu ra (thư mục mới):
  tasks.json     — nhiệm vụ Label Studio (có predictions của máy) để người soát sửa
  held_out.json  — danh sách doc_id TUYỆT ĐỐI không dùng để huấn luyện
  manifest.csv   — trang nào, của tài liệu nào trên web (scan_id), số thực thể máy gán
  HUONG_DAN_SOAT.md — hướng dẫn soát ngắn

    python -m label_studio_pipeline.select_han_test --gold-dir <han_llm_trial/gold> --out <dir> [--n 15]
"""
from __future__ import annotations

import argparse
import csv
import json
import statistics
from pathlib import Path
from typing import Any, Dict, List

from label_studio_pipeline.build_han_pilot import has_non_bmp
from label_studio_pipeline.han_llm_prelabel import to_ls_task

GUIDE = """# Hướng dẫn soát tập test Hán ({n} trang)

Mục đích: tạo **chân trị do người soát** để đo model thật sự tốt đến đâu. Nhãn đang có là nhãn MÁY (Gemini), chưa đúng hết.

1. Label Studio → dự án Hán (cùng bộ nhãn PER_NAME, GENERATION, DATE, ORDER, LOC) → Import `tasks.json`.
2. Mỗi trang đã có nhãn máy sẵn. Việc của người soát: **xoá nhãn sai, sửa ranh giới, thêm nhãn bị sót**, rồi Submit.
3. Quy tắc (đề xuất, chưa được thầy duyệt): hậu tố 公/氏 nằm trong PER_NAME; chức tước đứng trước tên KHÔNG gán;
   ngày âm lịch không năm và ngày giỗ gán DATE; không quy đổi dương lịch.
4. Ảnh gốc của trang xem ở web: mở tài liệu theo `scan_id` trong `manifest.csv` (tab Trang) để đối chiếu khi chữ OCR nghi sai.
5. Quan hệ (FATHER_OF/MOTHER_OF/SPOUSE) chỉ ghi khi văn bản nói rõ; không chắc thì bỏ. Văn bản OCR có thể bị xáo thứ tự dòng.
6. Ghi lại số phút soát mỗi trang (để ước thời gian gán nhãn cho cả kho).
7. Xuất JSON sau khi soát và đặt vào `han_test_v1/reviewed/`. **Không dùng các trang này để huấn luyện.**
"""


def eligible(doc: Dict[str, Any], min_entities: int = 8) -> bool:
    ents = doc["entities"]
    return (
        not has_non_bmp(doc["text"])
        and len(ents) >= min_entities
        and any(e["label"] == "PER_NAME" for e in ents)
    )


def select(docs: List[Dict[str, Any]], n: int = 15) -> List[Dict[str, Any]]:
    pool = [d for d in docs if eligible(d)]
    if not pool:
        return []
    median = statistics.median(len(d["entities"]) for d in pool)
    best: Dict[Any, Dict[str, Any]] = {}
    for d in pool:
        sid = d["provenance"]["scan_id"]
        key = (abs(len(d["entities"]) - median), d["doc_id"])
        if sid not in best or key < (abs(len(best[sid]["entities"]) - median), best[sid]["doc_id"]):
            best[sid] = d
    # Mỗi sách một trang; nếu nhiều sách hơn n, giữ n sách có trang gần trung vị nhất.
    ranked = sorted(best.values(), key=lambda d: (abs(len(d["entities"]) - median), d["doc_id"]))[:n]
    return sorted(ranked, key=lambda d: d["doc_id"])


def run(gold_dir: Path, out_dir: Path, n: int = 15) -> Dict[str, Any]:
    docs = [json.loads(p.read_text(encoding="utf-8")) for p in sorted(gold_dir.glob("*.json"))]
    chosen = select(docs, n)
    out_dir.mkdir(parents=True, exist_ok=True)
    (out_dir / "tasks.json").write_text(json.dumps([to_ls_task(d) for d in chosen], ensure_ascii=False, indent=1), encoding="utf-8")
    (out_dir / "held_out.json").write_text(json.dumps([d["doc_id"] for d in chosen], ensure_ascii=False, indent=1), encoding="utf-8")
    with (out_dir / "manifest.csv").open("w", encoding="utf-8", newline="") as fh:
        writer = csv.writer(fh)
        writer.writerow(["doc_id", "scan_id", "page_number", "han_chars", "machine_entities", "machine_relations"])
        for d in chosen:
            p = d["provenance"]
            writer.writerow([d["doc_id"], p["scan_id"], p["page_number"], len(d["text"]), len(d["entities"]), len(d["relations"])])
    (out_dir / "HUONG_DAN_SOAT.md").write_text(GUIDE.format(n=len(chosen)), encoding="utf-8")
    return {"pages": len(chosen), "docs": len({d["provenance"]["scan_id"] for d in chosen}), "machine_entities": sum(len(d["entities"]) for d in chosen), "han_chars": sum(len(d["text"]) for d in chosen)}


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--gold-dir", type=Path, required=True)
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument("--n", type=int, default=15)
    args = parser.parse_args()
    print(json.dumps(run(args.gold_dir, args.out, args.n), ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
