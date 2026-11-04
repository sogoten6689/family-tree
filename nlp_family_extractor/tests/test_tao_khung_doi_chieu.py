from tools.tao_khung_doi_chieu import char_box, locate_rows, reading_order


def box(text, x0=100, y0=0, x1=120):
    return {"box": [x0, y0, x1, y0 + 10 * len(text)], "text": text}


def test_char_box_divides_vertical_and_horizontal():
    assert char_box(box("公回"), 1) == [100, 10, 120, 20]
    assert char_box({"box": [0, 0, 40, 10], "text": "公回改姓"}, 2) == [20, 0, 30, 10]


def test_wrong_paddle_char_keeps_machine_text_and_position():
    chars, missing = locate_rows(["公回改姓名"], [box("公回X姓名")])
    assert missing == 0
    assert [c["c"] for c in chars] == list("公回改姓名")
    assert chars[2]["b"] == [100, 20, 120, 30]


def test_column_split_into_two_boxes_is_joined_in_order():
    chars, missing = locate_rows(["公回改姓"], [box("公回", y0=0), box("改姓", y0=50)])
    assert missing == 0
    assert [c["b"][1] for c in chars] == [0, 10, 50, 60]


def test_repeated_rows_take_different_boxes():
    chars, _ = locate_rows(["此公舊載", "此公舊載"], [box("此公舊載", x0=200, x1=220), box("此公舊載", x0=100, x1=120)])
    assert [c["b"][0] for c in chars] == [200] * 4 + [100] * 4


def test_unlocated_chars_are_counted_not_guessed():
    chars, missing = locate_rows(["公回", "九十多人"], [box("公回")])
    assert (len(chars), missing) == (2, 4)


def test_table_reads_right_page_then_left_tier_by_tier():
    upper_right = box("十一世", x0=800, y0=100, x1=820)
    lower_right = box("十二世", x0=900, y0=500, x1=920)
    left = box("十三世", x0=100, y0=100, x1=120)
    order = reading_order([left, lower_right, upper_right], gutter=(480, 520))
    assert [b["text"] for b in order] == ["十一世", "十二世", "十三世"]


def test_printed_gutter_and_specks_never_receive_text():
    gutter_box = box("鄂氏宗譜", x0=490, y0=100, x1=510)
    speck = {"box": [700, 0, 704, 4], "text": "公"}
    chars, missing = locate_rows(["鄂氏公回"], [gutter_box, speck, box("公回", x0=800, x1=820)], gutter=(480, 520))
    assert [c["c"] for c in chars] == ["公", "回"]
    assert chars[0]["b"][0] == 800
    assert missing == 2


def test_box_is_not_overfilled():
    narrow = {"box": [100, 0, 120, 40], "text": "公水回"}
    chars, missing = locate_rows(["公一二三四五六七八九回"], [narrow])
    assert (chars, missing) == ([], 11)


def test_page_with_almost_no_match_places_nothing():
    border = {"box": [100, 0, 120, 200], "text": "甲乙丙丁戊己庚辛壬癸"}
    assert locate_rows(["鄂氏宗譜卷之十"], [border]) == ([], 7)


def test_unmatched_box_at_page_edge_gets_nothing():
    chars, missing = locate_rows(["甲乙丙公回改姓名"], [box("丁戊己", x0=200, x1=220), box("公回改姓名")])
    assert [c["c"] for c in chars] == list("公回改姓名")
    assert missing == 3
