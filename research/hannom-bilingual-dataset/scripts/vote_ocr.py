#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Vote + mix OCR N engine (tối đa 5: kim_hannom_lab (=CLC), paddle_v6, deepseek,
google_vision, gemini) cho 1 trang của 1 cuốn trong
family-tree/data/00_raw/hannom/books_catalog.json.

Mở rộng 4 lần từ family-tree/nlp_family_extractor/tools/mix_hannom.py:
  (1) 2 engine cố định -> N engine (bản đầu, 2026-09-08 sáng)
  (2) "đối chiếu theo dòng, luôn giữ nguyên backbone" -> VOTE THẬT Ở MỨC KÝ TỰ
      (2026-09-08 chiều) — vì OCR không chính xác hoàn toàn, chỉ tin 1 engine
      (dù đã chọn kỹ) vẫn mang lỗi của riêng engine đó đi tiếp.
  (3) VOTE KÝ TỰ -> VOTE CẢ CÂU BẰNG LEVENSHTEIN MED THẬT (2026-09-14, theo
      yêu cầu họp) — vote ký tự dùng difflib.SequenceMatcher
      (Ratcliff/Obershelp), không phải Levenshtein/Minimum-Edit-Distance thật,
      nên mọi đoạn `insert`/`delete`/`replace` lệch độ dài đều BỊ BỎ QUA không
      vote (chỉ ghi `structural_diffs`) — đúng chỗ hổng thầy chỉ ra.
  (4) LUÔN ĐẢM BẢO SỐ TOOL THAM GIA VOTE LÀ SỐ LẺ (2026-09-15, theo yêu cầu
      "luôn chạy đủ lẻ tool để vote") — 5 tool vẫn luôn được GỌI hết, nhưng nếu
      1 tool lỗi/hết quota khiến số tool THÀNH CÔNG cho 1 trang bị chẵn, tự
      động loại engine ưu tiên THẤP NHẤT trong số đang có khỏi vòng vote (vẫn
      giữ nguyên text thô của nó trong `engines` — không mất dữ liệu, chỉ
      không cho nó "bỏ phiếu"). Xem PHÂN TÍCH bên dưới.
  (5) FALLBACK VOTE THEO TỪNG VỊ TRÍ KHI CẢ CÂU KHÔNG ĐỦ ĐA SỐ (2026-09-17,
      theo phân tích thật khi rà lại thuật toán) — vote CÂU (mục 3) chọn
      NGUYÊN 1 dòng thắng cuộc, nên nếu mỗi engine chỉ sai ở 1 CHỖ KHÁC NHAU
      trong cùng 1 câu (vd. engine A thiếu 1 chữ ở giữa câu, engine B thừa 1
      chữ ở chỗ khác), không dòng nào đủ giống dòng nào để tạo đa số — có khi
      còn tệ hơn: 2 engine tình cờ giống nhau ở đúng chỗ SAI (cùng thiếu 1
      chữ) lại bị tính là "đa số" (`line_confirmed_majority`) trong khi 3
      engine khác đọc ĐÚNG đúng chữ đó nhưng mỗi engine lại sai 1 chỗ khác
      nên nhìn CẢ DÒNG thì không giống nhau. `vote_line_positional()` sửa
      việc này: căn TỪNG engine khác vào đúng vị trí ký tự của backbone bằng
      `Levenshtein.editops()` thật (khác difflib ở mục (3): xử lý được cả
      chèn/xoá lệch độ dài, không bỏ qua), rồi vote riêng từng vị trí/khe hở
      theo ĐÚNG luật gốc trong CLAUDE.md của repo này — chỉ tự sửa khi ≥3
      engine đồng thuận tại đúng 1 vị trí. Chỉ chạy fallback này cho dòng mà
      vote CÂU (mục 3) chưa cho kết quả rõ ràng (`line_no_majority` hoặc
      `line_confirmed_majority`) — dòng đã `line_unanimous`/
      `line_majority_override` không chạy lại, giữ nguyên hành vi cũ.

## Vì sao cần vote — không chỉ đối chiếu dòng rồi tin 1 engine

Test thật trên gpc-dang-1928 trang 1 (lab vs paddle, xem README §Phân tích OCR):
6 dòng, similarity theo dòng dao động 0.82–1.00 (trung bình ~0.90) — tức ~10%
ký tự lệch nhau ngay cả ở trang OCR "tốt". Ví dụ dòng 5: lab đọc `欤` (trợ từ
nghi vấn — khớp đúng ngữ pháp câu "khởi bất vĩ dư!" trong bản dịch nghĩa đã có),
paddle đọc `欣` (vui mừng — sai nghĩa hoàn toàn, dù nhìn gần giống mặt chữ). Nếu
`mix_hannom.py` cũ chỉ ghi similarity=0.88 vào file ghi chú riêng, người OCR vẫn
nhận nguyên `voted_text` = backbone, KHÔNG có tín hiệu nào ở ngay trong text chính
báo "chỗ này có 2 engine bất đồng, tự kiểm tra".

## Thuật toán vote CÂU bằng Levenshtein MED (từ 2026-09-14, generalize N=2..5)

Đơn vị vote đổi từ KÝ TỰ sang CÂU/DÒNG (đúng yêu cầu họp: "bắt buộc vote từ
câu, nếu dùng câu để nói câu") — không còn ghép Frankenstein ký tự của nhiều
engine vào 1 dòng, mà chọn NGUYÊN 1 dòng thắng cuộc. Dùng `rapidfuzz.distance.
Levenshtein` (Minimum Edit Distance thật — insert/delete/replace có chi phí
tường minh) thay `difflib.SequenceMatcher` ở cả 2 chỗ:

Với mỗi dòng của engine backbone (mặc định kim_hannom_lab):
  1. `best_match()`: với MỖI engine khác, tìm dòng khớp nhất bằng
     `Levenshtein.normalized_similarity` (0..1) thay vì difflib ratio — cùng
     là "độ giống", nhưng Levenshtein đo đúng số phép sửa tối thiểu, không phải
     heuristic khối khớp dài nhất.
  2. `vote_line()`: gom {backbone + các dòng khớp nhất từ engine khác} thành
     các CỤM — 2 dòng vào cùng cụm nếu `normalized_similarity >= SIM_MATCH`
     (0.92, coi như "cùng 1 câu", sai khác nhỏ do OCR). Việc gom cụm này chính
     là bước "nối 2 thằng lại giống hàng" bằng Levenshtein mà không cần quan
     tâm 2 dòng có lệch độ dài hay không — khác hẳn vote ký tự cũ (chỉ vote
     được `replace` CÙNG độ dài, bỏ qua insert/delete/replace lệch độ dài).
  3. Cụm nào có NHIỀU ENGINE ĐỒNG Ý HƠN cụm chứa backbone thì THẮNG (đa số thật
     sự — same nguyên tắc an toàn như bản ký tự cũ: đúng 2 engine chỉ hoà 1-1,
     KHÔNG BAO GIỜ tự ghi đè; cần ≥3 engine mới có đa số thật). Trong cụm thắng
     có >1 dòng hơi khác nhau (dưới ngưỡng nhưng chưa giống hệt), chọn dòng
     "trung tâm" nhất (medoid — tổng khoảng cách Levenshtein tới các dòng còn
     lại trong cụm nhỏ nhất) làm `voted_line`.
  4. Mọi dòng có >1 cụm (tức có engine bất đồng thật, không unanimous) được
     liệt kê vào `uncertain_spans` — mỗi bản ghi giờ ở CẤP DÒNG (`line`,
     `method`, `voted_line`, `n_agree`/`n_total`, `disagreeing`: danh sách
     engine + dòng của họ + độ giống với dòng thắng) thay vì cấp ký tự
     (`pos`, `backbone`, `resolved`, `votes`).

`structural_diffs` giữ lại trong schema để tương thích ngược với record đã vote
kiểu cũ, nhưng từ bản này LUÔN RỖNG `[]` — vì vote câu không còn khái niệm
"đoạn lệch độ dài không vote được", Levenshtein MED xử lý được mọi trường hợp
insert/delete/replace ngay trong bước gom cụm.

Engine chưa có key tự trả None ở adapter -> bị bỏ qua, không lỗi, không chặn
các engine đang chạy được.

## Vì sao số tool tham gia vote phải luôn LẺ (từ 2026-09-15)

Nguyên tắc gốc (mục 3 ở trên): cụm khác chỉ được ghi đè backbone khi có SỐ
ENGINE ĐỒNG Ý NHIỀU HƠN cụm chứa backbone — tổng số "phiếu" chẵn (vd. 4: 2 cụm
2-2) có thể tạo ra tình huống 2 cụm bằng nhau mà không cụm nào áp đảo, buộc
phải hoà, giống hệt rủi ro "2 engine hoà 1-1" ban đầu nhưng ở quy mô lớn hơn.
Tổng số phiếu LẺ (1, 3, 5) không loại bỏ hoàn toàn khả năng nhiều cụm hoà nhau
(vd. 5 phiếu chia 2-2-1), nhưng đảm bảo KHÔNG BAO GIỜ đúng 2 cụm ngang nhau
chiếm hết phiếu — luôn còn dư ít nhất 1 phiếu ở đâu đó, giảm hẳn rủi ro so với
số chẵn.

Cách đảm bảo: `vote_page()` tính `other_names` (engine khác backbone thật sự
CÓ dữ liệu cho trang này). Nếu `len(other_names)` LẺ (=> tổng LUÔN backbone +
other_names là CHẴN), loại 1 engine — chọn theo `priority.index()`, tức engine
đứng CUỐI trong `DEFAULT_PRIORITY` (ưu tiên thấp nhất, tin cậy thấp nhất theo
thứ tự đã chốt) — khỏi `other_names` trước khi vào vòng vote từng dòng. Engine
bị loại VẪN xuất hiện đầy đủ trong `engines{}` của kết quả (không mất text thô,
chỉ không được tính khi vote), và bị ghi rõ vào `vote_method` (hậu tố
`_excl_<engine>_for_odd`) để không âm thầm mất dấu vết.

**Trường hợp biên cần biết:** đúng 2 engine có dữ liệu (`other_names` có 1
phần tử, LẺ) -> loại nốt engine còn lại -> chỉ còn backbone MỘT MÌNH bỏ phiếu.
Khác với bản trước (2 engine vẫn được SO SÁNH, chỉ không override, và bất đồng
1-1 vẫn hiện trong `uncertain_spans` để người soát biết) — từ bản này, trang
chỉ có 2 engine sẽ KHÔNG còn thấy bất đồng đó trong `uncertain_spans` nữa (vì
engine thứ 2 bị loại trước khi so sánh từng dòng). Đây là đánh đổi có chủ đích
theo đúng yêu cầu "luôn đủ lẻ" — nếu cần vẫn thấy bất đồng 1-1 để soát tay, đọc
trực tiếp `engines{}` (luôn đủ, không bị lọc).

Lưu ý: nguyên tắc lẻ áp dụng ở CẤP TRANG (tập engine được PHÉP vote cho cả
trang). Ở CẤP TỪNG DÒNG, `n_total` trong `vote_line()` vẫn có thể chẵn nếu 1
trong số engine được phép vote không có dòng khớp đủ (`SIM_NOTE_MIN`) cho đúng
vị trí dòng đó — không thể ép lẻ ở mức này mà không có rủi ro ghép sai dòng.

Dùng:
  python scripts/vote_ocr.py --book gpc-dang-1928 --pages 0,1,2
  python scripts/vote_ocr.py --book gpc-dang-1928 --pages 0 --priority paddle_v6,kim_hannom_lab
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

from rapidfuzz.distance import Levenshtein

from ocr_adapters import base as _base  # noqa: F401  (đảm bảo package import được)
from ocr_adapters import deepseek, gemini, google_vision, kim_hannom_lab, paddle_v6
from _repo_paths import FAMILY_TREE

ROOT = Path(__file__).resolve().parents[1]

# Đúng 5 tool đã họp: Paddle v6, Kim Hán Nôm Lab (= "CLC" trong tên gọi cũ ở họp —
# XÁC NHẬN 2026-09-08: 2 tên chỉ 1 dịch vụ, không phải 2 engine khác nhau), DeepSeek,
# Google Vision, Gemini.
ADAPTERS = {
    "kim_hannom_lab": kim_hannom_lab,
    "paddle_v6": paddle_v6,
    "deepseek": deepseek,
    "google_vision": google_vision,
    "gemini": gemini,
}
DEFAULT_PRIORITY = ["kim_hannom_lab", "paddle_v6", "deepseek", "google_vision", "gemini"]
SIM_MATCH = 0.92
SIM_NOTE_MIN = 0.30


def vote_line(backbone_name: str, backbone_line: str, other_lines: dict[str, str]) -> dict[str, Any]:
    """Vote CẢ DÒNG (câu) giữa backbone_line và mỗi dòng khớp nhất từ engine khác
    (other_lines, đã chọn sẵn bằng best_match). Dùng Levenshtein MED thật để gom
    dòng "cùng câu" (kể cả lệch độ dài do insert/delete/replace) vào 1 cụm, cụm
    nào nhiều engine đồng ý hơn cụm chứa backbone thì thắng (đa số thật sự — xem
    docstring đầu file). Trả {"voted_line", "method", "n_agree", "n_total",
    "disagreeing"}.
    """
    candidates: list[tuple[str, str]] = [(backbone_name, backbone_line), *other_lines.items()]
    clusters: list[list[tuple[str, str]]] = []
    for name, text in candidates:
        for cluster in clusters:
            if Levenshtein.normalized_similarity(text, cluster[0][1]) >= SIM_MATCH:
                cluster.append((name, text))
                break
        else:
            clusters.append([(name, text)])

    backbone_cluster = next(c for c in clusters if any(n == backbone_name for n, _ in c))
    best_cluster = max(clusters, key=len)

    if len(best_cluster) > len(backbone_cluster):
        winner_cluster, method = best_cluster, "line_majority_override"
    elif len(clusters) == 1:
        winner_cluster, method = backbone_cluster, "line_unanimous"
    elif len(backbone_cluster) > 1:
        winner_cluster, method = backbone_cluster, "line_confirmed_majority"
    else:
        winner_cluster, method = backbone_cluster, "line_no_majority"

    if len(winner_cluster) == 1:
        voted_line = winner_cluster[0][1]
    else:
        # medoid: dòng có tổng khoảng cách Levenshtein tới các dòng còn lại trong cụm nhỏ nhất
        voted_line = min(
            (text for _, text in winner_cluster),
            key=lambda t: sum(Levenshtein.distance(t, other) for _, other in winner_cluster),
        )

    winner_names = {n for n, _ in winner_cluster}
    disagreeing = [
        {"engine": name, "text": text,
         "similarity": round(Levenshtein.normalized_similarity(text, voted_line), 4)}
        for name, text in candidates if name not in winner_names
    ]

    return {"voted_line": voted_line, "method": method, "n_agree": len(winner_cluster),
            "n_total": len(candidates), "disagreeing": disagreeing}


def vote_line_positional(backbone_name: str, backbone_line: str, other_lines: dict[str, str],
                          min_majority: int = 3) -> dict[str, Any]:
    """Fallback dùng khi `vote_line()` không cho kết quả rõ ràng cho cả dòng
    (`line_no_majority` hoặc `line_confirmed_majority` — xem mục (5) docstring
    đầu file). Căn TỪNG engine khác vào đúng vị trí ký tự của backbone bằng
    `Levenshtein.editops()` thật (star alignment lấy backbone làm tâm — không
    phải multiple sequence alignment đầy đủ giữa các engine với nhau, đơn
    giản hơn nhưng đủ dùng vì mọi so sánh đều quy về cùng 1 toạ độ backbone),
    rồi vote riêng từng VỊ TRÍ ký tự và từng KHE HỞ (chỗ có thể bị chèn thêm)
    — đúng luật gốc CLAUDE.md: chỉ tự sửa khi ≥`min_majority` engine (tính cả
    backbone tự "bỏ phiếu" giữ nguyên chữ của mình) đồng thuận tại ĐÚNG 1 vị
    trí/khe hở đó; còn lại giữ nguyên chữ backbone và ghi vào
    `uncertain_positions` để người soát biết chính xác ký tự nào còn treo
    (khác vote CÂU cũ — chỉ biết "cả dòng có vấn đề", không biết đúng chỗ nào).

    `editops(backbone_line, other_line)` cho từng engine độc lập (không so
    engine khác với nhau) — mỗi `replace`/`delete` gắn với 1 vị trí ký tự
    trong backbone (`src_pos`), mỗi `insert` gắn với 1 khe hở TRƯỚC vị trí đó.
    Nhiều `insert` liên tiếp cùng khe hở được gộp thành 1 cụm theo đúng thứ tự
    trong dòng gốc của engine đó, rồi vote TỪNG KÝ TỰ trong cụm theo vị trí
    thứ tự của nó (ký tự đầu cụm của engine này so với ký tự đầu cụm của
    engine khác, ký tự thứ 2 so ký tự thứ 2...) — KHÔNG vote cả cụm như 1
    khối. Lý do: nếu vote cả cụm, 1 engine đọc dư thêm 1 ký tự lạ ngay sau
    ký tự đúng (vd. đọc đúng "C" nhưng thêm "?" ngay sau) sẽ làm cụm của nó
    ("C?") không khớp CHÍNH XÁC với cụm chỉ có "C" của các engine khác, làm
    phiếu cho "C" bị tách ra và mất đa số dù thực ra đa số engine đều đồng ý
    "C" — XÁC NHẬN bằng test offline 2026-09-17 (backbone thiếu "C", 1 engine
    đọc dư thêm ký tự lạ ngay sau "C", 2 engine khác đọc "C" y hệt: vote theo
    cụm cho `line_no_majority` liên tục ở khe đó dù 3/5 tổng thể đồng ý "C";
    vote theo từng ký tự trong cụm khắc phục đúng chỗ này).
    """
    n = len(backbone_line)
    position_votes: dict[int, dict[str, list[str]]] = {i: {"__keep__": [backbone_name]} for i in range(n)}
    insert_run_by_gap: dict[int, dict[str, str]] = {i: {} for i in range(n + 1)}

    for name, line in other_lines.items():
        ops = Levenshtein.editops(backbone_line, line)
        touched_positions: set[int] = set()
        for op in sorted(ops, key=lambda o: (o.src_pos, o.dest_pos)):
            if op.tag == "replace":
                touched_positions.add(op.src_pos)
                position_votes[op.src_pos].setdefault(line[op.dest_pos], []).append(name)
            elif op.tag == "delete":
                touched_positions.add(op.src_pos)
                position_votes[op.src_pos].setdefault("__delete__", []).append(name)
            elif op.tag == "insert":
                gap = insert_run_by_gap[op.src_pos]
                gap[name] = gap.get(name, "") + line[op.dest_pos]
        for i in range(n):
            if i not in touched_positions:
                position_votes[i]["__keep__"].append(name)

    result_parts: list[str] = []
    uncertain_positions: list[dict[str, Any]] = []

    for i in range(n + 1):
        runs_by_engine = insert_run_by_gap[i]
        max_len = max((len(r) for r in runs_by_engine.values()), default=0)
        for j in range(max_len):
            sub_votes: dict[str, list[str]] = {"": [backbone_name]}
            for name, run in runs_by_engine.items():
                val = run[j] if j < len(run) else ""
                sub_votes.setdefault(val, []).append(name)
            for name in other_lines:
                if name not in runs_by_engine:
                    sub_votes[""].append(name)
            best_value, best_voters = max(sub_votes.items(), key=lambda kv: len(kv[1]))
            if best_value != "" and len(best_voters) >= min_majority:
                result_parts.append(best_value)
                uncertain_positions.append({"gap_before": i, "insert_index": j, "resolved": best_value,
                                             "method": "gap_majority_override", "votes": sub_votes})
            elif len(sub_votes) > 1:
                uncertain_positions.append({"gap_before": i, "insert_index": j, "resolved": None,
                                             "method": "gap_no_majority", "votes": sub_votes})

        if i == n:
            break
        pvotes = position_votes[i]
        pbest_value, pbest_voters = max(pvotes.items(), key=lambda kv: len(kv[1]))
        if pbest_value != "__keep__" and len(pbest_voters) >= min_majority:
            if pbest_value != "__delete__":
                result_parts.append(pbest_value)
            uncertain_positions.append({"backbone_pos": i, "backbone_char": backbone_line[i],
                                         "resolved": None if pbest_value == "__delete__" else pbest_value,
                                         "method": "position_majority_override", "votes": pvotes})
        else:
            result_parts.append(backbone_line[i])
            if len(pvotes) > 1:
                uncertain_positions.append({"backbone_pos": i, "backbone_char": backbone_line[i],
                                             "resolved": None, "method": "position_no_majority", "votes": pvotes})

    return {"voted_line": "".join(result_parts), "n_total": 1 + len(other_lines),
            "uncertain_positions": uncertain_positions}


def load_catalog() -> dict[str, dict[str, Any]]:
    path = FAMILY_TREE / "data/00_raw/hannom/books_catalog.json"
    books = json.loads(path.read_text(encoding="utf-8")).get("books") or []
    return {b["book_id"]: b for b in books}


def best_match(line: str, candidates: list[str]) -> tuple[str | None, float]:
    """Tìm dòng khớp nhất bằng Levenshtein normalized_similarity (0..1) — thay
    difflib.SequenceMatcher.ratio() (Ratcliff/Obershelp) bằng MED thật, đúng yêu
    cầu họp 14/09: "trước khi so sánh, dùng Levenshtein nối 2 thằng lại giống hàng".
    """
    best_text, best_sim = None, 0.0
    for c in candidates:
        sim = Levenshtein.normalized_similarity(line, c)
        if sim > best_sim:
            best_text, best_sim = c, sim
    return best_text, best_sim


def _bag_of_lines_similarity(lines_a: list[str], lines_b: list[str]) -> float:
    """Độ giống giữa 2 TẬP dòng, KHÔNG phụ thuộc thứ tự — trung bình 2 chiều của
    best_match() từng dòng bên này so với TOÀN BỘ dòng bên kia.

    XÁC NHẬN 2026-09-15, phát hiện khi kiểm chứng rank_by_similarity() bằng dữ
    liệu thật: bản đầu so 2 CHUỖI ĐÃ NỐI LIỀN THEO ĐÚNG THỨ TỰ dòng gốc — sai ở
    trang nom-1255/001, nơi paddle_v6 đọc đúng 8 dòng THEO THỨ TỰ HOÀN TOÀN
    NGƯỢC/XÁO TRỘN so với 4 engine kia (không phải đọc sai nội dung, chỉ đọc
    khác thứ tự cột) — so nối liền theo thứ tự cho similarity=0.035 (như thể
    paddle_v6 đọc sai gần hết), trong khi so theo TỪNG DÒNG (đối chiếu đúng nội
    dung, không quan tâm thứ tự) similarity thật phải cao vì nội dung từng dòng
    khá giống nhau. Dùng bag-of-lines để tránh lặp lại lỗi này.
    """
    def avg_best(src: list[str], dst: list[str]) -> float:
        sims = [best_match(line, dst)[1] for line in src if line]
        return sum(sims) / len(sims) if sims else 0.0

    if not lines_a or not lines_b:
        return 0.0
    return (avg_best(lines_a, lines_b) + avg_best(lines_b, lines_a)) / 2


def rank_by_similarity(results: dict[str, Any], priority: list[str]) -> tuple[list[str], dict[str, float]]:
    """XÁC NHẬN 2026-09-15 (yêu cầu: "không xếp theo thứ tự ưu tiên, mà xếp theo
    độ giống nhau của các tools"): thay DEFAULT_PRIORITY cố định bằng xếp hạng
    ĐỘNG theo độ giống nhau thật giữa các engine ĐÃ CÓ DỮ LIỆU cho đúng trang này.

    Với mỗi engine, tính độ giống trung bình (`_bag_of_lines_similarity`, xem
    docstring ở trên — KHÔNG phụ thuộc thứ tự/cách tách dòng) so với TỪNG engine
    khác. Engine có độ giống trung bình CAO NHẤT (gần với "đa số" nhất) đứng đầu
    -> làm backbone. Engine THẤP NHẤT (lạc nhất so với các engine còn lại) đứng
    cuối -> ứng viên đầu tiên bị loại khi cần giữ số phiếu lẻ (xem vote_page).

    Không còn giả định trước "engine nào tốt hơn" (vd. không mặc định coi
    google_vision/gemini kém hơn paddle_v6/deepseek) — để dữ liệu thật của
    TỪNG TRANG tự quyết định, vì có trang 1 engine lạc nhóm, có trang engine
    khác lại lạc nhóm (xem PHÂN TÍCH trong README, ví dụ Gemini đọc đúng hơn ở
    một số trang dù win-rate trung bình thấp — win-rate đo "khớp đa số", không
    đo "đúng thật"; đây là cách tiếp cận thận trọng hơn: không cần biết trước
    engine nào đáng tin, chỉ cần xem nó có giống các engine khác hay không).

    `priority` (DEFAULT_PRIORITY) chỉ còn dùng để CHỌN ENGINE NÀO ĐƯỢC GỌI
    (không đổi), và làm tie-break xác định khi 2 engine có độ giống trung bình
    bằng hệt nhau (vd. đúng 2 engine — độ giống A~B và B~A luôn bằng nhau).
    """
    names = list(results)
    lines = {n: results[n].lines for n in names}
    pair_sim: dict[tuple[str, str], float] = {}
    avg_sim: dict[str, float] = {}
    for n in names:
        others = [m for m in names if m != n]
        if not others:
            avg_sim[n] = 1.0
            continue
        total = 0.0
        for m in others:
            key = tuple(sorted((n, m)))
            if key not in pair_sim:
                pair_sim[key] = _bag_of_lines_similarity(lines[n], lines[m])
            total += pair_sim[key]
        avg_sim[n] = total / len(others)
    ranked = sorted(names, key=lambda n: (-avg_sim[n], priority.index(n)))
    return ranked, avg_sim


def vote_from_results(results: dict[str, Any], priority: list[str]) -> dict[str, Any]:
    """Vote 1 trang từ dict engine -> EngineResult đã có sẵn (không gọi API).

    Dùng lại khi OCR cache nằm trong record (`engines{}`) — áp dụng lại thuật toán
    câu/Levenshtein mà không OCR lại. `vote_page()` gọi hàm này sau khi load adapter.
    """
    if not results:
        return {"voted_text": None, "vote_method": None, "engines": {}}

    ranked, avg_sim = rank_by_similarity(results, priority)
    backbone_name = ranked[0]
    backbone = results[backbone_name]

    engines_out: dict[str, Any] = {}
    for name, r in results.items():
        avg_score = (sum(r.scores.values()) / len(r.scores)) if r.scores else None
        engines_out[name] = {"text": "\n".join(r.lines), "score": avg_score,
                              "similarity_to_others": round(avg_sim[name], 4)}

    other_names = ranked[1:]

    excluded_from_vote = None
    if len(other_names) % 2 == 1:
        excluded_from_vote = other_names[-1]
        other_names = other_names[:-1]

    voted_lines: list[str] = []
    uncertain_spans: list[dict[str, Any]] = []

    for i, line in enumerate(backbone.lines):
        other_best: dict[str, str] = {}
        for name in other_names:
            match_text, sim = best_match(line, results[name].lines)
            if match_text is not None and sim >= SIM_NOTE_MIN:
                other_best[name] = match_text
        resolved = vote_line(backbone_name, line, other_best)
        voted_line = resolved["voted_line"]

        # Mục (5) docstring đầu file: vote CÂU không đủ đa số rõ ràng (hoặc "đa số"
        # chỉ là 2 engine tình cờ cùng sai giống nhau) -> thử vote lại theo từng vị
        # trí ký tự, có thể ghép được chỗ đúng của NHIỀU engine khác nhau trong
        # cùng 1 dòng mà vote CÂU không làm được (mỗi engine chỉ sai 1 chỗ khác nhau).
        positional = None
        if resolved["method"] in ("line_no_majority", "line_confirmed_majority") and other_best:
            positional = vote_line_positional(backbone_name, line, other_best)
            voted_line = positional["voted_line"]

        voted_lines.append(voted_line)
        if resolved["method"] != "line_unanimous" or resolved["disagreeing"] or positional is not None:
            span: dict[str, Any] = {"line": i, **resolved}
            if positional is not None:
                span["voted_line"] = voted_line
                span["positional"] = positional
            uncertain_spans.append(span)

    n_lines = len(backbone.lines) or 1
    excl_note = f"_excl_{excluded_from_vote}_for_odd" if excluded_from_vote else ""
    if other_names:
        method = f"{backbone_name}_backbone_line_vote_levenshtein_{len(other_names)}_other{excl_note}"
    else:
        method = f"{backbone_name}_only_no_other_engine{excl_note}"

    return {
        "voted_text": "\n".join(voted_lines),
        "vote_method": method,
        "engines": engines_out,
        "uncertain_spans": uncertain_spans,
        "structural_diffs": [],
        "uncertain_rate": round(len(uncertain_spans) / n_lines, 4),
    }


def results_from_engines(engines: dict[str, Any]) -> dict[str, Any]:
    """Khôi phục EngineResult từ `l1_ocr.engines` đã lưu trong record."""
    from ocr_adapters.base import EngineResult

    results: dict[str, Any] = {}
    for name, data in (engines or {}).items():
        if not isinstance(data, dict):
            continue
        text = data.get("text") or ""
        lines = text.split("\n")
        if not any(ln.strip() for ln in lines):
            continue
        scores: dict[str, float] = {}
        score = data.get("score")
        if score is not None:
            scores["_avg"] = float(score)
        results[name] = EngineResult(engine=name, lines=lines, scores=scores)
    return results


def vote_page(book: dict[str, Any], stem: str, priority: list[str]) -> dict[str, Any]:
    """Trả dict đúng khung `l1_ocr` của bilingual_record.schema.json.

    XÁC NHẬN 2026-09-12: đã thử gọi N engine SONG SONG (ThreadPoolExecutor)
    thay vì tuần tự, đo thực tế trên nom-84 trang 017-024: 429s/8 trang
    (53.6s/trang) — CHẬM HƠN cả bản tuần tự gốc (92.7s/8 trang = 11.6s/trang)
    lẫn lần thử song song theo trang trước đó (299s/8 trang). Rate limit phía
    server áp dụng cho cả việc gọi nhiều engine cùng lúc, không chỉ nhiều
    trang cùng lúc. ĐÃ REVERT về tuần tự từng engine — không tự ý bật lại
    song song ở đây khi chưa đo lại cẩn thận, cô lập khỏi mọi tiến trình khác
    đang chạy song song trên cùng API key.
    """
    results: dict[str, Any] = {}
    for name in priority:
        try:
            r = ADAPTERS[name].load(book, stem, FAMILY_TREE)
        except Exception:
            r = None
        if r is not None:
            results[name] = r

    return vote_from_results(results, priority)


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--book", required=True, help="book_id trong books_catalog.json")
    ap.add_argument("--pages", required=True, help="vd: 0,1,2 hoặc 001,002")
    ap.add_argument("--priority", default=",".join(DEFAULT_PRIORITY),
                     help="Thứ tự engine ưu tiên làm khung đọc (engine đầu tiên CÓ dữ liệu sẽ làm backbone)")
    ap.add_argument("--out", default=None, help="Thư mục ghi {stem}.vote.json (mặc định in ra stdout)")
    args = ap.parse_args()

    catalog = load_catalog()
    book = catalog.get(args.book)
    if book is None:
        raise SystemExit(f"Không có book_id {args.book} trong books_catalog.json")

    priority = [p.strip() for p in args.priority.split(",") if p.strip()]
    unknown = set(priority) - set(ADAPTERS)
    if unknown:
        raise SystemExit(f"Engine không rõ: {unknown}. Hợp lệ: {sorted(ADAPTERS)}")

    out_dir = Path(args.out) if args.out else None
    if out_dir:
        out_dir.mkdir(parents=True, exist_ok=True)

    for stem in [p.strip() for p in args.pages.split(",") if p.strip()]:
        result = vote_page(book, stem, priority)
        used = list(result["engines"].keys())
        print(f"[{args.book} p.{stem}] engine có dữ liệu: {used or '(không có engine nào)'}")
        if out_dir:
            (out_dir / f"{stem}.vote.json").write_text(
                json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8"
            )
        else:
            print(json.dumps(result, ensure_ascii=False, indent=2)[:2000])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
