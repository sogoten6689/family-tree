"""Dựng tree.json (BalkanNode) và gia_pha_structured.json cho vol 563 từ nhãn trang.

  python -X utf8 research/nom_volume_trees/vol563_build_tree.py data/03_derived/nom_volume_trees/563
"""
import json, os, sys

OUT = sys.argv[1]

# (id, tên, giới, fid, mid, pids, title, bio, năm sinh, năm mất)
NODES = [
    # Đời 1–4 (thế thứ trang 44, khớp trang 1, 38)
    (1, "Bối Am cư sĩ", "male", None, None, [], "Đời 1 (第一紀)",
     "Nguyễn phủ quân, tự Bối Am cư sĩ 貝庵居士; táng tại bản xã. Nguồn: trang 44.", None, None),
    (2, "Nguyễn Tử Hữu", "male", 1, None, [], "Đời 2 (第二紀); Hàn lâm viện thị giảng thời Trần",
     "Húy Tử Hữu 子有, thụy Tự Cường 自彊; ở xã Bối Khê, huyện Thanh Oai; táng ở thôn Ngọc Phác, xã Kim Bài. "
     "Trang 1 OCR ghi họ là 叚. Cha–con với đời 1 suy từ thế thứ (độ tin cậy vừa). Nguồn: trang 1, 44.", None, None),
    (3, "Nguyễn Bính", "male", 2, None, [4], "Đời 3 (第三紀); Nho học giáo quan",
     "Húy 炳 (trang 44 ghi 子炳), thụy Văn Hoán 文煥, hiệu Thông Trí cư sĩ 通智居士. Trang 1: 曾祖子有生祖考阮炳. Nguồn: trang 1, 38, 44.", None, None),
    (4, "Ngô Thị Ân", "female", 5, None, [3], "Vợ Nguyễn Bính",
     "Hiệu Quy Không bà 歸空婆; hợp táng với chồng ở xứ Luyện Đan, xã Bối Khê. Nguồn: trang 1, 38.", None, None),
    (5, "Ngô Quán", "male", None, None, [], "Cha bà Ngô Thị Ân",
     "Trang 38 chỉ còn chữ 觀 (觀之女曰氏恩); họ Ngô theo trang 1. Nguồn: trang 1, 38.", None, None),
    (6, "Nguyễn Thời Trung", "male", 3, 4, [7], "Đời 4 (第四紀); Bối Khê tiên sinh; Giáo thụ, Tế tửu Quốc Tử Giám",
     "Húy Thời Trung 時中, hiệu Như Ngu cư sĩ 如愚居士. Cuối Trần lánh loạn Hồ về Tiểu Động Mộng (nay thôn Văn Khê). "
     "Mất ngày 3 tháng 5 năm Đại Bảo 3 (1442), táng ở Muội Nguyên, xã Nghĩa Bang. Trang 38: được bà Thị Cải (chị cả bà Ân) nhận làm con. "
     "Nguồn: trang 9, 20, 22, 38, 42.", None, 1442),
    (7, "Đỗ Thị Trừng", "female", 8, 9, [6], "Vợ Bối Khê tiên sinh",
     "Húy Trừng 澄, hiệu Đức Trinh 德貞, cung nhân; mất ngày 10 tháng 3 năm Diên Ninh 2 (1455), hợp táng với chồng. Nguồn: trang 7, 11, 26.", None, 1455),
    (8, "Đỗ Tu Thân cư sĩ", "male", None, None, [9], "Cha bà Đỗ Thị Trừng", "Nguồn: trang 7, 26.", None, None),
    (9, "Từ Niệm bà", "female", None, None, [8], "Mẹ bà Đỗ Thị Trừng", "Chính thất của Tu Thân cư sĩ. Nguồn: trang 7, 26.", None, None),
    # Đời 5
    (10, "Nguyễn Trực", "male", 6, 7, [16, 19], "Đời 5 (第五紀); Trạng nguyên khoa Nhâm Tuất 1442; Hàn lâm viện Thừa chỉ, Tế tửu Quốc Tử Giám",
     "Húy Trực 直, hiệu Xư Liêu 樗寮, thụy Công Đĩnh 公挺. Sinh ngày 16 tháng 5 năm Đinh Dậu (1417) ở am Long Đẩu núi Phật Tích; "
     "mất ngày 28 tháng 12 năm Hồng Đức 4 (1473), thọ 57; cải táng ở thôn Đại Lại, xã Bạch Thạch, huyện Mỹ Lương. "
     "Nguồn: trang 7, 18, 26, 30, 31, 34.", 1417, 1473),
    (11, "Nguyễn Chân", "male", 6, 7, [], "Quốc Tử Giám tòng sự, phủ Quảng Uy", "Con thứ của Bối Khê tiên sinh. Nguồn: trang 7, 26.", None, None),
    (12, "Nguyễn Như Nột", "male", 11, None, [], "Con Nguyễn Chân", "Trang 26: Trạng nguyên nuôi làm con. Nguồn: trang 7, 26.", None, None),
    (13, "Nguyễn Thị Hiệu", "female", 6, 7, [], "Con gái trưởng", "OCR ghi 氏校. Nguồn: trang 26.", None, None),
    (14, "Cấn Thọ", "male", None, 13, [], "Tiến công lang, Y học huấn khoa", "Con trưởng của Thị Hiệu (OCR đảo dòng, độ tin cậy vừa). Nguồn: trang 26.", None, None),
    (15, "Nguyễn Thị Chuyên", "female", 6, 7, [], "Con gái thứ", "Nguồn: trang 26.", None, None),
    (16, "Nguyễn Trần Thị Lỗi", "female", 17, 18, [10], "Vợ cả Trạng nguyên; Cung nhân (1490), Huy nhân, tặng Hiển Cung phu nhân",
     "Húy Lỗi 磊, người hương Ngô Sài, dòng dõi hoàng thái tử Uy Minh thời Trần. Nguồn: trang 3, 16, 23.", None, None),
    (17, "Ngộ Phúc cư sĩ", "male", None, None, [18], "Cha bà Thị Lỗi", "Nguyễn Trần công, tự Ngộ Phúc 遇福. Nguồn: trang 16, 23.", None, None),
    (18, "Tịnh Niệm bà", "female", None, None, [17], "Mẹ bà Thị Lỗi", "Nguồn: trang 16, 23.", None, None),
    (19, "Đào Thị Anh", "female", 20, None, [10], "Vợ thứ (thứ thất) Trạng nguyên; Nghi nhân",
     "Húy Anh 瓔, người xã Thiện Phiến, huyện Tiên Lữ. Nguồn: trang 14, 16.", None, None),
    (20, "Đào Công Soạn", "male", None, None, [], "Tiến sĩ, Thượng thư, Hành khiển",
     "Tự Tân Khanh 賓卿. OCR ghi 陶公僕 (trang 14) và 公侯 (trang 16), đọc là 僎. Nguồn: trang 14, 16.", None, None),
    # Đời 6
    (21, "Nguyễn Lực Hành", "male", 10, 16, [28, 30, 32], "Đời 6, con trưởng; Đồng tiến sĩ khoa Mậu Tuất 1478; Đồng tri phủ Thao Giang",
     "Thụy Đôn Giản 敦簡; trang 14 còn ghi 阮公諱炯. Người soạn gia phả năm Hồng Đức 27 (1496). Nguồn: trang 1, 6, 14, 16, 19, 23.", None, None),
    (22, "Nguyễn Tử Triệt", "male", 10, 16, [48], "Đời 6, con thứ hai; Lại bộ hữu thượng thư",
     "Thụy Trang Khải 莊凱. Nguồn: trang 4, 8, 13, 16, 23, 40.", None, None),
    (23, "Nguyễn Thị Thục", "female", 10, 16, [54, 55], "Con gái trưởng",
     "Trang 3, 8: vợ cố Hộ khoa đô cấp sự trung Nguyễn Đình Viên; trang 29: lấy Tri huyện Đỗ Tử Sĩ. Xem unresolved. Nguồn: trang 3, 8, 13, 16, 29.", None, None),
    (24, "Nguyễn Thị Kính", "female", 10, 16, [], "Vào cung năm Hồng Đức 1 (1470); Dung Hoa, Tiệp dư, Tu Dung",
     "Đổi tên Cẩn Kính 謹敬; nuôi hoàng tử thứ 16 và Thị Tiên (con Lực Hành). Nguồn: trang 14, 16, 29, 32.", None, None),
    (25, "Nguyễn Thị Uyển", "female", 10, 16, [59], "Con gái thứ ba", "Nguồn: trang 3, 8, 14, 16, 32.", None, None),
    (26, "Nguyễn Đôn Tĩnh", "male", 10, 19, [64], "Đời 6, con thứ ba; Thái thường tự thiếu khanh",
     "Thụy Đoan Nhã 端雅. Trang 37 gọi là 妾子 (con thiếp, OCR ghi 衰靜) trong khi trang 16 ghi mẹ là Đào Thị Anh. Nguồn: trang 4, 14, 16, 37.", None, None),
    (27, "Nguyễn Mộng Ứng", "male", 10, 19, [66], "Đời 6, con thứ tư; Thái thường tự thiếu khanh",
     "Thụy Đoan Chân 端真. Nguồn: trang 2, 4, 14, 16, 37.", None, None),
    (28, "Nguyễn Thị Điệu", "female", 29, None, [21], "Vợ cả Lực Hành",
     "Húy 銚 (trang 19 OCR ghi 姚), vọng tộc xã Mậu Hòa, huyện Đan Phượng. Nguồn: trang 6, 8, 19, 27.", None, None),
    (29, "Nguyễn Văn Lôi", "male", None, None, [], "Cha bà Thị Điệu", "Trang 19 ghi 阮雷. Nguồn: trang 6, 19.", None, None),
    (30, "Nguyễn Thị Chiêm", "female", 31, None, [21], "Thiếp của Lực Hành", "Người Nghĩa Bang. Nguồn: trang 19.", None, None),
    (31, "Nguyễn Khối", "male", None, None, [], "Cha bà Thị Chiêm", "Nguồn: trang 19.", None, None),
    (32, "Lê Thị Hiền", "female", 33, None, [21], "Thiếp của Lực Hành", "Người xã Nghĩa Bang. Nguồn: trang 19.", None, None),
    (33, "Lê Thọ", "male", None, None, [], "Cha bà Thị Hiền", "Nguồn: trang 19.", None, None),
    # Đời 7 – con Lực Hành
    (34, "Nguyễn Thị Mai", "female", 21, 28, [35], "Con gái trưởng Lực Hành", "Nguồn: trang 4, 6, 19.", None, None),
    (35, "Ngô Giám", "male", 36, None, [34], "Tri huyện An Lãng", "Con út Ngô Sĩ Liên. OCR tách 吳 / 鑒 sang hai dòng. Nguồn: trang 6, 19.", None, None),
    (36, "Ngô Sĩ Liên", "male", None, None, [], "Đồng tiến sĩ khoa Nhâm Tuất; Tế tửu Quốc Tử Giám, Sử quan", "Người Chúc Lý. Nguồn: trang 4, 6, 19.", None, None),
    (37, "Ngô Thị Bích", "female", 35, 34, [], "Con gái Ngô Giám", "Nguồn: trang 6.", None, None),
    (38, "Nguyễn Thị Tùng", "female", 21, 28, [], "Con gái thứ hai Lực Hành", "Trang 19 OCR ghi 長松. Nguồn: trang 19, 32.", None, None),
    (39, "Phạm Tuyên", "male", None, 38, [], "Con Thị Tùng", "Nguồn: trang 32.", None, None),
    (40, "Phạm Hòa", "male", None, 38, [], "Con Thị Tùng", "Nguồn: trang 32.", None, None),
    (41, "Nguyễn Quan Tiên", "female", 21, 28, [], "Con gái thứ ba Lực Hành; vào cung hầu Cảnh Thống hoàng đế", "Nguồn: trang 19, 32.", None, None),
    (42, "Nguyễn Thị Phi", "female", 21, 28, [], "Con gái thứ tư Lực Hành", "Nguồn: trang 19, 32.", None, None),
    (43, "Nguyễn Doãn Tuế", "male", None, 42, [], "Tiến sĩ", "OCR ghi 阮允歲. Nguồn: trang 32.", None, None),
    (44, "Nguyễn Thị Tiên", "female", 21, None, [], "Con gái Lực Hành; được bà Thị Kính nuôi", "Chưa rõ mẹ. Nguồn: trang 32.", None, None),
    (45, "Nguyễn Nghi An", "male", 21, None, [], "Con trưởng của thiếp; Lục sự, nho sinh Tú Lâm",
     "Tự Phúc Đường 福堂. Mẹ là một thiếp người xã Bạch Thạch, sách mất tên. Nguồn: trang 14, 19, 40.", None, None),
    (46, "Nguyễn Vĩnh Gia", "male", 21, 30, [], "Con Lực Hành và Thị Chiêm", "Nguồn: trang 14, 19.", None, None),
    (47, "Nguyễn Đạt Lĩnh", "male", 21, 30, [], "Con Lực Hành và Thị Chiêm", "Nguồn: trang 19.", None, None),
    # Đời 7 – con Tử Triệt
    (48, "Nguyễn Thục Tường", "female", 49, None, [22], "Vợ Tử Triệt", "Vọng tộc xã Hoàng Xá, huyện Ninh Sơn. Nguồn: trang 40.", None, None),
    (49, "Nguyễn Lĩnh", "male", None, None, [], "Cha bà Thục Tường", "Nguồn: trang 40.", None, None),
    (50, "Nguyễn Sùng Nghĩa", "male", 22, 48, [], "Con trưởng Tử Triệt", "Ở xã Nghĩa Bang. Nguồn: trang 4, 40.", None, None),
    (51, "Nguyễn Cức Tương", "male", 22, 48, [], "Con thứ Tử Triệt; mất sớm", "OCR ghi 亟漿. Nguồn: trang 40.", None, None),
    (52, "Nguyễn Toàn Nghĩa", "male", 22, 48, [], "Đồng tri phủ Lương Nguyên", "Người viết thay văn khế 1475. Nguồn: trang 8, 27, 40.", None, None),
    (53, "Nguyễn Thục Thận", "female", 22, 48, [], "Mỹ nhân của Thánh Tông", "Nguồn: trang 4, 40.", None, None),
    # Đời 7 – con các con gái
    (54, "Nguyễn Đình Viên", "male", None, None, [23], "Hộ khoa đô cấp sự trung", "Đã mất khi lập văn khế (故). Nguồn: trang 3, 8.", None, None),
    (55, "Đỗ Tử Sĩ", "male", None, None, [23], "Mậu tài lang, Tri huyện huyện Thanh Vi 清為 (OCR, chưa chắc), phủ Nghĩa Nhân", "Nguồn: trang 14, 29.", None, None),
    (56, "Đỗ Thị Toàn", "female", 55, 23, [57], "Con gái Thị Thục", "Cha là Đỗ Tử Sĩ (suy ra, độ tin cậy vừa). Nguồn: trang 29.", None, None),
    (57, "Nguyễn Hữu Quang", "male", 58, None, [56], "Nho sinh Tú Lâm cục", "Nguồn: trang 29.", None, None),
    (58, "Nguyễn Hữu Bằng", "male", None, None, [], "Phó quản lĩnh vệ Ngọc Linh", "Người xã Sơn Đồng, huyện Đan Phượng. Nguồn: trang 29.", None, None),
    (59, "Hoàng Bá Dương", "male", None, None, [25], "Nhị giáp tiến sĩ; Đề hình giám sát ngự sử",
     "OCR ghi 黃伯楊 / 黃伯揚 / 黃伯陽; táng ở xã Bạch Thạch. Nguồn: trang 3, 8, 14, 32.", None, None),
    (60, "Hoàng Nghĩa Minh", "male", 59, 25, [], "Con trưởng Thị Uyển", "Nguồn: trang 32.", None, None),
    (61, "Hoàng Nghĩa Cần", "male", 59, 25, [], "Con Thị Uyển", "Nguồn: trang 32.", None, None),
    (62, "Hoàng Tuấn Khanh", "male", 59, 25, [], "Con Thị Uyển", "Nguồn: trang 32.", None, None),
    (63, "Hoàng Nghĩa Cương", "male", 59, 25, [], "Con Thị Uyển", "Nguồn: trang 32.", None, None),
    # Đời 7 – con Đôn Tĩnh, Mộng Ứng
    (64, "Trần Hôn", "female", None, None, [26], "Vợ Đôn Tĩnh", "Cháu gái cố Lễ bộ thượng thư Trần Dục 陳昱; OCR ghi 陳昏. Nguồn: trang 37.", None, None),
    (65, "Nguyễn Đôn Nhiên", "male", 26, None, [], "Con Đôn Tĩnh", "Ở xã Nghĩa Bang; chưa rõ mẹ. Nguồn: trang 4.", None, None),
    (66, "Lê Thị Ngọc Mạo", "female", 67, None, [27], "Vợ Mộng Ứng", "Nguồn: trang 2, 37.", None, None),
    (67, "Lê Chưởng", "male", None, None, [], "Văn Minh á quận công", "Nguồn: trang 37.", None, None),
    (68, "Nguyễn Hữu Tượng", "male", 27, 66, [], "Đời 7 (第七紀); ở xã Bạch Thạch", "Nguồn: trang 2, 37.", None, None),
    (69, "Nguyễn Thụy Lân", "male", 27, 66, [], "Đời 7 (第七紀); ở thôn Văn Khê, Nghĩa Bang", "Nguồn: trang 2, 37.", None, None),
]

tree = []
for i, name, g, fid, mid, pids, title, bio, by, dy in NODES:
    n = {"id": i, "name": name, "gender": g}
    if by: n["birthYear"] = by
    if dy: n["deathYear"] = dy
    if fid: n["fid"] = fid
    if mid: n["mid"] = mid
    if pids: n["pids"] = pids
    n["title"] = title
    n["bio"] = bio
    tree.append(n)

ids = {n["id"]: n for n in tree}
assert len(ids) == len(tree)
for n in tree:
    for p in n.get("pids", []):
        assert n["id"] in ids[p].get("pids", []), (n["id"], p)
    if "fid" in n: assert ids[n["fid"]]["gender"] == "male", n["id"]
    if "mid" in n: assert ids[n["mid"]]["gender"] == "female", n["id"]

json.dump(tree, open(os.path.join(OUT, "tree.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=2)

pages = {}
for f in sorted(os.listdir(os.path.join(OUT, "pages"))):
    pages[int(f[:3])] = json.load(open(os.path.join(OUT, "pages", f), encoding="utf-8"))

relations = []
for n, pg in pages.items():
    for r in pg["relations"]:
        relations.append({"page": n, "type": r["type"], "head": pg["entities"][r["head"]]["text"],
                          "tail": pg["entities"][r["tail"]]["text"], "confidence": r["confidence"], "evidence": r["evidence"]})

structured = {
    "schema_version": "1.0",
    "tree_id": "nom-563",
    "lineage_name": "Họ Nguyễn ở Bối Khê, Thanh Oai — Trạng nguyên Xư Liêu tiên sinh gia phả 狀元樗寮先生家譜",
    "source": {"nomfoundation": "https://lib.nomfoundation.org/collection/1/volume/563/",
               "web_scan_id": 9, "ma_dinh_danh": "F-B-NG-BoiKhe-008-1496", "pages": 44},
    "compiled": "Nguyễn Lực Hành soạn năm Hồng Đức 27 (1496) (trang 1)",
    "label_source": "silver_claude (chưa người duyệt)",
    "persons_in_tree": len(tree),
    "relations_all_pages": relations,
    "unresolved": [
        {"text": "Chồng của Nguyễn Thị Thục", "reason": "conflict",
         "note": "Trang 3, 8 ghi là vợ cố Nguyễn Đình Viên 阮廷圓 (阮圓); trang 29 ghi lấy Tri huyện Đỗ Tử Sĩ 杜子仕 và sinh Thị Toàn. "
                 "Văn khế trang 3 gọi Đình Viên là 故 (đã mất), nên có thể bà tái giá; cây tạm để cả hai làm chồng, Thị Toàn là con Đỗ Tử Sĩ."},
        {"text": "Mẹ của Nguyễn Đôn Tĩnh", "reason": "conflict",
         "note": "Trang 16 và 14: con bà thứ thất Đào Thị Anh (được phong Nghi nhân); trang 37: 狀元公妾子 (con thiếp). Cây theo trang 14, 16."},
        {"text": "美人陳氏 (trang 4)", "reason": "ambiguous_link",
         "note": "Đứng cạnh 狀元公行參男 (con trai thứ ba); không rõ là vợ Đôn Tĩnh hay ghi chú khác. Trang 37 ghi vợ Đôn Tĩnh là Trần Hôn 陳昏, cháu gái Trần Dục. Chưa đưa vào cây."},
        {"text": "Họ của Tử Hữu (trang 1)", "reason": "ocr_error", "note": "OCR ghi 叚; theo ngữ cảnh là họ Nguyễn."},
        {"text": "Tên sách (trang 1)", "reason": "ocr_error", "note": "OCR ghi 狀元察先生家譜 và 樗庵; đúng là 樗寮."},
        {"text": "Nguyễn Khôi Ngô 阮魁梧 (trang 40; trang 4 có 梧魁)", "reason": "uncertain_parent",
         "note": "Mẹ là thiếp họ Trịnh; sách chỉ ghi 或疑是阮宜安之子 (có lẽ là con Nghi An). Chưa đưa vào cây."},
        {"text": "Nghi thức nhận con nuôi", "reason": "not_in_schema",
         "note": "Trang 38: bà Thị Cải (chị cả bà Ân) nhận Thời Trung làm con; trang 26: Trạng nguyên nuôi Như Nột làm con; trang 32: Thị Kính nuôi hoàng tử thứ 16 và Thị Tiên. Schema RE v1 không có quan hệ nhận nuôi."},
        {"text": "Mẹ của Nguyễn Nghi An", "reason": "missing_name", "note": "Trang 19: thiếp người xã Bạch Thạch, sách mất tên (失)."},
        {"text": "Các người họ hàng bên ngoại ở trang 38 (Thị Cổn, Tự, Sư Lượng, Lưu thị)", "reason": "no_link_to_tree",
         "note": "Anh chị em bà Thị Ân và con cháu; OCR đảo dòng, quan hệ chưa đủ rõ để đưa vào cây (chỉ gán 嗣 → 師亮)."},
        {"text": "Thị Quỳnh, Thị Dương, Thủ Khiêm, Nguyễn Duy Sảng (trang 19), Duy Chân (trang 14)", "reason": "no_parent_link",
         "note": "Ghi là 女孫 (cháu gái) hoặc tên rời trong ô nhỏ; không rõ cha mẹ."},
        {"text": "Thị Nông 氏農 (trang 42)", "reason": "ambiguous", "note": "Câu 氏農貝溪先生之妾子也 bị cắt; chưa rõ nghĩa."},
        {"text": "Nguyễn Doãn Đạt 阮允達 (trang 6), Trọng Đạt 仲達 (trang 4)", "reason": "no_link_to_tree", "note": "Dòng bị cắt; chưa rõ là chồng/con của ai."},
    ],
}
json.dump(structured, open(os.path.join(OUT, "gia_pha_structured.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=2)
print(f"tree: {len(tree)} người; quan hệ trên các trang: {len(relations)}; unresolved: {len(structured['unresolved'])}")
