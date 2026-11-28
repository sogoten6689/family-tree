"""Sinh dữ liệu gia phả tổng hợp (train 300 / test 50) theo format Alpaca.

Chạy từ gốc repo:
    python research/llm_extraction/generate_synthetic.py          # ghi đè data/01_interim/llm_synthetic/giapha_{train,test}.jsonl
    python research/llm_extraction/generate_synthetic.py <thư mục> # ghi ra thư mục khác
Seed cố định: chạy lại cho ra đúng hai file như cũ.
"""
import json
import random
import sys
from pathlib import Path

SEED = 20261127
rng = random.Random(SEED)

SURNAMES = ["Nguyễn", "Trần", "Lê", "Phạm", "Hoàng", "Huỳnh", "Phan", "Vũ", "Võ", "Đặng",
            "Bùi", "Đỗ", "Hồ", "Ngô", "Dương", "Lý", "Đinh", "Trịnh", "Lương", "Mai",
            "Tạ", "Cao", "Đoàn", "Lâm", "Trương", "Chu", "Hà", "Kiều", "Tô", "Quách"]
MALE_MID = ["Văn", "Đức", "Hữu", "Quang", "Minh", "Công", "Đình", "Xuân", "Bá", "Trọng",
            "Thanh", "Duy", "Quốc", "Tiến", "Mạnh", "Huy", "Khắc", "Doãn", "Đăng", "Ngọc"]
CLASSIC_MID = ["Đình", "Bá", "Trọng", "Khắc", "Doãn", "Hữu", "Đăng", "Công", "Văn", "Quý"]
MALE_GIVEN = ["An", "Bình", "Cường", "Dũng", "Đạt", "Định", "Đông", "Giang", "Hải", "Hào",
              "Hiển", "Hiếu", "Hòa", "Hùng", "Huy", "Khải", "Khang", "Khánh", "Khoa", "Kiên",
              "Lâm", "Lân", "Lộc", "Long", "Luân", "Mạnh", "Nam", "Nghĩa", "Nhân", "Ninh",
              "Phát", "Phong", "Phú", "Phúc", "Phương", "Quân", "Quý", "Sơn", "Tài", "Tâm",
              "Tân", "Thắng", "Thành", "Thịnh", "Thông", "Tiến", "Toàn", "Trí", "Trung", "Trường",
              "Tuấn", "Tùng", "Uy", "Việt", "Vinh", "Bảo", "Cảnh", "Chí", "Chiến", "Hậu",
              "Hưng", "Kha", "Kỳ", "Lương", "Nguyên", "Nhật", "Quyết", "Sang", "Thái", "Thiện",
              "Thuận", "Tín", "Tường", "Khiêm", "Liêm", "Cẩn", "Thạc", "Khôi", "Đoan", "Hoán",
              "Diễn", "Tuyển", "Khuê", "Bổng", "Chước", "Điển", "Hàm", "Kế", "Lạc", "Nhiêu"]
FEMALE_MID = ["Thị"] * 8 + ["Ngọc", "Thu", "Kim", "Thanh", "Bích", "Mỹ", "Diệu", "Hồng", "Phương"]
FEMALE_GIVEN = ["An", "Anh", "Bích", "Châu", "Chi", "Cúc", "Dung", "Duyên", "Đào", "Giang",
                "Hà", "Hạnh", "Hằng", "Hiền", "Hoa", "Hồng", "Huệ", "Hương", "Lan", "Liên",
                "Linh", "Loan", "Lụa", "Mai", "Mận", "My", "Nga", "Ngân", "Nguyệt", "Nhàn",
                "Nhung", "Oanh", "Phượng", "Quyên", "Quỳnh", "Sen", "Thảo", "Thắm", "Thoa", "Thu",
                "Thủy", "Thư", "Thương", "Trang", "Trinh", "Tuyết", "Uyên", "Vân", "Xuân", "Yến",
                "Gấm", "Huyền", "Lài", "Lệ", "Ly", "Mơ", "Nụ", "Tơ", "Ái", "Diệp", "Kiều", "Đoan",
                "Hảo", "Lựu", "Mùi", "Nhị", "Phấn", "Sương", "Tần", "Hiên"]
PLACES = ["làng Đông Ngạc", "xã Phù Lưu", "làng Kim Liên", "xã Hành Thiện", "làng Mộ Trạch",
          "xã Quỳnh Đôi", "làng Đường Lâm", "xã Tả Thanh Oai", "làng Bát Tràng", "xã Hoằng Lộc",
          "làng Phú Thị", "xã Diễn Châu", "làng Vạn Phúc", "xã Nghĩa Hưng", "làng Cổ Loa",
          "xã Thanh Chương", "làng Phước Tích", "xã Điện Bàn", "làng Minh Hương", "xã Cái Bè",
          "làng Thổ Hà", "xã Kiến Xương", "làng Hương Canh", "xã Yên Mô", "làng Dương Nỗ",
          "xã Tam Kỳ", "làng Chuông", "xã Quế Sơn", "làng Hành Cung", "xã Tiên Du",
          "phủ Thiệu Hóa", "huyện Thanh Liêm", "tổng Phù Lưu", "xã An Nhơn", "làng Lai Xá"]
TU = ["Mạnh Đạt", "Tử Kính", "Bá Ngọc", "Đức Nhuận", "Trọng Khiêm", "Tử Mỹ", "Văn Hiến",
      "Thúc Hòa", "Quý Thành", "Đạo Phủ", "Minh Trực", "Công Cẩn", "Hữu Lễ", "Tử Trung",
      "Bá Lân", "Đức Thuần", "Trọng Phu", "Thế Vinh", "Tử Nghi", "Doãn Đạt"]
HIEU = ["Tùng Am", "Mai Phong", "Liễu Trai", "Trúc Khê", "Cúc Ẩn", "Nam Sơn", "Thanh Hiên",
        "Bạch Vân", "Lan Đình", "Tĩnh Trai", "Hạc Đình", "Thạch Động", "Vân Hà", "Ngọa Long",
        "Đông Pha", "Nhất Trai", "Ẩn Phủ", "Hương Sơn", "Tùng Hiên", "Mặc Trai"]
CAN = ["Canh", "Tân", "Nhâm", "Quý", "Giáp", "Ất", "Bính", "Đinh", "Mậu", "Kỷ"]
CHI = ["Thân", "Dậu", "Tuất", "Hợi", "Tý", "Sửu", "Dần", "Mão", "Thìn", "Tỵ", "Ngọ", "Mùi"]
NUM = {1: "một", 2: "hai", 3: "ba", 4: "bốn", 5: "năm"}

USED_NAMES = set()


def can_chi(y):
    return f"{CAN[y % 10]} {CHI[y % 12]}"


def make_name(gender, surname, classic=False):
    for _ in range(1000):
        if gender == "male":
            mid = rng.choice(CLASSIC_MID if classic else MALE_MID)
            given = rng.choice(MALE_GIVEN)
        else:
            mid, given = rng.choice(FEMALE_MID), rng.choice(FEMALE_GIVEN)
        name = f"{surname} {mid} {given}"
        if mid != given and name not in USED_NAMES:
            USED_NAMES.add(name)
            return name
    raise RuntimeError("hết tên")


def other_surname(*avoid):
    return rng.choice([s for s in SURNAMES if s not in avoid])


def death_of(birth, has_kids=True):
    death = birth + rng.randint(56 if has_kids else 30, 92)
    return death if death <= 2025 else None


class Family:
    def __init__(self, classic=False, missing_prob=0.0):
        self.persons, self.rels, self.sents = [], [], []
        self.classic = classic
        self.missing_prob = missing_prob

    def add(self, name, gender, gen, true_birth, has_kids=True):
        """true_birth luôn có để tính năm đời sau; birth xuất ra có thể bị ẩn (null)."""
        death = death_of(true_birth, has_kids)
        shown = true_birth
        if self.missing_prob and gen <= 2 and rng.random() < self.missing_prob:
            shown = None
        p = {"name": name, "birth": shown, "death": death, "generation": gen,
             "gender": gender, "_b": true_birth}
        self.persons.append(p)
        return p

    def marry(self, husband, wife):
        self.rels.append({"from": husband["name"], "to": wife["name"], "type": "spouse"})

    def link(self, c, father=None, mother=None):
        kid = "son" if c["gender"] == "male" else "daughter"
        if father:
            self.rels.append({"from": father["name"], "to": c["name"], "type": "father"})
        if mother:
            self.rels.append({"from": mother["name"], "to": c["name"], "type": "mother"})
        if father:
            self.rels.append({"from": c["name"], "to": father["name"], "type": kid})
        if mother:
            self.rels.append({"from": c["name"], "to": mother["name"], "type": kid})

    # ---------- chữ ----------
    def yr(self, p):
        b, d = p["birth"], p["death"]
        if self.classic:
            if b is None and d is None:
                return rng.choice(["không rõ năm sinh năm mất", "năm sinh năm mất đều thất truyền"])
            if b is None:
                return rng.choice([f"năm sinh thất truyền, mất năm {can_chi(d)} ({d})",
                                   f"không rõ năm sinh, tạ thế năm {can_chi(d)} ({d})"])
            s = f"sinh năm {can_chi(b)} ({b})"
            if d:
                s += rng.choice([f", mất năm {can_chi(d)} ({d})", f", tạ thế năm {can_chi(d)} ({d})",
                                 f", quy tiên năm {can_chi(d)} ({d})"])
            return s
        if b is None and d is None:
            return "không rõ năm sinh"
        if b is None:
            return rng.choice([f"không rõ năm sinh, mất năm {d}", f"năm sinh không rõ, mất năm {d}"])
        if d is None:
            if b >= 1935:
                return rng.choice([f"sinh năm {b}", f"sinh năm {b}, hiện còn sống"])
            return f"sinh năm {b}, không rõ năm mất"
        return rng.choice([f"sinh năm {b}, mất năm {d}", f"sinh năm {b}, qua đời năm {d}",
                           f"{b} - {d}", f"{b}–{d}"])

    def ref(self, p):
        """'Tên (năm)' dùng khi liệt kê."""
        y = self.yr(p).replace(" (", " ").replace(")", "")
        return f"{p['name']} ({y})"

    def out(self):
        persons = [{k: v for k, v in p.items() if not k.startswith("_")} for p in self.persons]
        return {"persons": persons, "relations": self.rels}


def list_kids(fam, kids):
    parts, cnt = [], {"male": 0, "female": 0}
    for k in kids:
        male = k["gender"] == "male"
        n_same = sum(1 for x in kids if x["gender"] == k["gender"])
        i = cnt[k["gender"]]
        cnt[k["gender"]] += 1
        if fam.classic:
            w = ("trưởng nam" if male else "trưởng nữ") if i == 0 else ("thứ nam" if male else "thứ nữ")
        elif i == 0 and n_same > 1:
            w = "con trai trưởng" if male else "con gái đầu"
        else:
            w = "con trai" if male else "con gái"
        parts.append(f"{w} {fam.ref(k)}")
    return parts[0] if len(parts) == 1 else ", ".join(parts[:-1]) + " và " + parts[-1]


def make_kids(fam, surname, gen, father, mother, genders, start=None, names=None, classic=False):
    base = start if start is not None else (mother or father)["_b"] + rng.randint(19, 27)
    kids, year = [], base
    for i, g in enumerate(genders):
        b = min(year, 2018)
        name = names[i] if names and names[i] else make_name(g, surname, classic)
        kids.append(fam.add(name, g, gen, b, has_kids=False))
        year += rng.randint(2, 4)
    for k in kids:
        fam.link(k, father, mother)
    return kids


def rand_genders(n, first=None):
    gs = [rng.choice(["male", "male", "female"]) for _ in range(n)]
    if first:
        gs[0] = first
    return gs


def fit_sentences(sents, surname):
    sents = [s.strip().rstrip(".") for s in sents]
    while len(sents) > 6:  # gộp cặp kề nhau ngắn nhất
        i = min(range(len(sents) - 1), key=lambda j: len(sents[j]) + len(sents[j + 1]))
        sents[i:i + 2] = [sents[i] + "; " + sents[i + 1][0].lower() + sents[i + 1][1:]]
    place = rng.choice(PLACES)
    pool = [f"Gia phả này do chi trưởng họ {surname} lưu giữ",
            f"Mộ phần các cụ được an táng tại nghĩa trang {place}",
            f"Hằng năm con cháu họ {surname} về {place} giỗ tổ vào tháng Ba âm lịch",
            f"Từ đường của dòng họ hiện vẫn còn ở {place}"]
    rng.shuffle(pool)
    while len(sents) < 3:
        sents.append(pool.pop())
    return ". ".join(sents) + "."


# ======================= DỄ: 2-3 đời, 1 vợ, 4-6 người =======================
def build_easy():
    fam = Family()
    S, place = rng.choice(SURNAMES), rng.choice(PLACES)
    fb = rng.randint(1840, 1960)
    f = fam.add(make_name("male", S), "male", 1, fb)
    w = fam.add(make_name("female", other_surname(S)), "female", 1, fb + rng.randint(-1, 6))
    fam.marry(f, w)
    s = fam.sents
    s.append(rng.choice([
        f"Cụ tổ đời thứ nhất của dòng họ {S} là ông {fam.ref(f)}, quê ở {place}",
        f"Ông {fam.ref(f)} là người khai lập chi họ {S} tại {place}",
        f"Đời thứ nhất là cụ ông {fam.ref(f)}, người {place}",
    ]))
    s.append(rng.choice([f"Vợ ông là bà {fam.ref(w)}", f"Cụ bà là {fam.ref(w)}",
                         f"Ông lấy vợ là bà {fam.ref(w)}"]))
    if rng.random() < 0.55:  # 2 đời
        n = rng.randint(2, 4)
        kids = make_kids(fam, S, 2, f, w, rand_genders(n))
        s.append(rng.choice([f"Hai ông bà sinh được {NUM[n]} người con là {list_kids(fam, kids)}",
                             f"Ông bà có {NUM[n]} người con gồm {list_kids(fam, kids)}"]))
    else:  # 3 đời
        son = make_kids(fam, S, 2, f, w, ["male"])[0]
        s.append(rng.choice([f"Ông bà sinh được một người con trai là {fam.ref(son)}",
                             f"Con trai duy nhất của ông bà là {fam.ref(son)}"]))
        dau = fam.add(make_name("female", other_surname(S)), "female", 2, son["_b"] + rng.randint(-1, 5))
        fam.marry(son, dau)
        kids = make_kids(fam, S, 3, son, dau, rand_genders(rng.randint(1, 2)))
        s.append(rng.choice([
            f"Ông {son['name']} lấy vợ là bà {fam.ref(dau)}, sinh được {list_kids(fam, kids)}",
            f"Ông {son['name']} kết hôn với bà {fam.ref(dau)} và có {list_kids(fam, kids)}",
        ]))
    return fam, fit_sentences(s, S)


# ======================= TRUNG BÌNH: 4-5 đời, có dâu rể, 7-10 người =======================
def build_medium():
    fam = Family()
    S, place = rng.choice(SURNAMES), rng.choice(PLACES)
    G = rng.choice([4, 5])
    fb = rng.randint(1780, 1870) if G == 5 else rng.randint(1800, 1895)
    f = fam.add(make_name("male", S), "male", 1, fb)
    w = fam.add(make_name("female", other_surname(S)), "female", 1, fb + rng.randint(0, 6))
    fam.marry(f, w)
    s = fam.sents
    s.append(rng.choice([
        f"Thủy tổ họ {S} ở {place} là cụ {fam.ref(f)}, vợ là cụ bà {fam.ref(w)}",
        f"Đời thứ nhất là ông {fam.ref(f)} cùng vợ là bà {fam.ref(w)}, lập nghiệp tại {place}",
        f"Cụ tổ dòng họ {S} là ông {fam.ref(f)}, kết duyên với bà {fam.ref(w)}",
    ]))
    # mỗi đời giữa: con trai nối dõi + dâu; đời cuối: con cháu
    # G=4 'mid_re' : 7 cơ bản + con gái & rể ở đời giữa (+2) + tùy chọn 1 người -> 9-10
    # G=4 'last_re': 7 cơ bản + rể của cháu gái đời cuối (+1) -> 8
    # G=4 'ngoai'  : đời 3 là con gái + rể, đời 4 là cháu ngoại (họ rể) -> 7
    # G=5          : 9 cơ bản + rể của cháu gái đời 5 -> 10
    mode = rng.choice(["mid_re", "mid_re", "last_re", "ngoai"]) if G == 4 else "last_re"
    re_gen = rng.choice(range(2, G)) if mode == "mid_re" else None
    extra = rng.randint(0, 1) if mode == "mid_re" else 0
    father, mother, last_sur = f, w, S
    for g in range(2, G):
        if mode == "ngoai" and g == G - 1:
            d = make_kids(fam, S, g, father, mother, ["female"])[0]
            rs = other_surname(S)
            re = fam.add(make_name("male", rs), "male", g, d["_b"] + rng.randint(1, 6))
            fam.marry(re, d)
            s.append(rng.choice([
                f"Ông {father['name']} và bà {mother['name']} chỉ có một người con gái là {fam.ref(d)}, lấy chồng là ông {fam.ref(re)}",
                f"Đời thứ {g} chỉ có bà {fam.ref(d)}, con gái ông {father['name']}, gả cho ông {fam.ref(re)}",
            ]))
            father, mother, last_sur = re, d, rs
            continue
        seq = ["male"] + (["female"] if g == re_gen else [])
        if extra and rng.random() < 0.5:
            seq.append(rng.choice(["male", "female"]))
            extra -= 1
        rng.shuffle(seq)
        kids = make_kids(fam, S, g, father, mother, seq)
        heir = next(k for k in kids if k["gender"] == "male")
        dau = fam.add(make_name("female", other_surname(S)), "female", g, heir["_b"] + rng.randint(-2, 5))
        fam.marry(heir, dau)
        par = rng.choice([f"Ông {father['name']} và bà {mother['name']}", "Hai ông bà",
                          f"Vợ chồng ông {father['name']}"])
        sent = rng.choice([f"{par} sinh được {list_kids(fam, kids)}",
                           f"Đời thứ {g} gồm {list_kids(fam, kids)}"])
        sent += rng.choice([f"; ông {heir['name']} lấy vợ là bà {fam.ref(dau)}",
                            f"; con dâu là bà {fam.ref(dau)}, vợ ông {heir['name']}"])
        if g == re_gen:
            d = next(k for k in kids if k["gender"] == "female")
            re = fam.add(make_name("male", other_surname(S)), "male", g, d["_b"] + rng.randint(1, 6))
            fam.marry(re, d)
            sent += rng.choice([f"; bà {d['name']} lấy chồng là ông {fam.ref(re)}",
                                f"; bà {d['name']} gả cho ông {fam.ref(re)} ở {rng.choice(PLACES)}"])
        s.append(sent)
        father, mother = heir, dau
    # đời cuối
    seq = ["female"] if mode == "last_re" else rand_genders(1 + extra)
    kids = make_kids(fam, last_sur, G, father, mother, seq)
    lead = (f"Cháu ngoại đời thứ {G} là" if mode == "ngoai" else f"Đời thứ {G} có")
    sent = rng.choice([
        f"Ông {father['name']} và bà {mother['name']} sinh được {list_kids(fam, kids)}",
        f"{lead} {list_kids(fam, kids)}, con của ông {father['name']} và bà {mother['name']}",
    ])
    if mode == "last_re":
        d = kids[0]
        re = fam.add(make_name("male", other_surname(S)), "male", G, d["_b"] + rng.randint(1, 6),
                     has_kids=False)
        fam.marry(re, d)
        sent += rng.choice([f"; bà {d['name']} lấy chồng là ông {fam.ref(re)}",
                            f"; bà {d['name']} kết duyên với ông {fam.ref(re)}"])
    s.append(sent)
    return fam, fit_sentences(s, S)


# ======================= KHÓ =======================
# 2 vợ, con nuôi, con riêng, thiếu năm sinh, trùng tên khác đời, văn phong húy/tự/hiệu
def build_hard():
    feats = set(rng.sample(["two_wives", "adopted", "stepchild", "missing_birth", "dup_name"],
                           rng.randint(2, 4)))
    if "stepchild" in feats:
        feats.add("two_wives")
    fam = Family(classic=True, missing_prob=0.2 if "missing_birth" in feats else 0.0)
    S, place = rng.choice(SURNAMES), rng.choice(PLACES)
    fb = rng.randint(1700, 1880)
    f = fam.add(make_name("male", S, classic=True), "male", 1, fb)
    s = fam.sents
    s.append(rng.choice([
        f"Cụ tổ đời thứ nhất húy là {f['name']}, tự là {rng.choice(TU)}, hiệu là {rng.choice(HIEU)}, {fam.yr(f)}, người {place}",
        f"Thủy tổ họ {S} húy là {f['name']}, tự {rng.choice(TU)}, hiệu {rng.choice(HIEU)}, {fam.yr(f)}",
        f"Cụ ông húy là {f['name']}, hiệu là {rng.choice(HIEU)}, {fam.yr(f)}, gốc ở {place}",
    ]))
    w1 = fam.add(make_name("female", other_surname(S)), "female", 1, fb + rng.randint(0, 5))
    fam.marry(f, w1)
    w2 = None
    w2_title = rng.choice(["kế thất", "thứ thất", "trắc thất"])
    if "two_wives" in feats:
        w2 = fam.add(make_name("female", other_surname(S)), "female", 1, fb + rng.randint(8, 18))
        fam.marry(f, w2)
        s.append(rng.choice([
            f"Chính thất là bà {w1['name']}, {fam.yr(w1)}; {w2_title} là bà {w2['name']}, {fam.yr(w2)}",
            f"Cụ có hai bà vợ: chính thất húy là {w1['name']}, {fam.yr(w1)}, và {w2_title} là {w2['name']}, {fam.yr(w2)}",
        ]))
    else:
        s.append(rng.choice([f"Chính thất húy là {w1['name']}, {fam.yr(w1)}",
                             f"Cụ bà húy là {w1['name']}, {fam.yr(w1)}"]))
    k1 = make_kids(fam, S, 2, f, w1, rand_genders(rng.randint(1, 2), first="male"), classic=True)
    heir = k1[0]
    s.append(rng.choice([f"Bà chính thất sinh hạ {list_kids(fam, k1)}",
                         f"Cụ cùng bà {w1['name']} sinh được {list_kids(fam, k1)}"]))
    if w2:
        k2 = make_kids(fam, S, 2, f, w2, rand_genders(rng.randint(1, 2)), classic=True,
                       start=w2["_b"] + rng.randint(18, 24))
        s.append(rng.choice([f"Bà {w2_title} {w2['name']} sinh {list_kids(fam, k2)}",
                             f"Với bà {w2['name']}, cụ có thêm {list_kids(fam, k2)}"]))
    if "adopted" in feats:
        g = rng.choice(["male", "female"])
        sur = S if rng.random() < 0.6 else other_surname(S)
        a = fam.add(make_name(g, sur, classic=True), g, 2, heir["_b"] + rng.randint(-3, 6))
        fam.link(a, f, w1)
        s.append(rng.choice([f"Cụ và bà chính thất nhận {fam.ref(a)} làm con nuôi",
                             f"Ngoài ra hai cụ còn có người con nuôi là {a['name']}, {fam.yr(a)}"]))
    if "stepchild" in feats:
        g = rng.choice(["male", "female"])
        sc = fam.add(make_name(g, other_surname(S)), g, 2, w2["_b"] + rng.randint(16, 20))
        fam.link(sc, None, w2)
        s.append(rng.choice([
            f"Bà {w2['name']} trước đã có con riêng với chồng cũ là {sc['name']}, {fam.yr(sc)}",
            f"Khi về làm {w2_title}, bà {w2['name']} mang theo con riêng là {fam.ref(sc)}",
        ]))
    dau = fam.add(make_name("female", other_surname(S)), "female", 2, heir["_b"] + rng.randint(-1, 5))
    fam.marry(heir, dau)
    n3 = rng.randint(1, 2)
    if "dup_name" in feats:
        # cháu đích tôn (đời 3) trùng tên cụ tổ (đời 1): hai người khác nhau
        k3 = make_kids(fam, S, 3, heir, dau, rand_genders(n3, first="male"),
                       names=[f["name"]] + [None] * (n3 - 1), classic=True)
        tail = rng.choice(["; cháu đích tôn được đặt trùng tên với cụ tổ",
                           "; người cháu trưởng này trùng tên húy với cụ tổ đời thứ nhất"])
    else:
        k3 = make_kids(fam, S, 3, heir, dau, rand_genders(n3), classic=True)
        tail = ""
    s.append(rng.choice([
        f"Trưởng nam {heir['name']} lấy bà {dau['name']}, {fam.yr(dau)}, sinh hạ {list_kids(fam, k3)}{tail}",
        f"Ông {heir['name']} kết duyên cùng bà {dau['name']}, {fam.yr(dau)}; đời thứ ba có {list_kids(fam, k3)}{tail}",
    ]))
    if "missing_birth" in feats and all(p["birth"] is not None for p in fam.persons):
        return None  # yêu cầu thiếu năm sinh nhưng ngẫu nhiên không ẩn ai -> sinh lại
    return fam, fit_sentences(s, S)


MAX_CHARS = 3600  # ~ an toàn dưới 2048 token Qwen2.5 (ước lượng, cần đo lại)
INSTR = "Trích xuất thực thể và quan hệ gia phả từ văn bản sau. Trả về dạng JSON."


def to_record(fam, text):
    ans = json.dumps(fam.out(), ensure_ascii=False)
    return {"text": f"### Instruction:\n{INSTR}\n\n### Input:\n{text}\n\n### Response:\n{ans}"}


def gen(builder, n, seen):
    out = []
    while len(out) < n:
        snap = set(USED_NAMES)
        res = builder()
        if res is None:
            USED_NAMES.clear(); USED_NAMES.update(snap)
            continue
        fam, text = res
        if len(to_record(fam, text)["text"]) > MAX_CHARS:
            USED_NAMES.clear(); USED_NAMES.update(snap)
            continue
        if text in seen:
            continue
        seen.add(text)
        out.append(to_record(fam, text))
    return out


def main(outdir):
    outdir = Path(outdir)
    outdir.mkdir(parents=True, exist_ok=True)
    seen = set()
    # test sinh trước, tên dùng ở test không xuất hiện lại ở train (USED_NAMES toàn cục)
    test = gen(build_easy, 17, seen) + gen(build_medium, 17, seen) + gen(build_hard, 16, seen)
    train = gen(build_easy, 100, seen) + gen(build_medium, 100, seen) + gen(build_hard, 100, seen)
    rng.shuffle(train)
    rng.shuffle(test)
    for name, rows in (("giapha_train.jsonl", train), ("giapha_test.jsonl", test)):
        with open(outdir / name, "w", encoding="utf-8") as fh:
            for r in rows:
                fh.write(json.dumps(r, ensure_ascii=False) + "\n")
        print(name, len(rows))


if __name__ == "__main__":
    from _paths import SYNTH_DIR
    main(sys.argv[1] if len(sys.argv) > 1 else SYNTH_DIR)
