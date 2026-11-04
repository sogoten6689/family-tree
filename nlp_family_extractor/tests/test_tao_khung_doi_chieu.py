import pytest

from tools.tao_khung_doi_chieu import box_cells, char_box, locate_rows, merge_boxes, reading_order


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


def page_with_glyphs(tops, x0=100, size=20, height=300, width=300):
    """Ảnh giả: mỗi chữ là một ô mực vuông, cột dọc."""
    np = pytest.importorskip("numpy")
    ink = np.zeros((height, width), dtype=bool)
    for top in tops:
        ink[top : top + size, x0 : x0 + size] = True
    return ink


def test_cells_follow_ink_not_even_division():
    ink = page_with_glyphs([10, 40, 120])
    cells = box_cells({"box": [90, 0, 130, 200], "text": "公回改"}, ink)
    assert cells == [[100, 10, 120, 30], [100, 40, 120, 60], [100, 120, 120, 140]]


def test_neighbouring_column_inside_box_is_ignored():
    ink = page_with_glyphs([10, 40, 70])
    ink[0:100, 128:130] = True
    cells = box_cells({"box": [90, 0, 130, 100], "text": "公回改"}, ink)
    assert [c[2] for c in cells] == [120, 120, 120]


def test_broken_strokes_of_one_glyph_stay_together():
    np = pytest.importorskip("numpy")
    ink = np.zeros((100, 100), dtype=bool)
    ink[10:13, 20:40] = True  # 二: hai nét rời
    ink[20:23, 20:40] = True
    ink[45:65, 20:40] = True
    cells = box_cells({"box": [10, 0, 50, 90], "text": "二公"}, ink)
    assert cells == [[20, 10, 40, 23], [20, 45, 40, 65]]


def test_touching_glyphs_are_split_by_glyph_size():
    ink = page_with_glyphs([10, 30])
    assert [c[1] for c in box_cells({"box": [90, 0, 130, 60], "text": "公回"}, ink)] == [10, 30]


def test_located_chars_use_ink_cells_when_count_matches():
    ink = page_with_glyphs([10, 40, 120])
    chars, missing = locate_rows(["公回改"], [{"box": [90, 0, 130, 200], "text": "公回改"}], ink=ink)
    assert missing == 0
    assert [c["b"][1] for c in chars] == [10, 40, 120]
    assert all("u" not in c for c in chars)


def test_extra_glyph_on_image_keeps_paddle_position():
    ink = page_with_glyphs([10, 40, 70])
    chars, _ = locate_rows(["公改"], [{"box": [90, 0, 130, 100], "text": "公回改"}], ink=ink)
    assert [c["b"][1] for c in chars] == [10, 70]


def test_count_mismatch_is_marked_estimated():
    ink = page_with_glyphs([10])
    chars, _ = locate_rows(["公回"], [{"box": [90, 0, 130, 100], "text": "公回"}], ink=ink)
    assert all(c["u"] == 1 for c in chars)


def test_coarse_boxes_fill_empty_places_but_do_not_replace_better_reading():
    fine = [{"box": [0, 0, 10, 100], "text": "公"}]
    coarse = [{"box": [0, 0, 12, 100], "text": "甲"}, {"box": [50, 0, 90, 100], "text": "鄂"}]
    assert [b["text"] for b in merge_boxes(fine, coarse, "公鄂")] == ["公", "鄂"]


def test_coarse_reading_replaces_ornament_read_as_garbage():
    fine = [{"box": [90, 0, 110, 90], "text": "国国"}, {"box": [90, 100, 110, 190], "text": "面"}]
    coarse = [{"box": [0, 0, 110, 200], "text": "鄂氏宗譜"}]
    assert [b["text"] for b in merge_boxes(fine, coarse, "鄂氏宗譜")] == ["鄂氏宗譜"]


def test_parenthesis_on_image_takes_a_cell_but_gets_no_char():
    ink = page_with_glyphs([10, 40, 70, 100])
    box_ = {"box": [90, 0, 130, 130], "text": "公回改", "raw": "公(回改"}
    chars, _ = locate_rows(["公回改"], [box_], ink=ink)
    assert [c["b"][1] for c in chars] == [10, 70, 100]
    assert all("u" not in c for c in chars)


def test_small_real_box_on_cover_is_not_noise():
    title = {"box": [100, 0, 400, 1000], "text": "鄂氏宗譜"}
    small = {"box": [150, 1000, 250, 1200], "text": "卷之"}
    assert len(reading_order([title, small])) == 2
