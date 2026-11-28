"""Fine-tune LoRA cho Qwen2.5-7B-Instruct bằng Unsloth để trích xuất gia phả.

Chạy trên GPU (ví dụ Vast.ai RTX 4090, 24 GB):
    python src/train.py
    python src/train.py --data data_train/giapha_train.jsonl --out giapha_lora_adapter
"""
import argparse
from pathlib import Path

# Unsloth phải được import trước transformers/trl để vá tối ưu.
from unsloth import FastLanguageModel, is_bfloat16_supported  # noqa: I001
from datasets import load_dataset
from trl import SFTTrainer

ROOT = Path(__file__).resolve().parent.parent
MODEL_NAME = "Qwen/Qwen2.5-7B-Instruct"
MAX_SEQ_LENGTH = 2048


def parse_args():
    ap = argparse.ArgumentParser()
    ap.add_argument("--data", type=Path, default=ROOT / "data_train" / "giapha_train.jsonl")
    ap.add_argument("--out", type=Path, default=ROOT / "giapha_lora_adapter")
    ap.add_argument("--model", default=MODEL_NAME)
    ap.add_argument("--seed", type=int, default=3407)
    return ap.parse_args()


def main():
    args = parse_args()

    model, tokenizer = FastLanguageModel.from_pretrained(
        model_name=args.model,
        max_seq_length=MAX_SEQ_LENGTH,
        dtype=None,          # tự chọn bf16 trên RTX 4090
        load_in_4bit=True,
    )

    model = FastLanguageModel.get_peft_model(
        model,
        r=16,
        lora_alpha=32,
        lora_dropout=0,
        target_modules=["q_proj", "k_proj", "v_proj", "o_proj",
                        "gate_proj", "up_proj", "down_proj"],
        bias="none",
        use_gradient_checkpointing="unsloth",
        random_state=args.seed,
    )

    # Mỗi mẫu đã là prompt hoàn chỉnh "### Instruction ... ### Response: {json}".
    # Thêm EOS để mô hình học cách dừng sau JSON.
    eos = tokenizer.eos_token
    dataset = load_dataset("json", data_files=str(args.data), split="train")
    dataset = dataset.map(lambda b: {"text": [t + eos for t in b["text"]]}, batched=True)

    n_tok = [len(tokenizer(t).input_ids) for t in dataset["text"]]
    print(f"Số mẫu: {len(dataset)} | token dài nhất: {max(n_tok)} | trung bình: {sum(n_tok) / len(n_tok):.0f}")
    if max(n_tok) > MAX_SEQ_LENGTH:
        print(f"CẢNH BÁO: có mẫu dài hơn {MAX_SEQ_LENGTH} token, sẽ bị cắt.")

    train_kwargs = dict(
        per_device_train_batch_size=2,
        gradient_accumulation_steps=4,
        num_train_epochs=3,
        learning_rate=2e-4,
        optim="adamw_8bit",
        warmup_steps=5,
        weight_decay=0.01,
        lr_scheduler_type="linear",
        fp16=not is_bfloat16_supported(),
        bf16=is_bfloat16_supported(),
        logging_steps=5,
        save_strategy="no",
        output_dir=str(ROOT / "outputs"),
        seed=args.seed,
        report_to="none",
    )

    try:
        # trl mới: SFTConfig (lớp con của transformers.TrainingArguments)
        from trl import SFTConfig
        sft_args = SFTConfig(dataset_text_field="text", max_seq_length=MAX_SEQ_LENGTH,
                             packing=False, **train_kwargs)
        trainer = SFTTrainer(model=model, tokenizer=tokenizer, train_dataset=dataset, args=sft_args)
    except (ImportError, TypeError):
        # trl cũ: TrainingArguments + tham số truyền thẳng vào SFTTrainer
        from transformers import TrainingArguments
        trainer = SFTTrainer(
            model=model,
            tokenizer=tokenizer,
            train_dataset=dataset,
            dataset_text_field="text",
            max_seq_length=MAX_SEQ_LENGTH,
            packing=False,
            args=TrainingArguments(**train_kwargs),
        )

    stats = trainer.train()
    print(f"Train xong: {stats.metrics}")

    args.out.mkdir(parents=True, exist_ok=True)
    model.save_pretrained(str(args.out))       # chỉ lưu adapter LoRA (~160 MB)
    tokenizer.save_pretrained(str(args.out))
    print(f"Đã lưu adapter vào {args.out}")


if __name__ == "__main__":
    main()
