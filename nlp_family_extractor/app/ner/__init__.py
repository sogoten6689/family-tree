"""Suy luận NER bằng model đã huấn luyện (ONNX, chạy CPU). Xem docs/planning/NER_WORK_LOG.md."""

from app.ner.phobert_onnx import NerModel, NerUnavailable, get_ner_model

__all__ = ["NerModel", "NerUnavailable", "get_ner_model"]
