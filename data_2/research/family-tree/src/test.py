"""Load adapter LoRA đã train và thử trích xuất một đoạn gia phả mới.

    python src/test.py
    python src/test.py --adapter giapha_lora_adapter --text "Cụ tổ đời thứ nhất là ..."
"""
import argparse
import json
from pathlib import Path

from unsloth import FastLanguageModel

ROOT = Path(__file__).resolve().parent.parent
MAX_SEQ_LENGTH = 2048
INSTRUCTION = "Trích xuất thực thể và quan hệ gia phả từ văn bản sau. Trả về dạng JSON."

# Đoạn mới, không có trong train/test.
SAMPLE_TEXT = (
    "Cụ tổ đời thứ nhất của dòng họ Phùng là ông Phùng Văn Thạch (sinh năm 1862, mất năm 1931), "
    "quê ở làng Mông Phụ. Vợ ông là bà Kiều Thị Nhạn (sinh năm 1866, mất năm 1940). "
    "Hai ông bà sinh được hai người con là con trai Phùng Đức Khang (sinh năm 1888, mất năm 1952) "
    "và con gái Phùng Thị Lựu (sinh năm 1892, mất năm 1970). "
    "Ông Phùng Đức Khang lấy vợ là bà Đỗ Thị Mai (sinh năm 1891, mất năm 1965), "
    "sinh được con trai Phùng Văn Hải (sinh năm 1915, mất năm 1988)."
)


def build_prompt(text):
    return f"### Instruction:\n{INSTRUCTION}\n\n### Input:\n{text}\n\n### Response:\n"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--adapter", type=Path, default=ROOT / "giapha_lora_adapter")
    ap.add_argument("--text", default=SAMPLE_TEXT)
    ap.add_argument("--max-new-tokens", type=int, default=1536)
    args = ap.parse_args()

    # Thư mục adapter chứa adapter_config.json trỏ về model gốc; Unsloth tự tải model gốc 4bit.
    model, tokenizer = FastLanguageModel.from_pretrained(
        model_name=str(args.adapter),
        max_seq_length=MAX_SEQ_LENGTH,
        dtype=None,
        load_in_4bit=True,
    )
    FastLanguageModel.for_inference(model)

    inputs = tokenizer([build_prompt(args.text)], return_tensors="pt").to(model.device)
    out = model.generate(**inputs, max_new_tokens=args.max_new_tokens, do_sample=False,
                         eos_token_id=tokenizer.eos_token_id, pad_token_id=tokenizer.eos_token_id)
    answer = tokenizer.decode(out[0][inputs["input_ids"].shape[1]:], skip_special_tokens=True).strip()

    print("=== Input ===\n" + args.text)
    print("\n=== Output thô ===\n" + answer)
    try:
        data = json.loads(answer)
    except json.JSONDecodeError as e:
        print(f"\nKHÔNG parse được JSON: {e}")
        return
    print("\n=== JSON đã parse ===")
    print(json.dumps(data, ensure_ascii=False, indent=2))
    print(f"\nSố người: {len(data.get('persons', []))} | số quan hệ: {len(data.get('relations', []))}")


if __name__ == "__main__":
    main()
