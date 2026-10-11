"""NER tiếng Việt: encoder đã fine-tune (PhoBERT hoặc XLM-RoBERTa), xuất ONNX int8, chạy bằng onnxruntime trên CPU.

Không cần torch/transformers. Tokenizer: PhoBERT → BPE cài lại thuần Python (đã đối chiếu ``PhobertTokenizer`` HF);
XLM-RoBERTa (có ``tokenizer.json`` trong thư mục model) → thư viện ``tokenizers`` (nhẹ, không cần transformers). Cách chia từ/câu phải KHỚP với lúc huấn luyện
(``research/label_studio_pipeline/export_conll.py``: mức âm tiết + dấu câu, câu kết thúc bằng ``.!?;`` hoặc xuống dòng,
tối đa 128 token/câu).

Thư mục model (``NER_MODEL_DIR_VI``) cần: ``model.int8.onnx``, ``label_list.json`` và MỘT trong hai bộ tokenizer:
``vocab.txt`` + ``bpe.codes`` (PhoBERT) hoặc ``tokenizer.json`` (XLM-R). ``model_card.json`` (nếu có) được trả trong ``info``.
"""

from __future__ import annotations

import json
import os
import re
import threading
from dataclasses import dataclass
from pathlib import Path
from typing import Optional, Sequence

_WORD_TOKEN = re.compile(r"(?:\w|[̀-ͯ])+|[^\w\s]", re.UNICODE)
_SENTENCE_END = frozenset(".!?;")
MAX_TOKENS_PER_SENTENCE = 128
MAX_SEQ_LEN = 256
_PIECE = re.compile(r"\S+\n?")


class NerUnavailable(RuntimeError):
    """Model chưa được triển khai (thiếu tệp / thiếu thư viện)."""


# --------------------------------------------------------------------------- tokenizer PhoBERT (BPE)


class PhobertBpe:
    """Cài lại ``PhobertTokenizer`` (vocab.txt + bpe.codes) — chỉ phần mã hoá một từ."""

    def __init__(self, vocab_file: Path, merges_file: Path):
        self.encoder = {"<s>": 0, "<pad>": 1, "</s>": 2, "<unk>": 3}
        for line in Path(vocab_file).read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if not line:
                continue
            word = line.rsplit(" ", 1)[0]
            self.encoder[word] = len(self.encoder)
        merges = Path(merges_file).read_text(encoding="utf-8").split("\n")[:-1]
        self.ranks = {tuple(m.split()[:-1]): i for i, m in enumerate(merges)}
        self._cache: dict[str, list[str]] = {}
        self.cls_id, self.pad_id, self.sep_id, self.unk_id = 0, 1, 2, 3

    def _bpe(self, token: str) -> list[str]:
        if token in self._cache:
            return self._cache[token]
        word = tuple(token[:-1]) + (token[-1] + "</w>",)
        pairs = {(a, b) for a, b in zip(word, word[1:])}
        if not pairs:
            self._cache[token] = [token]
            return [token]
        while True:
            bigram = min(pairs, key=lambda p: self.ranks.get(p, float("inf")))
            if bigram not in self.ranks:
                break
            first, second = bigram
            merged, i = [], 0
            while i < len(word):
                try:
                    j = word.index(first, i)
                except ValueError:
                    merged.extend(word[i:])
                    break
                merged.extend(word[i:j])
                i = j
                if word[i] == first and i < len(word) - 1 and word[i + 1] == second:
                    merged.append(first + second)
                    i += 2
                else:
                    merged.append(word[i])
                    i += 1
            word = tuple(merged)
            if len(word) == 1:
                break
            pairs = {(a, b) for a, b in zip(word, word[1:])}
        joined = "@@ ".join(word)[:-4]  # bỏ "</w>" ở cuối
        out = joined.split(" ")
        self._cache[token] = out
        return out

    def tokenize_word(self, word: str) -> list[str]:
        pieces: list[str] = []
        for part in _PIECE.findall(word):
            pieces.extend(self._bpe(part))
        return pieces

    def word_ids(self, word: str) -> list[int]:
        return [self.encoder.get(p, self.unk_id) for p in self.tokenize_word(word)] or [self.unk_id]


class HFTokenizerJson:
    """Tokenizer XLM-R/BERT-họ dùng ``tokenizer.json`` qua thư viện ``tokenizers`` (cùng kết quả ``AutoTokenizer``)."""

    def __init__(self, tokenizer_json: Path, config_json: Optional[Path] = None):
        from tokenizers import Tokenizer

        self._tok = Tokenizer.from_file(str(tokenizer_json))
        vocab = self._tok.get_vocab()
        self.cls_id, self.pad_id, self.sep_id, self.unk_id = (vocab.get(t, d) for t, d in (("<s>", 0), ("<pad>", 1), ("</s>", 2), ("<unk>", 3)))

    def word_ids(self, word: str) -> list[int]:
        return list(self._tok.encode(word, add_special_tokens=False).ids) or [self.unk_id]


def load_tokenizer(model_dir: Path):
    if (Path(model_dir) / "tokenizer.json").exists():
        return HFTokenizerJson(Path(model_dir) / "tokenizer.json")
    return PhobertBpe(Path(model_dir) / "vocab.txt", Path(model_dir) / "bpe.codes")


# --------------------------------------------------------------------------- chia từ / câu


@dataclass(frozen=True)
class Word:
    text: str
    start: int
    end: int


def split_words(text: str) -> list[Word]:
    return [Word(m.group(), m.start(), m.end()) for m in _WORD_TOKEN.finditer(text)]


def split_sentences(text: str, words: Sequence[Word], max_tokens: int = MAX_TOKENS_PER_SENTENCE) -> list[tuple[int, int]]:
    """Cùng quy tắc lúc huấn luyện (``line_breaks=split`` cho mức từ): hết câu ở ``.!?;`` hoặc khi sang dòng mới."""
    ranges, start = [], 0
    for i, w in enumerate(words):
        last = i == len(words) - 1
        newline = (not last) and "\n" in text[w.end:words[i + 1].start]
        if last or newline or w.text in _SENTENCE_END:
            ranges.append((start, i + 1))
            start = i + 1
    out = []
    for a, b in ranges:
        while b - a > max_tokens:
            out.append((a, a + max_tokens))
            a += max_tokens
        if a < b:
            out.append((a, b))
    return out


def bio_to_spans(tags: Sequence[str]) -> list[tuple[int, int, str]]:
    """BIO → [(đầu, cuối+1, nhãn)]; ``I-X`` mồ côi mở span mới (như lúc đánh giá)."""
    spans, start, cur = [], 0, None
    for i, tag in enumerate(list(tags) + ["O"]):
        prefix, _, label = tag.partition("-")
        if cur is not None and not (prefix == "I" and label == cur):
            spans.append((start, i, cur))
            cur = None
        if prefix in ("B", "I") and cur is None:
            start, cur = i, label
    return spans


# --------------------------------------------------------------------------- model


class NerModel:
    def __init__(self, model_dir: Path, *, session=None):
        self.model_dir = Path(model_dir)
        self.labels: list[str] = json.loads((self.model_dir / "label_list.json").read_text(encoding="utf-8"))
        self.tokenizer = load_tokenizer(self.model_dir)
        if session is None:
            try:
                import onnxruntime as ort
            except ImportError as error:  # pragma: no cover - phụ thuộc môi trường
                raise NerUnavailable("Thiếu thư viện onnxruntime") from error
            opts = ort.SessionOptions()
            opts.intra_op_num_threads = int(os.getenv("NER_THREADS", "4"))
            session = ort.InferenceSession(str(self.model_dir / "model.int8.onnx"), opts, providers=["CPUExecutionProvider"])
        self.session = session
        card = self.model_dir / "model_card.json"
        self.info = json.loads(card.read_text(encoding="utf-8")) if card.exists() else {}

    def _encode(self, words: Sequence[Word]) -> tuple[list[int], list[int]]:
        ids, first = [self.tokenizer.cls_id], []
        for w in words:
            pieces = self.tokenizer.word_ids(w.text)
            if len(ids) + len(pieces) > MAX_SEQ_LEN - 1:
                break
            first.append(len(ids))
            ids.extend(pieces)
        ids.append(self.tokenizer.sep_id)
        return ids, first

    def predict_sentence(self, words: Sequence[Word]) -> tuple[list[str], list[float]]:
        import numpy as np

        ids, first = self._encode(words)
        x = np.array([ids], dtype=np.int64)
        logits = self.session.run(None, {"input_ids": x, "attention_mask": np.ones_like(x)})[0][0]
        e = np.exp(logits - logits.max(-1, keepdims=True))
        probs = e / e.sum(-1, keepdims=True)
        tags, conf = ["O"] * len(words), [0.0] * len(words)
        for k, pos in enumerate(first):
            idx = int(probs[pos].argmax())
            tags[k], conf[k] = self.labels[idx], float(probs[pos][idx])
        return tags, conf

    def extract(self, text: str) -> list[dict]:
        """Trả về danh sách thực thể: ``{label, text, start, end, confidence}`` (offset theo code point của ``text``)."""
        words = split_words(text)
        entities: list[dict] = []
        for a, b in split_sentences(text, words):
            sent = words[a:b]
            tags, conf = self.predict_sentence(sent)
            for s, e, label in bio_to_spans(tags):
                start, end = sent[s].start, sent[e - 1].end
                entities.append({
                    "label": label, "text": text[start:end], "start": start, "end": end,
                    "confidence": round(sum(conf[s:e]) / (e - s), 4),
                })
        return entities


# --------------------------------------------------------------------------- nạp một lần


_lock = threading.Lock()
_cache: dict[str, NerModel] = {}


def get_ner_model(language: str = "vi") -> NerModel:
    """Nạp model (một lần, an toàn đa luồng). Chưa cấu hình/thiếu tệp → ``NerUnavailable``."""
    env = {"vi": "NER_MODEL_DIR_VI"}.get(language)
    path = os.getenv(env, "") if env else ""
    if not path:
        raise NerUnavailable(f"Chưa cấu hình {env or 'model cho ngôn ngữ ' + language}")
    d = Path(path)
    need = ["model.int8.onnx", "label_list.json"] + ([] if (d / "tokenizer.json").exists() else ["vocab.txt", "bpe.codes"])
    missing = [n for n in need if not (d / n).exists()]
    if missing:
        raise NerUnavailable(f"Thiếu tệp model trong {d}: {', '.join(missing)}")
    with _lock:
        if path not in _cache:
            _cache[path] = NerModel(d)
        return _cache[path]
