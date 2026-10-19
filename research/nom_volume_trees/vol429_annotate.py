"""Gán nhãn NER/RE (silver, Claude) cho vol 429 và ghi pages/NNN.json.

Mỗi trang: danh sách thực thể theo thứ tự xuất hiện (key, nhãn, chuỗi); offset được dò tuần tự
trong hannom_text (không sửa chữ OCR) và kiểm tra text[start:end] == chuỗi.
Quan hệ: (loại, key đầu, key cuối, độ tin cậy, căn cứ).
"""
import json, os, sys

SRC, OUT = sys.argv[1], sys.argv[2]

P, G, D, O, L = "PER_NAME", "GENERATION", "DATE", "ORDER", "LOC"

PAGES = {
    1: dict(ents=[("loc_thuyung", L, "瑞應")], rels=[]),
    2: dict(
        ents=[
            ("loc_xa", L, "大南國河東省懷德府丹鳳縣丹鳳總瑞應社"),
            ("loc_thon", L, "中村"),
            ("loc_chua", L, "興隆寺"),
            ("thongdoi", P, "通對"),
            ("g_khao", G, "顯考"), ("dangthanh", P, "院貴公"), ("dangthanh_huy", P, "登清"), ("dangthanh_tu", P, "福秋"), ("d1", D, "八月十六日"),
            ("g_dichti", G, "顯嫡妣"), ("chiem", P, "阮氏占"), ("chiem_hieu", P, "慈安"), ("d2", D, "九月十八日"),
            ("g_thuti", G, "顯次妣"), ("chau", P, "阮氏珠"), ("chau_hieu", P, "妙書"), ("d3", D, "十一月初三日"),
            ("g_tokhao", G, "顯祖考"), ("phucnghi", P, "阮貴公"), ("phucnghi_tu", P, "福儀"), ("d4", D, "貳月初五日"),
            ("g_toti", G, "顯祖妣"), ("tuhanh", P, "阮貴氏"), ("tuhanh_hieu", P, "慈杏"), ("d5", D, "叁月貳拾日"),
            ("g_tangto", G, "曾祖考"), ("phucthinh", P, "福盛"), ("d6", D, "十月二十八日"),
            ("g_tangti", G, "曾祖妣"), ("tunghiem", P, "阮貴氏"), ("tunghiem_hieu", P, "慈儼"), ("d7", D, "三月二十一日"),
        ],
        rels=[
            ("FATHER_OF", "dangthanh", "thongdoi", "vừa", "顯考 trong lời cúng do Thông Đối đứng tên"),
            ("SPOUSE", "dangthanh", "chiem", "cao", "顯嫡妣 (vợ cả) ngay sau 顯考"),
            ("SPOUSE", "dangthanh", "chau", "cao", "顯次妣 (vợ thứ) ngay sau 顯考"),
            ("FATHER_OF", "phucnghi", "dangthanh", "vừa", "顯祖考 là cha của 顯考"),
            ("SPOUSE", "phucnghi", "tuhanh", "cao", "顯祖考 / 顯祖妣"),
            ("MOTHER_OF", "tuhanh", "dangthanh", "vừa", "顯祖妣 là mẹ của 顯考"),
            ("FATHER_OF", "phucthinh", "phucnghi", "vừa", "曾祖考 là cha của 祖考"),
            ("SPOUSE", "phucthinh", "tunghiem", "cao", "曾祖考 / 曾祖妣"),
            ("MOTHER_OF", "tunghiem", "phucnghi", "vừa", "曾祖妣 là mẹ của 祖考"),
        ],
    ),
    3: dict(
        ents=[
            ("g_caoto", G, "高祖考"), ("phucbao", P, "阮貴公"), ("phucbao_tu", P, "福寶"),
            ("g_caoti", G, "高祖妣"), ("tuvan", P, "阮貴氏"), ("tuvan_hieu", P, "慈雲"),
            ("a1", P, "阮貴公"), ("a1_tu", P, "福壽"),
            ("a2", P, "阮貴公"), ("a2_tu", P, "福德"),
            ("thai", P, "阮公"), ("thai_huy", P, "台"), ("thai_tu", P, "福净"), ("dong", P, "阮氏仝"),
            ("a3", P, "阮登帶"), ("a4", P, "阮登武"),
            ("phucphu", P, "阮貴公"), ("phucphu_tu", P, "福富"), ("nghiathanh", P, "義青"),
            ("a5", P, "阮氏廸"), ("a6", P, "阮氏"), ("a6_hieu", P, "慈汝"),
            ("a7", P, "阮貴公"), ("a7_tu", P, "福珅"), ("a8", P, "阮氏肇"),
            ("g_ngoaito1", G, "外祖"), ("phucman", P, "福滿"), ("tuthieu", P, "慈韶"),
            ("a9", P, "阮氏"), ("a9_hieu", P, "慈圓"), ("a10", P, "阮氏信"), ("a11", P, "侍"),
            ("phucphoi", P, "福配"), ("thi", P, "阮氏詩"),
            ("a12", P, "阮氏裘"), ("a13", P, "阮春在"), ("a14", P, "阮氏迭"), ("a15", P, "阮氏才"),
            ("a16", P, "阮春耀"), ("a16_hieu", P, "淑孌"),
            ("g_thuyto", G, "始祖"), ("phucthuat", P, "阮貴公"), ("phucthuat_tu", P, "福術"), ("chi", P, "阮氏芷"), ("chi_hieu", P, "慈臺"),
            ("luong", P, "俍"), ("luong_tu", P, "法習"), ("luong_hieu", P, "玄文"),
            ("tudan", P, "阮氏"), ("tudan_hieu", P, "慈寅"), ("tunghia", P, "慈義"), ("thucnghia", P, "淑義"),
            ("nguu", P, "阮貴公"), ("nguu_huy", P, "牛"), ("nguu_tu", P, "福堯"),
            ("g_ngoaito2", G, "外祖"), ("phaphien", P, "阮貴公"), ("phaphien_tu", P, "法顯"), ("tuthan", P, "慈嘆"),
            ("d1", D, "拾月初八日"),
        ],
        rels=[
            ("SPOUSE", "phucbao", "tuvan", "cao", "高祖考 / 高祖妣"),
            ("SPOUSE", "thai", "dong", "cao", "娶阮氏仝"),
            ("SPOUSE", "phucphu", "nghiathanh", "cao", "娶號義青"),
            ("SPOUSE", "phucman", "tuthieu", "cao", "娶號慈韶"),
            ("SPOUSE", "phucphoi", "thi", "cao", "娶阮氏詩"),
            ("SPOUSE", "phucthuat", "chi", "vừa", "姚 (đọc là 妣) 阮氏芷 sau 始祖"),
            ("SPOUSE", "luong", "tudan", "cao", "正室 (vợ cả)"),
            ("SPOUSE", "luong", "tunghia", "cao", "側室 (vợ lẽ)"),
            ("SPOUSE", "phaphien", "tuthan", "cao", "娶號慈嘆"),
        ],
    ),
    4: dict(ents=[], rels=[]),
    5: dict(
        ents=[
            ("d0", D, "大南維新六年歲次壬子七月初五日"),
            ("loc_xa", L, "河\n東省懷德府慈廉縣下池總下池社"),
            ("damquang", P, "曇光"), ("nguyen", P, "阮氏源"), ("nguyen_hieu", P, "妙淵"),
            ("thuy", P, "阮氏垂"), ("thuy_hieu", P, "妙依"), ("dangphuc", P, "阮登馥"),
            ("g_khao", G, "顯考"), ("danghuu", P, "阮貴公"), ("danghuu_huy", P, "登友"), ("danghuu_hieu", P, "德仁"), ("d1", D, "捌月貳拾日"),
            ("g_ti", G, "顯妣"), ("tinh", P, "阮貴氏"), ("tinh_huy", P, "情"), ("tinh_hieu", P, "福貞"), ("d2", D, "拾月貳拾五日"),
            ("g_tokhao", G, "祖考"), ("phucninh", P, "阮貴公"), ("phucninh_tu", P, "福寧"), ("d3", D, "五月二十捌日"),
            ("g_toti", G, "祖妣"), ("thuctin", P, "淑信"), ("d4", D, "五月 初七日"),
            ("thong", P, "阮氏通"), ("hong", P, "阮氏紅"), ("d5", D, "九月三十日"),
            ("g_ngoaito", G, "外祖考"), ("ducchieu", P, "阮貴公"), ("ducchieu_tu", P, "德釗"), ("d6", D, "五月初壹日"),
            ("tuthuan", P, "阮貴氏"), ("tuthuan_hieu", P, "慈順"), ("d7", D, "十二月二十八日"),
            ("huutruc", P, "阮有直"), ("huutruc_hieu", P, "福真"), ("tutiet", P, "慈節"), ("tukien", P, "慈健"),
            ("ly", P, "李貴公"), ("ly_tu", P, "進達"), ("tukhoan", P, "慈寬"), ("ducchi", P, "德志"), ("tuhue", P, "慈惠"),
        ],
        rels=[
            ("SPOUSE", "danghuu", "tinh", "cao", "顯考 / 顯妣"),
            ("FATHER_OF", "danghuu", "damquang", "vừa", "顯考 trong lời cúng do Đàm Quang đứng tên"),
            ("MOTHER_OF", "tinh", "damquang", "vừa", "顯妣 trong lời cúng do Đàm Quang đứng tên"),
            ("FATHER_OF", "danghuu", "thuy", "vừa", "cùng đứng tên lời cúng"),
            ("MOTHER_OF", "tinh", "thuy", "vừa", "cùng đứng tên lời cúng"),
            ("FATHER_OF", "danghuu", "dangphuc", "vừa", "承嗣 (người nối dõi); có thể là con nuôi"),
            ("FATHER_OF", "phucninh", "danghuu", "vừa", "祖考 là cha của 顯考"),
            ("SPOUSE", "phucninh", "thuctin", "cao", "祖考 / 祖妣"),
            ("MOTHER_OF", "thuctin", "danghuu", "vừa", "祖妣 là mẹ của 顯考"),
            ("SPOUSE", "ducchieu", "tuthuan", "cao", "外祖考 / 妣"),
            ("FATHER_OF", "ducchieu", "tinh", "thấp", "外祖考 (ông ngoại người đứng tên) suy ra là cha của 顯妣"),
            ("MOTHER_OF", "tuthuan", "tinh", "thấp", "bà ngoại người đứng tên suy ra là mẹ của 顯妣"),
            ("SPOUSE", "huutruc", "tutiet", "vừa", "妣號慈節 ngay sau tên"),
            ("SPOUSE", "ly", "tukhoan", "vừa", "妣號慈寬 ngay sau tên"),
        ],
    ),
    6: dict(
        ents=[
            ("phucminh", P, "福明"), ("dieuduc", P, "妙德"), ("phuckhang", P, "福康"), ("tutu", P, "慈秀"),
            ("phuctruong", P, "福長"), ("tuan", P, "慈恩"), ("phucthien", P, "福善"), ("tuai", P, "慈愛"),
            ("le", P, "黎貴公"), ("le_tu", P, "黃秀"), ("le_thuy", P, "福銀"), ("linhtinh", P, "靈静"),
            ("phaptri", P, "法持"), ("thucman", P, "淑滿"), ("thucdao", P, "淑道"),
            ("d1", D, "八月二十五日"),
            ("thuantruc", P, "元貴公"), ("thuantruc_tu", P, "純直"), ("hoang", P, "黃相公"),
            ("tiep", P, "阮氏捷"), ("d2", D, "十一月初三日"),
            ("dangto", P, "阮貴公"), ("dangto_huy", P, "登素"), ("phucthu", P, "福秋"),
            ("dangtriem", P, "阮登霑"), ("dangtriem_hieu", P, "直純"), ("vang", P, "阮氏彚"),
            ("dangdao", P, "玩登道"), ("dangdao_hieu", P, "福慶"), ("tuan2", P, "黃氏恂"),
            ("dinhtam", P, "范廷叄"), ("diem", P, "阮氏點"), ("ket", P, "阮氏結"), ("vantuan", P, "阮文遵"),
            ("lo", P, "阮氏鷺"), ("trungthuan", P, "忠順"), ("minhlang", P, "明朗"),
            ("thucluong", P, "鍾淑良"), ("thucluong_tu", P, "早安"),
        ],
        rels=[
            ("SPOUSE", "phucminh", "dieuduc", "vừa", "紕 (đọc là 妣) 妙德 ngay sau tự 福明"),
            ("SPOUSE", "phuckhang", "tutu", "thấp", "cặp tự – hiệu liền nhau, chữ giữa OCR mờ"),
            ("SPOUSE", "phuctruong", "tuan", "vừa", "她 (đọc là 妣) 號慈恩"),
            ("SPOUSE", "phucthien", "tuai", "vừa", "她 (đọc là 妣) 慈愛"),
            ("SPOUSE", "le", "linhtinh", "vừa", "她 (đọc là 妣) 靈静"),
            ("SPOUSE", "phaptri", "thucman", "vừa", "她號淑滿"),
        ],
    ),
    7: dict(
        ents=[(f"p{i}", P, s) for i, s in enumerate([
            "早脫", "阮文匡", "淑清", "淑言", "直成", "直春", "慈幸", "阮文适", "德輝", "阮氏緣", "權貴",
            "阮氏檄", "妙善", "阮文謀", "阮文連", "阮文燦", "阮文急", "阮文祿", "阮文貫", "阮文祿", "福敬",
            "阮氏醉", "妙貞", "阮文駕", "福加", "阮氏瑩", "慈兄", "阮文儒", "阮文忠", "阮文員", "阮文碩",
            "阮登流", "忠直", "阮氏松", "慈栢", "阮氏欣", "慈馨", "阮氏榮", "淑美花", "范氏品", "范廷汝",
            "阮氏心", "范廷梯", "范廷雲", "黎氏慈", "范文士", "阮氏說", "范文詩", "直身", "阮登壇"])]
        + [(f"d{i}", D, s) for i, s in enumerate(["正月初四日", "十二月二十七日", "正月十六日", "正月二十日", "十月十一日"])],
        rels=[("SPOUSE", "p45", "p46", "vừa", "婺 (đọc là 娶) 阮氏說")],
    ),
    8: dict(
        ents=[(f"p{i}", P, s) for i, s in enumerate([
            "阮維亨", "福元", "阮貴公", "明心", "阮氏援", "妙全", "阮氏成", "妙就", "阮氏啓", "妙珙",
            "阮氏五", "瓊花", "黃德尊", "道軒", "陳氏蓮", "淑美", "黃德寵", "黃德事", "黃氏全", "阮登祝",
            "直敏", "裴氏元", "慈闈", "阮氏鍊", "淑義", "阮氏琬", "曇莊", "曇芝", "范文學", "直閏", "范氏魁",
            "春青", "范文院", "阮文科", "黃青早", "阮登芳", "福成", "阮登碩", "福掌", "阮登員", "直銓",
            "阮一郎", "早志", "阮氏淵", "妙泉", "阮文𩂏", "阮氏歡", "阮文溢", "阮氏樺", "阮文敬", "阮氏然",
            "阮文桂", "阮文蕙", "阮氏員", "阮文慧", "阮文錠"])],
        rels=[],
    ),
    9: dict(
        ents=[(f"p{i}", P, s) for i, s in enumerate([
            "直定", "阮氏節", "范廷韶", "范文筆", "范文攀", "范文章", "范文召", "阮登行", "武氏審", "阮氏榴",
            "慈桃", "阮氏通", "阮氏點", "阮氏劍", "阮氏杜", "青度", "范文法", "阮氏裕", "范氏養", "淑和", "阮氏紅"])]
        + [("d0", D, "皇朝維新六年歲在壬子秋月穀日"), ("writer", P, "阮金芝")],
        rels=[],
    ),
}

os.makedirs(os.path.join(OUT, "pages"), exist_ok=True)
stats = {"entities": 0, "relations": 0, "by_label": {}, "by_rel": {}}
errors = []
for n, spec in PAGES.items():
    src = json.load(open(os.path.join(SRC, f"{n:03d}.json"), encoding="utf-8"))
    text = src["hannom_text"]
    # Thực thể ghi theo thứ tự đọc; trang 7–9 liệt kê lẫn thứ tự dòng nên dò từ đầu, bỏ các vị trí đã dùng.
    used, ents, keyidx = [], [], {}
    pos = 0
    for key, label, s in spec["ents"]:
        i = text.find(s, pos)
        if i < 0:  # thử lại từ đầu, bỏ qua vị trí đã dùng
            i = -1
            start = 0
            while True:
                j = text.find(s, start)
                if j < 0:
                    break
                if not any(a < j + len(s) and j < b for a, b in used):
                    i = j
                    break
                start = j + 1
        if i < 0:
            errors.append(f"trang {n}: không tìm thấy {key} {s!r}")
            continue
        if any(a < i + len(s) and i < b for a, b in used):
            errors.append(f"trang {n}: chồng lấn {key} {s!r}")
            continue
        used.append((i, i + len(s)))
        assert text[i:i + len(s)] == s
        keyidx[key] = len(ents)
        ents.append({"start": i, "end": i + len(s), "label": label, "text": s})
        pos = i + len(s)
        stats["by_label"][label] = stats["by_label"].get(label, 0) + 1
    rels = []
    for typ, h, t, conf, cue in spec["rels"]:
        if h not in keyidx or t not in keyidx:
            errors.append(f"trang {n}: quan hệ thiếu thực thể {h}->{t}")
            continue
        rels.append({"type": typ, "head": keyidx[h], "tail": keyidx[t], "confidence": conf, "evidence": cue})
        stats["by_rel"][typ] = stats["by_rel"].get(typ, 0) + 1
    stats["entities"] += len(ents)
    stats["relations"] += len(rels)
    out = {
        "doc_id": "nom-429", "lang": "han", "page_number": n,
        "provenance": {"book_id": "nom-429", "scan_id": src["scan_id"], "page_id": f"{n:03d}",
                       "ocr_source": "giapha.kimtudien.com.vn, tải ngày 19/10/2026"},
        "source": "silver_claude",
        "hannom_text": text, "transliteration_text": src["transliteration_text"], "translation_text": src["translation_text"],
        "entities": ents, "relations": rels,
    }
    with open(os.path.join(OUT, "pages", f"{n:03d}.json"), "w", encoding="utf-8") as fh:
        json.dump(out, fh, ensure_ascii=False, indent=2)

print(json.dumps(stats, ensure_ascii=False))
print("\n".join(errors) if errors else "không lỗi")
