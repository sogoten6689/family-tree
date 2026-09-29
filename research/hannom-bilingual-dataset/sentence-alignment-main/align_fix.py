# -*- coding: utf-8 -*-
"""Vá lỗi môi trường của Bertalign trên máy Mac này — import file này TRƯỚC
khi import bertalign (hoặc gọi apply() ở đầu script), rồi dùng bertalign như
bình thường (bertalign.Bertalign(..., is_split=True)).

2 lỗi đã gặp và fix khi chạy thật trên dữ liệu Hán-Việt (2026-09-14,
docx-nguyen-van 476/649 dòng):

1. Segfault khi encode NHIỀU câu cùng lúc (`model.encode(list_cau)`) —
   xung đột luồng OpenMP giữa torch và faiss (cả 2 cài qua pip, mỗi cái
   mang theo 1 bản libomp riêng). Encode TỪNG câu một (batch_size=1) né
   được, chỉ chậm hơn chứ không mất độ chính xác.
2. Segfault khi faiss tìm kiếm đa luồng trong bước align_sents() (dù đã
   fix (1)) — ép faiss + torch chạy đơn luồng né được nốt.

Không dùng `googletrans` để đoán ngôn ngữ (thư viện scrape Google Translate
không chính thức, hay gãy, lại cần mạng) — mình luôn biết trước Hán(zh)/
Việt(vi) nên tự đoán bằng ký tự CJK, không cần gọi mạng.

Dùng:
    import align_fix; align_fix.apply()
    import bertalign  # import SAU khi apply()
    aligner = bertalign.Bertalign(src=han_text, tgt=viet_text, is_split=True)
    aligner.align_sents()
"""
import os
import sys
import types

_applied = False


def apply():
    global _applied
    if _applied:
        return
    _applied = True

    # Phai set TRUOC khi import torch/faiss, neu khong bien nay vo tac dung.
    os.environ.setdefault("KMP_DUPLICATE_LIB_OK", "TRUE")

    # bertalign.utils co `from googletrans import Translator` o top-level —
    # stub module gia de import khong loi, vi ham detect_lang se bi ghi de
    # ben duoi, khong bao gio thuc su goi Translator().
    if "googletrans" not in sys.modules:
        fake_gt = types.ModuleType("googletrans")

        class _FakeTranslator:
            def __init__(self, *a, **k):
                pass

            def detect(self, text):
                raise RuntimeError("align_fix: khong dung googletrans, xem detect_lang_offline")

        fake_gt.Translator = _FakeTranslator
        sys.modules["googletrans"] = fake_gt

    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

    import bertalign.utils as bu
    import bertalign.aligner as ba
    import bertalign.encoder as be

    bu.detect_lang = _detect_lang_offline
    ba.detect_lang = _detect_lang_offline
    be.Encoder.transform = _transform_batch1

    import faiss
    import torch

    faiss.omp_set_num_threads(1)
    torch.set_num_threads(1)


def _detect_lang_offline(text):
    """Han co ky tu CJK (U+4E00-U+9FFF), Viet la Latin co dau — khong can
    goi mang de doan, vi du luon biet truoc 2 phia la gi."""
    for ch in text:
        if "一" <= ch <= "鿿":
            return "zh"
    return "vi"


def _transform_batch1(self, sents, num_overlaps):
    """Thay the Encoder.transform goc — giong het logic cu, chi doi
    encode(overlaps) -> encode(overlaps, batch_size=1) de tranh segfault."""
    import numpy as np
    from bertalign.utils import yield_overlaps

    overlaps = list(yield_overlaps(sents, num_overlaps))
    sent_vecs = np.asarray(self.model.encode(overlaps, batch_size=1))
    embedding_dim = sent_vecs.size // (len(sents) * num_overlaps)
    sent_vecs.resize(num_overlaps, len(sents), embedding_dim)

    len_vecs = [len(line.encode("utf-8")) for line in overlaps]
    len_vecs = np.array(len_vecs)
    len_vecs.resize(num_overlaps, len(sents))
    return sent_vecs, len_vecs
