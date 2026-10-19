"""Dựng tree.json (BalkanNode) và gia_pha_structured.json cho vol 429 từ nhãn trang."""
import json, os, sys

OUT = sys.argv[1]

# (id, tên, giới, fid, mid, pids, title, bio)
NODES = [
    # Sổ thứ nhất: xã Thuỵ Ứng (trang 2–3)
    (1, "Nguyễn Phúc Bảo", "male", None, None, [2], "Cao tổ khảo (sổ Thuỵ Ứng)",
     "Nguyễn quý công, tự Phúc Bảo 福寶. Nguồn: trang 3."),
    (2, "Từ Vân", "female", None, None, [1], "Cao tổ tỉ (sổ Thuỵ Ứng)",
     "Nguyễn quý thị, hiệu Từ Vân 慈雲. Nguồn: trang 3."),
    (3, "Phúc Thịnh", "male", 1, 2, [4], "Tằng tổ khảo (sổ Thuỵ Ứng)",
     "Tự Phúc Thịnh 福盛; giỗ 28 tháng 10 âm lịch. Nguồn: trang 2. Quan hệ cha–con với cao tổ suy từ thứ bậc trong sổ (độ tin cậy vừa)."),
    (4, "Từ Nghiễm", "female", None, None, [3], "Tằng tổ tỉ (sổ Thuỵ Ứng)",
     "Nguyễn quý thị, hiệu Từ Nghiễm 慈儼; giỗ 21 tháng 3. Nguồn: trang 2."),
    (5, "Nguyễn Phúc Nghi", "male", 3, 4, [6], "Tổ khảo (sổ Thuỵ Ứng)",
     "Nguyễn quý công, tự Phúc Nghi 福儀; giỗ 5 tháng 2. Nguồn: trang 2."),
    (6, "Từ Hạnh", "female", None, None, [5], "Tổ tỉ (sổ Thuỵ Ứng)",
     "Nguyễn quý thị, hiệu Từ Hạnh 慈杏; giỗ 20 tháng 3. Nguồn: trang 2."),
    (7, "Nguyễn Đăng Thanh", "male", 5, 6, [8, 9], "Tiền Chánh tổng; hiển khảo (sổ Thuỵ Ứng)",
     "Húy Đăng Thanh 登清, tự Phúc Thu 福秋; giỗ 16 tháng 8. OCR ghi họ là 院, đọc là 阮 (Nguyễn). Nguồn: trang 2."),
    (8, "Nguyễn Thị Chiêm", "female", None, None, [7], "Vợ cả (đích thất)",
     "Hiệu Từ An 慈安; giỗ 18 tháng 9. Nguồn: trang 2."),
    (9, "Nguyễn Thị Châu", "female", None, None, [7], "Vợ thứ",
     "Hiệu Diệu Thư 妙書; giỗ 3 tháng 11. Nguồn: trang 2."),
    (10, "Thích Thông Đối", "male", 7, None, [], "Tỳ kheo, trụ trì chùa Hưng Long, thôn Trung; người lập sổ",
     "Đệ tử Phật, thọ giới Bồ tát, tự Thông Đối 通對, dòng thiền Phổ Cập. Là con của hiển khảo Đăng Thanh (suy từ lời cúng, độ tin cậy vừa); chưa rõ mẹ là vợ cả hay vợ thứ. Nguồn: trang 2."),
    (11, "Nguyễn Phúc Thuật", "male", None, None, [12], "Thủy tổ (sổ Thuỵ Ứng)",
     "Nguyễn quý công, tự Phúc Thuật 福術. Chưa nối được với cao tổ Phúc Bảo (sổ không ghi các đời giữa). Nguồn: trang 3."),
    (12, "Nguyễn Thị Chỉ", "female", None, None, [11], "Vợ thủy tổ",
     "Hiệu Từ Đài 慈臺. OCR ghi 姚, đọc là 妣. Nguồn: trang 3."),
    # Sổ thứ hai: xã Hạ Trì (trang 5), lập năm Duy Tân 6 (1912)
    (13, "Nguyễn Phúc Ninh", "male", None, None, [14], "Tổ khảo (sổ Hạ Trì)",
     "Nguyễn quý công, tự Phúc Ninh 福寧; giỗ 28 tháng 5. Nguồn: trang 5."),
    (14, "Thục Tín", "female", None, None, [13], "Tổ tỉ (sổ Hạ Trì)",
     "Hiệu Thục Tín 淑信; giỗ 7 tháng 5. Nguồn: trang 5."),
    (15, "Nguyễn Đăng Hữu", "male", 13, 14, [16], "Hiển khảo (sổ Hạ Trì)",
     "Nguyễn quý công, húy Đăng Hữu 登友, hiệu Đức Nhân 德仁; giỗ chính 20 tháng 8. Nguồn: trang 5."),
    (16, "Nguyễn Thị Tình", "female", 17, 18, [15], "Hiển tỉ (sổ Hạ Trì)",
     "Nguyễn quý thị, húy Tình 情, hiệu Phúc Trinh 福貞; giỗ chính 25 tháng 10. Cha mẹ là ông bà ngoại của người lập sổ (suy ra, độ tin cậy thấp). Nguồn: trang 5."),
    (17, "Nguyễn Đức Chiêu", "male", None, None, [18], "Ngoại tổ khảo (sổ Hạ Trì)",
     "Nguyễn quý công, tự Đức Chiêu 德釗; giỗ 1 tháng 5. Nguồn: trang 5."),
    (18, "Từ Thuận", "female", None, None, [17], "Ngoại tổ tỉ (sổ Hạ Trì)",
     "Nguyễn quý thị, hiệu Từ Thuận 慈順; giỗ 28 tháng 12. Nguồn: trang 5."),
    (19, "Nguyễn Thị Nguyên", "female", 15, 16, [], "Tỳ kheo ni, pháp hiệu Đàm Quang; người lập sổ",
     "Pháp hiệu Đàm Quang 曇光, hiệu Diệu Uyên 妙淵, thọ giới Bồ tát. Em đọc Đàm Quang và Nguyễn Thị Nguyên là cùng một người (chưa chắc). Nguồn: trang 5."),
    (20, "Nguyễn Thị Thùy", "female", 15, 16, [], "Cùng đứng tên lập sổ",
     "Hiệu Diệu Y 妙依. Nguồn: trang 5."),
    (21, "Nguyễn Đăng Phức", "male", 15, None, [], "Người thừa tự (nối dõi)",
     "Ghi là 承嗣 (thừa tự); có thể là con nuôi nên chưa gắn mẹ. Nguồn: trang 5."),
]

tree = []
for i, name, g, fid, mid, pids, title, bio in NODES:
    n = {"id": i, "name": name, "gender": g}
    if fid: n["fid"] = fid
    if mid: n["mid"] = mid
    if pids: n["pids"] = pids
    n["title"] = title
    n["bio"] = bio
    tree.append(n)

# Kiểm tra nhất quán: pids đối xứng, fid/mid trỏ tới đúng giới
ids = {n["id"]: n for n in tree}
for n in tree:
    for p in n.get("pids", []):
        assert n["id"] in ids[p].get("pids", []), (n["id"], p)
    if "fid" in n: assert ids[n["fid"]]["gender"] == "male", n["id"]
    if "mid" in n: assert ids[n["mid"]]["gender"] == "female", n["id"]

json.dump(tree, open(os.path.join(OUT, "tree.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=2)

# Bản có cấu trúc: các cặp vợ chồng khác và điều chưa giải quyết
pages = {}
for f in sorted(os.listdir(os.path.join(OUT, "pages"))):
    pages[int(f[:3])] = json.load(open(os.path.join(OUT, "pages", f), encoding="utf-8"))

other_couples = []
tree_names = {"阮貴公", "阮貴氏"}
for n, pg in pages.items():
    for r in pg["relations"]:
        if r["type"] != "SPOUSE":
            continue
        h, t = pg["entities"][r["head"]]["text"], pg["entities"][r["tail"]]["text"]
        other_couples.append({"page": n, "head": h, "tail": t, "confidence": r["confidence"], "evidence": r["evidence"]})

per_list = {n: sum(1 for e in pg["entities"] if e["label"] == "PER_NAME") for n, pg in pages.items()}
structured = {
    "schema_version": "1.0",
    "tree_id": "nom-429",
    "lineage_name": "Họ Nguyễn — Thuỵ Ứng gia phả 瑞應家譜 (gồm 2 sổ: xã Thuỵ Ứng và xã Hạ Trì)",
    "source": {"nomfoundation": "https://lib.nomfoundation.org/collection/1/volume/429/",
               "web_scan_id": 7, "ma_dinh_danh": "F-B-NG-ThuyUng-005-1912", "pages": 9},
    "label_source": "silver_claude (chưa người duyệt)",
    "persons_in_tree": len(tree),
    "spouse_pairs_all_pages": other_couples,
    "unresolved": [
        {"text": "Thủy tổ Nguyễn Phúc Thuật (trang 3) và cao tổ Nguyễn Phúc Bảo", "reason": "missing_generations",
         "note": "Sổ không ghi các đời giữa thủy tổ và cao tổ."},
        {"text": "Sổ Thuỵ Ứng (trang 1–3) và sổ Hạ Trì (trang 4–9)", "reason": "unknown_link",
         "note": "Cả hai đều họ Nguyễn, chữ lót Đăng (Đăng Thanh, Đăng Hữu, Đăng Phức), cùng dòng thiền Phổ Cập, nhưng sách không ghi quan hệ giữa hai nhánh."},
        {"text": "Thích Thông Đối", "reason": "ambiguous_mother", "note": "Không rõ là con vợ cả Chiêm hay vợ thứ Châu."},
        {"text": "Các người họ hàng ở trang 3 (Phúc Thọ, Phúc Đức, Thai/Phúc Tịnh, Đăng Đới, Đăng Võ, Phúc Phú, Phúc Thân, Phúc Mãn, Phúc Phối, Xuân Tại, Xuân Diệu…, có ghi 附為丙支 'phụ vào chi Bính')",
         "reason": "no_parent_link", "note": "Chỉ là danh sách cúng giỗ; có các cặp vợ chồng nhưng không ghi cha mẹ."},
        {"text": f"Danh sách tên ở trang 6–9 ({per_list[6] + per_list[7] + per_list[8] + per_list[9]} lượt tên)", "reason": "no_parent_link",
         "note": "Danh sách người được cúng (họ Nguyễn, Phạm, Hoàng, Lê, Trần, Bùi, Vũ…); OCR nhiều chỗ nhầm 妣 thành 她/紕/姚. Trang 6 có dòng 阮貴公諱登素 / 福秋 trùng tự Phúc Thu của Đăng Thanh, chưa rõ cùng người hay không."},
        {"text": "Nguyễn Thị Thông, Nguyễn Thị Hồng (trang 5, lặp lại ở trang 9)", "reason": "no_parent_link", "note": "Giỗ cùng tháng 9; không ghi quan hệ."},
        {"text": "Tú tài Nguyễn Hữu Trực; Lý quý công tự Tiến Đạt (trang 5)", "reason": "no_link_to_tree", "note": "Có vợ (Từ Tiết, Từ Khoan) nhưng không rõ quan hệ với người lập sổ."},
    ],
}
json.dump(structured, open(os.path.join(OUT, "gia_pha_structured.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=2)
print(f"tree: {len(tree)} người; cặp vợ chồng trên các trang: {len(other_couples)}; unresolved: {len(structured['unresolved'])}")
