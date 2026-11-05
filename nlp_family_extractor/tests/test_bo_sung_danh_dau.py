import json

from tools.bo_sung_danh_dau import build_prompt, marked_rows, merge_suggestions, parse_reply

ROWS = [
    {"trang": "003", "han": "公回", "viet": "", "bo": False, "danh_dau": "chua_dich", "ma": "a1"},
    {"trang": "003", "han": "改[?]", "viet": "Đổi", "bo": False, "danh_dau": "ocr", "ma": "b2", "ghi_chu": "chữ thứ hai mờ"},
]


def test_only_marked_rows_with_code_and_not_dropped_are_sent():
    draft = {
        "rows": [
            *ROWS,
            {"trang": "003", "han": "姓", "viet": "Họ", "bo": False},
            {"trang": "004", "han": "名", "viet": "", "bo": True, "danh_dau": "ocr", "ma": "c3"},
            {"trang": "004", "han": "字", "viet": "", "bo": False, "danh_dau": "ocr"},
        ]
    }
    assert {page: [r["ma"] for r in rows] for page, rows in marked_rows(draft).items()} == {"003": ["a1", "b2"]}


def test_row_waiting_for_review_is_not_sent_again_but_dismissed_one_is():
    draft = {"rows": [ROWS[0], {**ROWS[1], "bo_goi_y": 1}]}
    pages = marked_rows(draft, {"a1": {"viet": "Đang chờ", "lan": 1}, "b2": {"viet": "Đã bỏ", "lan": 1}})
    assert [r["ma"] for r in pages["003"]] == ["b2"]


def test_prompt_carries_code_kind_text_and_reviewer_note():
    prompt = build_prompt(ROWS)
    for text in ("a1", "b2", "chua_dich", "ocr", "改[?]", "chữ thứ hai mờ"):
        assert text in prompt
    assert "{{" not in prompt


def test_untranslated_row_keeps_its_han_and_ocr_row_can_change_it():
    reply = 'JSON {"goi_y": [{"ma": "a1", "han": "公归", "viet": "Ông về"}, {"ma": "b2", "han": "改姓", "viet": "Đổi họ"}]}'
    assert parse_reply(reply, ROWS) == {"a1": {"viet": "Ông về"}, "b2": {"han": "改姓", "viet": "Đổi họ"}}


def test_broken_reply_keeps_good_items_and_ignores_unknown_codes():
    reply = '{"goi_y": [{"ma": "a1", "viet": "Ông về"}, {"ma": "b2", "han": "改姓", "viet": }, {"ma": "la", "viet": "Lạ"}]}'
    assert parse_reply(reply, ROWS) == {"a1": {"viet": "Ông về"}}
    assert parse_reply("(rỗng)", ROWS) == {}


def test_translation_mixed_with_han_is_dropped_but_han_is_kept():
    reply = json.dumps({"goi_y": [{"ma": "b2", "han": "改姓", "viet": "Đổi 姓"}]}, ensure_ascii=False)
    assert parse_reply(reply, ROWS) == {"b2": {"han": "改姓"}}


def test_merge_keeps_other_codes_and_counts_runs():
    old = {"a1": {"viet": "Cũ", "lan": 1, "luc": "x"}, "z9": {"viet": "Giữ", "lan": 2, "luc": "x"}}
    merged = merge_suggestions(old, {"a1": {"viet": "Mới"}, "b2": {"han": "改"}}, "y")
    assert merged["a1"] == {"viet": "Mới", "lan": 2, "luc": "y"}
    assert merged["b2"] == {"han": "改", "lan": 1, "luc": "y"}
    assert merged["z9"] == old["z9"]
