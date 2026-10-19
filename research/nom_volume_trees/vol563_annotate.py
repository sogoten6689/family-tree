"""Gán nhãn NER/RE (silver, Claude) cho vol 563 và ghi pages/NNN.json qua engine.run.

Mỗi trang: thực thể theo thứ tự xuất hiện trong hannom_text (key, nhãn, chuỗi đúng nguyên văn OCR);
quan hệ: (loại, key đầu, key cuối, độ tin cậy, căn cứ). Nhiều trang OCR đảo thứ tự dòng: thực thể
vẫn liệt kê theo vị trí trong chuỗi, còn quan hệ đọc theo nghĩa (ghi rõ ở căn cứ).
Quan hệ gắn vào tên xuất hiện đầu tiên của mục theo thứ tự đọc (quy tắc H4).

  python -X utf8 research/nom_volume_trees/vol563_annotate.py data/00_raw/hannom/giapha_web_export_2026-10-19/563 data/03_derived/nom_volume_trees/563
"""
import json, os, sys

sys.path.insert(0, os.path.dirname(__file__))
from engine import run

SRC, OUT = sys.argv[1], sys.argv[2]

P, G, D, O, L = "PER_NAME", "GENERATION", "DATE", "ORDER", "LOC"

PAGES = {
    1: dict(
        ents=[
            ("d1", D, "洪德萬年之二十七春穀日"), ("luchanh", P, "阮力行"), ("xulieu", P, "樗庵"),
            ("g1", G, "曾祖"), ("tuhuu", P, "子有"), ("l1", L, "青威縣貝溪社"), ("l2", L, "金牌社玉璞村"),
            ("g2", G, "曾祖"), ("tuhuu2", P, "子有"), ("g3", G, "祖考"), ("binh", P, "阮炳"), ("binh2", P, "柄"),
            ("l3", L, "同究社"),
        ],
        rels=[
            ("FATHER_OF", "tuhuu2", "binh", "cao", "曾祖子有生祖考阮炳"),
        ],
    ),
    2: dict(
        ents=[
            ("o1", O, "長"), ("huutuong", P, "有象"), ("l1", L, "白石社"), ("o2", O, "次"), ("thuylan", P, "瑞麟"),
            ("l2", L, "義邦文溪村"), ("trangnguyen", P, "狀元公"), ("o3", O, "行肆男"), ("ngocmao", P, "黎氏"),
            ("ngocmao2", P, "玉"), ("g1", G, "第七紀"),
        ],
        rels=[
            ("MOTHER_OF", "ngocmao", "huutuong", "cao", "夫人黎氏…玉生二男，一長有象"),
            ("MOTHER_OF", "ngocmao", "thuylan", "cao", "夫人黎氏…生二男…次瑞麟"),
        ],
    ),
    3: dict(
        ents=[
            ("l1", L, "國威府寧山縣吾儕社"), ("loi", P, "阮氏磊"), ("truc", P, "阮直"), ("uyen", P, "氏婉"),
            ("trangnguyen", P, "狀元公"), ("baduong", P, "黃伯楊"), ("dinhvien", P, "阮廷圓"), ("thuc", P, "阮氏淑"),
        ],
        rels=[
            ("SPOUSE", "dinhvien", "thuc", "cao", "故阮廷圓妻阮氏淑"),
            ("SPOUSE", "baduong", "uyen", "cao", "黃伯楊妻阮氏婉"),
            ("FATHER_OF", "truc", "thuc", "cao", "緣親父前朝狀元公…故阮直 (văn khế anh chị em chia ruộng)"),
            ("FATHER_OF", "truc", "uyen", "cao", "緣親父前朝狀元公…故阮直"),
            ("MOTHER_OF", "loi", "thuc", "cao", "母…夫人故阮氏磊"),
            ("MOTHER_OF", "loi", "uyen", "cao", "母…夫人故阮氏磊"),
            ("SPOUSE", "truc", "loi", "vừa", "cha 阮直 và mẹ 阮氏磊 của cùng các con; OCR đảo dòng"),
        ],
    ),
    4: dict(
        ents=[
            ("mongung", P, "端真"), ("tutriet_huy", P, "子徹"), ("dontinh_huy", P, "敦靜"), ("tutriet", P, "莊凱"),
            ("dontinh", P, "端雅"), ("l1", L, "祝里"), ("silien", P, "吳士連"), ("trongdat", P, "仲達"),
            ("g1", G, "第六紀"), ("o1", O, "第四支"), ("g2", G, "第六紀"), ("o2", O, "第三支"),
            ("g3", G, "第六紀"), ("o3", O, "第二文"), ("thucthan", P, "淑慎"), ("tn1", P, "狀元公"), ("o4", O, "行貳男"),
            ("sungnghia", P, "崇義"), ("l2", L, "義邦社"), ("o5", O, "季男"), ("ngokhoi", P, "梧魁"),
            ("donnhien", P, "敦然"), ("l3", L, "義邦社"), ("tn2", P, "狀元公"), ("o6", O, "行參男"),
            ("tranthi", P, "陳氏"), ("l4", L, "文溪村"), ("l5", L, "貝溪"), ("mai", P, "氏梅"),
        ],
        rels=[
            ("FATHER_OF", "tn1", "tutriet", "vừa", "乃狀元公行貳男 (đứng ở cột Tử Triệt, 第六紀第二支; OCR ghi 文)"),
            ("FATHER_OF", "tutriet", "sungnghia", "vừa", "生一男崇義居義邦社 (cột Tử Triệt)"),
            ("FATHER_OF", "tutriet", "thucthan", "vừa", "女淑慎為聖宗皇帝美人 (cột Tử Triệt; khớp trang 40)"),
            ("FATHER_OF", "tn2", "dontinh", "vừa", "乃狀元公行參男 (cột Đôn Tĩnh, 第六紀第三支)"),
            ("FATHER_OF", "dontinh", "donnhien", "vừa", "一男敦然居義邦社 (cột Đôn Tĩnh)"),
            ("SPOUSE", "dontinh", "tranthi", "thấp", "美人陳氏 đứng cạnh 狀元公行參男; chưa rõ là vợ Đôn Tĩnh"),
            ("FATHER_OF", "silien", "trongdat", "thấp", "祝里進士吳士連之男 / 仲達: dòng rời, có thể không liền nhau"),
        ],
    ),
    5: dict(ents=[("l1", L, "西山")], rels=[]),
    6: dict(
        ents=[
            ("l1", L, "天長府西真縣"), ("l2", L, "安朗縣"), ("l3", L, "祝里"), ("silien", P, "吳士連"),
            ("vanloi", P, "阮文雷"), ("dieu", P, "氏銚"), ("o1", O, "長"), ("mai", P, "氏梅"), ("luchanh", P, "力行"),
            ("l4", L, "丹鳳縣茂和社"), ("l5", L, "洮江府"), ("xulieu", P, "樗寮先生"), ("giam", P, "鑒"),
            ("mai2", P, "氏梅"), ("bich", P, "氏璧"), ("d1", D, "正月二十日"), ("luchanh2", P, "力行"),
            ("l6", L, "洪府長津縣"), ("d2", D, "二十七年壬辰"), ("doandat", P, "阮允達"),
        ],
        rels=[
            ("FATHER_OF", "xulieu", "luchanh", "cao", "是樗寮先生之令嗣也力行"),
            ("SPOUSE", "luchanh", "dieu", "cao", "力行娶丹鳳縣茂和社望族阮文雷女氏銚"),
            ("FATHER_OF", "vanloi", "dieu", "cao", "阮文雷女氏銚"),
            ("MOTHER_OF", "dieu", "mai", "cao", "氏銚生女四人長曰氏梅"),
            ("FATHER_OF", "luchanh", "mai", "vừa", "con gái của vợ chồng Lực Hành – Thị Điệu"),
            ("FATHER_OF", "silien", "giam", "cao", "祝里先生吳士連季男…吳鑒 (OCR tách 吳 / 鑒 sang hai dòng)"),
            ("SPOUSE", "mai", "giam", "cao", "長曰氏梅嫁…吳鑒"),
            ("MOTHER_OF", "mai2", "bich", "cao", "氏梅生女氏璧"),
            ("FATHER_OF", "giam", "bich", "vừa", "con gái của vợ chồng Ngô Giám – Thị Mai"),
        ],
    ),
    7: dict(
        ents=[
            ("l1", L, "廣盛府"), ("o1", O, "長"), ("truc", P, "直"), ("tn", P, "狀元公"), ("o2", O, "次"), ("chan", P, "真"),
            ("tuniem", P, "慈念"), ("ductrinh", P, "德貞"), ("dothi", P, "杜氏"), ("tuthan", P, "杜修身居士"), ("trung", P, "澄"),
            ("nguyenho", P, "阮胡"), ("g1", G, "第五紀"), ("nhunot", P, "如訥"), ("chan2", P, "真"), ("l2", L, "義邦社"),
            ("d1", D, "乙亥年延年參月拾三日"),
        ],
        rels=[
            ("FATHER_OF", "tuthan", "ductrinh", "cao", "恭人號德貞杜氏乃杜修身居士…之女 (OCR đảo dòng)"),
            ("MOTHER_OF", "tuniem", "ductrinh", "cao", "正室號慈念之女"),
            ("MOTHER_OF", "ductrinh", "truc", "vừa", "(杜氏) 生二男長曰直是狀元公 (OCR đảo dòng)"),
            ("MOTHER_OF", "ductrinh", "chan", "vừa", "生二男…次曰真"),
            ("FATHER_OF", "chan2", "nhunot", "vừa", "真生 / 如訥 (hai dòng ngắn liền nhau)"),
        ],
    ),
    8: dict(
        ents=[
            ("l1", L, "涼源"), ("toannghia", P, "阮全義"), ("nao", P, "阮瑙"), ("baduong", P, "黃伯揚"), ("vien", P, "阮圓"),
            ("thuc", P, "阮氏淑"), ("tutriet", P, "阮子徹"), ("l2", L, "臨洮府"), ("luchanh", P, "阮力行"), ("dieu", P, "阮氏銚"),
            ("o1", O, "次女"), ("uyen", P, "阮氏婉"), ("l3", L, "玉札"), ("d1", D, "洪德六年捌月二十日"), ("toannghia2", P, "阮全義"),
        ],
        rels=[
            ("SPOUSE", "vien", "thuc", "cao", "阮圓妻阮氏淑"),
            ("SPOUSE", "luchanh", "dieu", "cao", "阮力行妻阮氏銚"),
            ("FATHER_OF", "tutriet", "toannghia2", "cao", "阮子徹親男同知府阮全義 (OCR đảo dòng; khớp trang 27)"),
        ],
    ),
    9: dict(
        ents=[
            ("thoitrung_hieu", P, "如愚居士"), ("thoitrung_ho", P, "阮公"), ("thoitrung", P, "時中"), ("l1", L, "安山縣茂社"),
            ("l2", L, "東蒙"), ("l3", L, "小洞夢村"), ("l4", L, "文溪村"), ("l5", L, "柴山"), ("d1", D, "紹平元年"),
        ],
        rels=[],
    ),
    10: dict(ents=[("l1", L, "西山"), ("l2", L, "鳳城")], rels=[]),
    11: dict(
        ents=[
            ("tn", P, "狀元公"), ("ductrinh", P, "德貞婆"), ("boikhe", P, "貝溪先生"), ("l1", L, "昧原"),
            ("d1", D, "延寧二年乙亥三月初十日"), ("dothi", P, "杜氏"), ("d2", D, "大和三年甲子五月十二日"),
        ],
        rels=[
            ("MOTHER_OF", "dothi", "tn", "vừa", "(狀元公) 母杜氏卒 (OCR đảo dòng)"),
            ("SPOUSE", "boikhe", "ductrinh", "vừa", "諡德貞婆合葬與貝溪先生 (hợp táng)"),
        ],
    ),
    12: dict(
        ents=[
            ("nhutong", P, "阮如宗"), ("d1", D, "洪德十六年乙巳二月二十日"), ("l1", L, "盛靈山"), ("tn", P, "狀元公"),
            ("l2", L, "寧山縣吾儕鄉"), ("truc", P, "阮直"), ("l3", L, "寧山縣吾儕社"), ("l4", L, "西山"),
        ],
        rels=[],
    ),
    13: dict(
        ents=[
            ("o1", O, "長女"), ("thuc", P, "阮氏淑"), ("o2", O, "次男"), ("tutriet", P, "阮子徹"), ("o3", O, "兄"),
            ("l1", L, "臨洮府"), ("luchanh", P, "阮力行"), ("l2", L, "吾儕社金剛村"), ("l3", L, "吾儕社金剛村"),
            ("tutriet2", P, "阮子徹"), ("linh", P, "阮玲"),
        ],
        rels=[],
    ),
    14: dict(
        ents=[
            ("o1", O, "長"), ("nghian", P, "宜安"), ("luchanh_thuy", P, "敦簡"), ("luchanh_ho", P, "阮府君"),
            ("luchanh_huy", P, "力行"), ("luchanh", P, "炯"), ("l1", L, "洮江府"), ("o2", O, "仲男"), ("dontinh", P, "敦靜"),
            ("congsoan", P, "陶公僕"), ("congsoan_tu", P, "賓卿"), ("o3", O, "次室"), ("anh", P, "瓔"), ("anh_ho", P, "陶氏"),
            ("l2", L, "仙侶縣善片"), ("tusi", P, "杜子仕"), ("g1", G, "第六紀"), ("mongung", P, "端真"), ("o4", O, "次女"),
            ("kinh", P, "敬謹"), ("duychan", P, "阮維真"), ("uyen", P, "氏婉"), ("baduong", P, "黃伯陽"),
        ],
        rels=[
            ("FATHER_OF", "luchanh", "nghian", "vừa", "(阮公諱炯…力行) 生四男長錄事宜安 (OCR đảo dòng)"),
            ("FATHER_OF", "congsoan", "anh", "cao", "陶公僕字賓卿之女 (僕 là OCR của 僎)"),
            ("MOTHER_OF", "anh", "dontinh", "cao", "次室…諱瓔陶氏…之女生仲男少卿敦靜"),
            ("SPOUSE", "baduong", "uyen", "vừa", "氏婉 / 甲黃伯陽 (hai dòng ngắn liền nhau; khớp trang 3, 32)"),
        ],
    ),
    15: dict(ents=[("l1", L, "貝溪別墅"), ("hoanggian", P, "黃諫"), ("l2", L, "義邦")], rels=[]),
    16: dict(
        ents=[
            ("luchanh", P, "力行"), ("dontinh", P, "敦靜"), ("mongung", P, "夢應"), ("tn", P, "狀元公"), ("o1", O, "長子"),
            ("congsoan", P, "陶先生"), ("congsoan_huy", P, "公侯"), ("o2", O, "長女"), ("anh", P, "氏瓔"),
            ("thuc", P, "氏淑"), ("kinh", P, "氏敬"), ("uyen", P, "氏婉"), ("loi", P, "氏磊"), ("luchanh2", P, "力行"),
            ("loi2", P, "氏磊"), ("d1", D, "本年十一月二十日"), ("d2", D, "洪德二十一年庚戌六月十一日"),
            ("l1", L, "吾儕鄉"), ("uyminh", P, "威明皇太子"), ("loi3", P, "氏磊"), ("ngophuc", P, "遇福居士"),
            ("tinhniem", P, "淨念婆"),
        ],
        rels=[
            ("FATHER_OF", "ngophuc", "loi3", "cao", "氏磊父曰遇福居士"),
            ("MOTHER_OF", "tinhniem", "loi3", "cao", "母曰淨念婆"),
            ("MOTHER_OF", "loi", "luchanh2", "cao", "氏磊生男二長曰力行"),
            ("MOTHER_OF", "loi", "thuc", "cao", "(氏磊生) 女三長曰氏淑"),
            ("MOTHER_OF", "loi", "kinh", "cao", "次曰氏敬"),
            ("MOTHER_OF", "loi", "uyen", "cao", "又次氏婉"),
            ("FATHER_OF", "congsoan", "anh", "cao", "陶先生諱公侯之長女氏瓔 (公侯 là OCR của 公僎)"),
            ("MOTHER_OF", "anh", "dontinh", "cao", "氏瓔…生男二曰敦靜"),
            ("MOTHER_OF", "anh", "mongung", "cao", "生男二…曰夢應"),
            ("FATHER_OF", "tn", "luchanh", "cao", "狀元公長子曰力行"),
            ("SPOUSE", "tn", "anh", "vừa", "後娶…陶先生…之長女氏瓔 (chủ ngữ lược là Trạng nguyên)"),
        ],
    ),
    17: dict(ents=[("dichnha", P, "易牙"), ("banhac", P, "伯樂"), ("tancong", P, "晉公")], rels=[]),
    18: dict(
        ents=[
            ("l1", L, "極樂寺"), ("l2", L, "大賴村"), ("l3", L, "盛美山"), ("l4", L, "妹原"), ("l5", L, "美良縣"),
            ("d1", D, "十二月二十八日"), ("l6", L, "佛跡山庵"), ("truc_hieu", P, "樗寮"), ("truc_thuy", P, "公挺"),
            ("truc_ho", P, "阮公"), ("truc", P, "直"), ("d2", D, "丁酉年"),
        ],
        rels=[],
    ),
    19: dict(
        ents=[
            ("luchanh", P, "阮力行"), ("l1", L, "茂和"), ("loi", P, "阮雷"), ("dieu", P, "阮氏姚"), ("l2", L, "白石社"),
            ("l3", L, "義邦社"), ("letho", P, "黎壽"), ("hien", P, "氏賢"), ("vinhgia", P, "永嘉"), ("datlinh", P, "達領"),
            ("l4", L, "義邦"), ("khoi", P, "阮塊"), ("chiem", P, "氏占"), ("o1", O, "長男"), ("nghian", P, "宜安"),
            ("o2", O, "第四女"), ("phi", P, "氏妃"), ("o3", O, "第三女"), ("o4", O, "次女"), ("tung", P, "長松"),
            ("l5", L, "彰德縣古鴞社"), ("o5", O, "長女"), ("l6", L, "祝里"), ("silien", P, "吳士連"), ("o6", O, "季男"),
            ("thukhiem", P, "守謙"), ("quynh", P, "氏瓊"), ("nghian2", P, "宜安"), ("duong", P, "氏揚"),
            ("duysang", P, "阮維爽"), ("duysang_tu", P, "玄明"), ("nghian3", P, "阮宜安"), ("nghian3_tu", P, "福堂"),
        ],
        rels=[
            ("SPOUSE", "luchanh", "dieu", "cao", "阮力行娶茂和阮雷之女阮氏姚 (姚 là OCR của 銚)"),
            ("FATHER_OF", "loi", "dieu", "cao", "阮雷之女阮氏姚"),
            ("FATHER_OF", "letho", "hien", "cao", "黎壽之女曰氏賢"),
            ("SPOUSE", "luchanh", "hien", "vừa", "又妾義邦社黎壽之女曰氏賢 (chủ ngữ lược là Lực Hành)"),
            ("FATHER_OF", "khoi", "chiem", "cao", "阮塊之女曰氏占"),
            ("SPOUSE", "luchanh", "chiem", "vừa", "又妾義邦人阮塊之女曰氏占"),
            ("MOTHER_OF", "chiem", "vinhgia", "vừa", "氏占生二男 / 曰永嘉曰達領 (OCR đảo dòng)"),
            ("MOTHER_OF", "chiem", "datlinh", "vừa", "氏占生二男 / 曰永嘉曰達領"),
            ("FATHER_OF", "luchanh", "nghian", "vừa", "妾子長男曰宜安"),
            ("MOTHER_OF", "dieu", "phi", "vừa", "阮氏姚生四女…第四女氏妃"),
            ("MOTHER_OF", "dieu", "tung", "vừa", "生四女…次女長松 (長松 nghi là OCR của 氏松, khớp trang 32)"),
            ("FATHER_OF", "luchanh", "phi", "vừa", "con gái của Lực Hành"),
            ("FATHER_OF", "luchanh", "tung", "vừa", "con gái của Lực Hành"),
        ],
    ),
    20: dict(ents=[("d1", D, "大寶三年三月"), ("ho", P, "胡"), ("l1", L, "貝水")], rels=[]),
    21: dict(
        ents=[
            ("l1", L, "廣威府美良縣白石社大賴村"), ("d1", D, "洪德十五年甲辰七月二十三日"), ("l2", L, "義邦溪"),
            ("nguyenho", P, "阮胡"), ("l3", L, "順安府超類縣古珠"), ("l4", L, "昧原"), ("d2", D, "十一月丙申"), ("l5", L, "義邦"),
        ],
        rels=[],
    ),
    22: dict(
        ents=[
            ("l1", L, "南策上路"), ("d1", D, "太和二年"), ("thoitrung", P, "愚居士"), ("l2", L, "義邦社妹原"),
            ("tn", P, "狀元公"), ("d2", D, "五月初三日"), ("boikhe", P, "貝溪先生"), ("tn2", P, "狀元公"),
        ],
        rels=[],
    ),
    23: dict(
        ents=[
            ("l1", L, "義邦社"), ("nhantrung", P, "申公仁忠"), ("luchanh_thuy", P, "敦简"), ("hoangtu", P, "陳皇子"),
            ("ngophuc", P, "阮陳公"), ("ngophuc_tu", P, "遇福"), ("loi", P, "磊"), ("loi_ho", P, "阮陳氏"), ("l2", L, "吾儕"),
            ("tinhniem", P, "净念"), ("o1", O, "次"), ("tutriet", P, "子徹"), ("l3", L, "洮江"), ("luchanh", P, "力行"),
            ("thuc", P, "氏恭淑"),
        ],
        rels=[
            ("FATHER_OF", "ngophuc", "loi", "cao", "諱磊阮陳氏乃…阮陳公字遇福居士…之女 (OCR đảo dòng)"),
            ("MOTHER_OF", "tinhniem", "loi", "cao", "(正室號) 净念…之女"),
            ("MOTHER_OF", "loi", "luchanh", "cao", "生男長洮江同知府力行"),
            ("MOTHER_OF", "loi", "tutriet", "cao", "次六部尚書子徹"),
            ("MOTHER_OF", "loi", "thuc", "vừa", "女氏恭淑 (nghi là Thị Thục)"),
        ],
    ),
    24: dict(ents=[("d1", D, "壬戌科"), ("d2", D, "甲寅科"), ("duongphi", P, "楊妃"), ("l1", L, "香爐寺")], rels=[]),
    25: dict(ents=[], rels=[]),
    26: dict(
        ents=[
            ("chan", P, "真"), ("nhunot", P, "如訥"), ("tn", P, "狀元公"), ("o1", O, "長男"), ("cantho", P, "艮壽"),
            ("dothi", P, "杜氏"), ("hieu", P, "氏校"), ("l1", L, "廣威府"), ("o2", O, "長女"), ("hieu2", P, "氏校"),
            ("o3", O, "次"), ("chuyen", P, "氏專"), ("o4", O, "長"), ("truc", P, "直"), ("tn2", P, "狀元公"), ("o5", O, "次"),
            ("chan2", P, "真"), ("tuniem", P, "慈念婆"), ("dothi2", P, "杜氏"), ("l2", L, "貝溪別墅"), ("trung", P, "澄"),
            ("tuthan", P, "脩身居士"), ("l3", L, "義邦溪"), ("l4", L, "義邦社"), ("dothi3", P, "杜氏"), ("trung2", P, "氏澄"),
            ("l5", L, "白石縣"), ("l6", L, "寧山縣"), ("l7", L, "國成府"), ("l8", L, "義邦社小洞夢"),
        ],
        rels=[
            ("FATHER_OF", "chan", "nhunot", "cao", "真男曰如訥"),
            ("MOTHER_OF", "hieu", "cantho", "vừa", "氏校 / 長男曰艮壽 (OCR đảo dòng)"),
            ("MOTHER_OF", "dothi2", "truc", "cao", "杜氏生四子長曰直是狀元公"),
            ("MOTHER_OF", "dothi2", "chan2", "cao", "次曰真"),
            ("MOTHER_OF", "dothi2", "hieu2", "cao", "長女曰氏校"),
            ("MOTHER_OF", "dothi2", "chuyen", "cao", "次曰氏專"),
            ("FATHER_OF", "tuthan", "trung", "cao", "諱澄父曰脩身居士"),
            ("MOTHER_OF", "tuniem", "trung", "cao", "毋曰慈念婆"),
        ],
    ),
    27: dict(
        ents=[
            ("l1", L, "應天府清威縣貝溪社"), ("l2", L, "寧山縣義邦社"), ("l3", L, "臨泃府"), ("luchanh", P, "阮力行"),
            ("dieu", P, "阮氏銚"), ("tutriet", P, "阮子徹"), ("toannghia", P, "阮全義"),
        ],
        rels=[
            ("SPOUSE", "luchanh", "dieu", "cao", "故阮力行妻阮氏銚"),
            ("FATHER_OF", "tutriet", "toannghia", "cao", "故阮子徹親男阮全義"),
        ],
    ),
    28: dict(
        ents=[("tn", P, "狀元公"), ("tn2", P, "狀元公"), ("l1", L, "邦溪"), ("l2", L, "義邦社"), ("hoanggian", P, "黃諫")],
        rels=[],
    ),
    29: dict(
        ents=[
            ("canhthuan", P, "耿順"), ("xuandung", P, "春容"), ("quangvien", P, "光媛"), ("tn", P, "狀元公"), ("thuc", P, "氏淑"),
            ("l1", L, "義仁府清為縣"), ("tusi", P, "杜子仕"), ("thuc2", P, "氏淑"), ("toan", P, "氏全"), ("l2", L, "丹鳳縣"),
            ("l3", L, "山桐社"), ("huubang", P, "阮有朋"), ("o1", O, "長男"), ("huuquang", P, "阮有光"), ("o2", O, "次女"),
            ("kinh", P, "氏敬"), ("d1", D, "洪德元年庚寅"), ("kinh2", P, "謹敬"), ("d2", D, "二十三年戊子十一月二十四日"),
        ],
        rels=[
            ("FATHER_OF", "tn", "thuc", "cao", "狀元公女氏淑"),
            ("SPOUSE", "thuc", "tusi", "cao", "氏淑嫁茂材郎…知縣杜子仕 (mâu thuẫn với trang 3, 8: chồng là 阮廷圓)"),
            ("MOTHER_OF", "thuc2", "toan", "cao", "氏淑女曰氏全"),
            ("FATHER_OF", "tusi", "toan", "vừa", "con gái của vợ chồng Đỗ Tử Sĩ – Thị Thục"),
            ("SPOUSE", "toan", "huuquang", "cao", "氏全嫁…阮有朋之長男…阮有光"),
            ("FATHER_OF", "huubang", "huuquang", "cao", "阮有朋之長男…阮有光"),
            ("FATHER_OF", "tn", "kinh", "vừa", "次女曰氏敬 (tiếp mục con gái Trạng nguyên)"),
        ],
    ),
    30: dict(
        ents=[
            ("d1", D, "今年二月二十二日"), ("truc", P, "阮直"), ("d2", D, "大寶三年壬戌科二月二十二日"), ("d3", D, "紹平元年甲寅"),
            ("l1", L, "佛跡山龍斗庵"), ("dothi", P, "杜氏"), ("d4", D, "丁酉年五月十六日"),
        ],
        rels=[
            ("MOTHER_OF", "dothi", "truc", "vừa", "初杜氏以丁酉年五月十六日生狀元公 (狀元公 = 阮直 cùng trang)"),
        ],
    ),
    31: dict(ents=[("d1", D, "洪德五年甲午三月初五日"), ("l1", L, "奉天府廣德縣")], rels=[]),
    32: dict(
        ents=[
            ("o1", O, "第四女"), ("phi", P, "阮氏妃"), ("doantue", P, "阮允歲"), ("luchanh", P, "洮江府公"), ("o2", O, "第二女"),
            ("tung", P, "氏松"), ("phamtuyen", P, "范宣"), ("phamhoa", P, "范和"), ("o3", O, "第三女"), ("quantien", P, "冠仙"),
            ("nghiacuong", P, "義剛"), ("nghiaminh", P, "義明"), ("nghiacan", P, "義勤"), ("tuankhanh", P, "俊卿"),
            ("baduong", P, "黃伯楊"), ("o4", O, "第三女"), ("uyen", P, "氏婉"), ("luchanh2", P, "力行"), ("tien", P, "氏仙"),
            ("d1", D, "二十六年享卯三月初六日"), ("l1", L, "美良縣白石社碧按原"), ("baduong2", P, "黃伯揚"), ("l2", L, "廣威府"),
        ],
        rels=[
            ("FATHER_OF", "luchanh", "tung", "cao", "洮江府公第二女氏松"),
            ("MOTHER_OF", "tung", "phamtuyen", "cao", "氏松生范宣范和"),
            ("MOTHER_OF", "tung", "phamhoa", "cao", "氏松生范宣范和"),
            ("FATHER_OF", "luchanh", "quantien", "cao", "第三女冠仙侍景統皇帝"),
            ("FATHER_OF", "luchanh", "phi", "vừa", "第四女阮氏妃 (dòng 1 là phần tiếp của dòng 2)"),
            ("MOTHER_OF", "phi", "doantue", "cao", "阮氏妃生阮允歲中進士"),
            ("SPOUSE", "uyen", "baduong", "cao", "第三女曰氏婉嫁同鄉…黃伯楊"),
            ("FATHER_OF", "baduong", "nghiaminh", "cao", "黃伯楊生四男長曰義明"),
            ("FATHER_OF", "baduong", "nghiacan", "cao", "次曰義勤"),
            ("FATHER_OF", "baduong", "tuankhanh", "cao", "次曰俊卿"),
            ("FATHER_OF", "baduong", "nghiacuong", "cao", "次曰義剛"),
            ("FATHER_OF", "luchanh2", "tien", "cao", "力行女曰氏仙"),
        ],
    ),
    33: dict(ents=[("d1", D, "光順元年庚辰"), ("l1", L, "泠山")], rels=[]),
    34: dict(
        ents=[("truc", P, "貝溪樗寮先生"), ("l1", L, "鳳城"), ("d1", D, "洪德元年"), ("l2", L, "占城"), ("d2", D, "光順三年")],
        rels=[],
    ),
    35: dict(ents=[("d1", D, "延寧六年乙卯十月初三日"), ("truc", P, "樗寮先生")], rels=[]),
    36: dict(ents=[("d1", D, "太和二年"), ("l1", L, "南寨路")], rels=[]),
    37: dict(
        ents=[
            ("tn", P, "狀元公"), ("ngocmao", P, "氏玉帽"), ("o1", O, "長"), ("huutuong", P, "有象"), ("o2", O, "次"),
            ("thuylan", P, "瑞麟"), ("lechuong", P, "黎掌"), ("lekhang", P, "黎康"), ("tranduc", P, "陳昱"), ("tranhon", P, "陳昏"),
            ("mongung", P, "夢應"), ("tn2", P, "狀元公"), ("dontinh", P, "衰靜"), ("ichton", P, "阮益遜"),
            ("l1", L, "國威府丹鳳縣茂和社"),
        ],
        rels=[
            ("MOTHER_OF", "ngocmao", "huutuong", "cao", "黎氏玉帽生男二長曰有象"),
            ("MOTHER_OF", "ngocmao", "thuylan", "cao", "次曰瑞麟"),
            ("FATHER_OF", "lechuong", "ngocmao", "cao", "亞郡公黎掌女黎氏玉帽"),
            ("SPOUSE", "mongung", "ngocmao", "vừa", "夢應 (dòng 7 cuối) / …卿娶…黎掌女黎氏玉帽 (OCR đảo dòng)"),
            ("FATHER_OF", "mongung", "huutuong", "vừa", "con của vợ chồng Mộng Ứng – Ngọc Mạo"),
            ("FATHER_OF", "mongung", "thuylan", "vừa", "con của vợ chồng Mộng Ứng – Ngọc Mạo"),
            ("FATHER_OF", "tn2", "dontinh", "cao", "狀元公妾子衰靜 (衰 là OCR của 敦; mâu thuẫn với trang 16 về mẹ)"),
            ("SPOUSE", "dontinh", "tranhon", "vừa", "娶前禮部尚書故陳昱女孫陳昏"),
        ],
    ),
    38: dict(
        ents=[
            ("con", P, "氏衮"), ("tu", P, "嗣"), ("boikhe", P, "貝溪先生"), ("an", P, "氏恩"), ("an_hieu", P, "歸空婆"),
            ("l1", L, "貝溪社"), ("tu2", P, "嗣"), ("sulong", P, "師亮"), ("binh", P, "柄"), ("binh_hieu", P, "通智居士"),
            ("thoitrung", P, "時中"), ("boikhe2", P, "貝溪先生"), ("cai", P, "氏改"), ("luuthi", P, "劉氏"), ("l2", L, "塔滿村"),
            ("l3", L, "彰德縣"), ("thoitrung2", P, "時中"), ("l4", L, "廣威府美良縣純良"), ("an2", P, "氏恩"), ("cai2", P, "氏改"),
            ("an3", P, "氏恩"), ("thoitrung3", P, "時中"), ("xulieu", P, "樗寮"),
        ],
        rels=[
            ("MOTHER_OF", "an3", "thoitrung3", "cao", "觀之女曰氏恩生男曰時中"),
            ("FATHER_OF", "thoitrung3", "xulieu", "cao", "時中是為樗寮先生之父"),
            ("SPOUSE", "binh", "an", "vừa", "柄號通智居士 / 氏恩號歸空婆俱塟于貝溪社 (hợp táng; OCR đảo dòng)"),
            ("FATHER_OF", "tu2", "sulong", "cao", "嗣生師亮為縣通判"),
        ],
    ),
    39: dict(
        ents=[("l1", L, "貝溪別墅"), ("l2", L, "義邦"), ("boikhe", P, "貝溪先生"), ("l3", L, "佛跡山天構寺"), ("tn", P, "狀元公")],
        rels=[],
    ),
    40: dict(
        ents=[
            ("tutriet", P, "子徹"), ("cuctuong", P, "亟漿"), ("toannghia", P, "全義"), ("thucthan", P, "淑慎"), ("linh", P, "阮領"),
            ("thuctuong", P, "淑祥"), ("sungnghia", P, "崇義"), ("l1", L, "寧山縣黃舍社"), ("l2", L, "東閣縣"),
            ("d1", D, "洪德二十一年庚戌六月十日"), ("trinhthi", P, "鄭氏"), ("khoingo", P, "阮魁梧"), ("nghian", P, "阮宜安"),
            ("luchanh", P, "阮力行"),
        ],
        rels=[
            ("SPOUSE", "tutriet", "thuctuong", "vừa", "(子徹) 娶寧山縣黃舍社望族阮領之女曰淑祥 (OCR đảo dòng)"),
            ("FATHER_OF", "linh", "thuctuong", "cao", "阮領之女曰淑祥"),
            ("MOTHER_OF", "thuctuong", "sungnghia", "cao", "淑祥生男三長曰崇義"),
            ("MOTHER_OF", "thuctuong", "cuctuong", "cao", "次曰亟漿蚤亡"),
            ("MOTHER_OF", "thuctuong", "toannghia", "cao", "次曰全義"),
            ("MOTHER_OF", "thuctuong", "thucthan", "cao", "女三長曰淑慎"),
            ("FATHER_OF", "tutriet", "sungnghia", "vừa", "con của vợ chồng Tử Triệt – Thục Tường"),
            ("FATHER_OF", "tutriet", "cuctuong", "vừa", "con của vợ chồng Tử Triệt – Thục Tường"),
            ("FATHER_OF", "tutriet", "toannghia", "vừa", "con của vợ chồng Tử Triệt – Thục Tường"),
            ("FATHER_OF", "tutriet", "thucthan", "vừa", "con của vợ chồng Tử Triệt – Thục Tường"),
            ("MOTHER_OF", "trinhthi", "khoingo", "vừa", "又妾鄭氏女…生男阮魁梧"),
            ("FATHER_OF", "nghian", "khoingo", "thấp", "或疑是阮宜安之子 (sách ghi chỉ là nghi)"),
            ("FATHER_OF", "luchanh", "nghian", "vừa", "阮宜安…為阮力行之孫 → 宜安 là con Lực Hành"),
        ],
    ),
    41: dict(
        ents=[
            ("d1", D, "洪德四年癸巳十月十四日"), ("l1", L, "占城"), ("d2", D, "洪德元年庚寅十月十六日"), ("l2", L, "環碧亭"),
            ("truc", P, "樗寮"), ("l3", L, "鳳城"),
        ],
        rels=[],
    ),
    42: dict(
        ents=[
            ("boikhe", P, "貝溪先生"), ("l1", L, "邦溪"), ("boikhe2", P, "貝溪先生"), ("d1", D, "大寶二年辛酉九月二十四日"),
            ("d2", D, "二年乙卯九月十三日"), ("d3", D, "紹平元年甲寅九月初五日"), ("boikhe3", P, "貝溪先生"),
            ("nong", P, "氏農"), ("boikhe4", P, "貝溪先生"),
        ],
        rels=[],
    ),
    43: dict(
        ents=[
            ("d1", D, "光順八年丁亥"), ("tn", P, "狀元公"), ("l1", L, "西山草堂"), ("d2", D, "光順七年七月"), ("tn2", P, "狀元公"),
            ("l2", L, "大頼村"), ("l3", L, "廣成府美良縣"),
        ],
        rels=[],
    ),
    44: dict(
        ents=[
            ("binh_thuy", P, "文煥"), ("binh_ho", P, "阮公"), ("binh", P, "子炳"), ("tuhuu_thuy", P, "自彊"), ("tuhuu_ho", P, "阮公"),
            ("tuhuu", P, "子有"), ("boiam", P, "貝庵居士"), ("boiam_ho", P, "阮府君"), ("l1", L, "貝溪"), ("g3", G, "第三紀"),
            ("l2", L, "竦離處"), ("g2", G, "第二紀"), ("g4", G, "第四紀"), ("g1", G, "第一紀"),
        ],
        rels=[
            ("FATHER_OF", "boiam", "tuhuu_thuy", "vừa", "thế thứ: 第一紀 貝庵居士 → 第二紀 自彊…子有 (OCR đảo dòng)"),
            ("FATHER_OF", "tuhuu_thuy", "binh_thuy", "vừa", "thế thứ: 第二紀 子有 → 第三紀 文煥…子炳; khớp trang 1"),
        ],
    ),
}

stats, errors = run(PAGES, SRC, OUT, "nom-563", "giapha.kimtudien.com.vn (web ID 9), xuất ngày 19/10/2026")
print(json.dumps(stats, ensure_ascii=False))
print("\n".join(errors) if errors else "không lỗi")
