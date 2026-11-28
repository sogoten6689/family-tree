"""Đường dẫn chung cho research/llm_extraction (chạy từ gốc repo hoặc từ worktree).

Repo dữ liệu `data/` không nằm trong git của repo chính; tìm nó bằng cách đi ngược lên
từ thư mục script (worktree của Claude nằm trong .claude/worktrees/ nên data/ ở cấp trên).
Đặt biến LLM_DATA_ROOT để chỉ định khác (ví dụ trên máy Vast.ai).
"""
import os
from pathlib import Path

HERE = Path(__file__).resolve().parent


def data_root() -> Path:
    env = os.getenv("LLM_DATA_ROOT")
    if env:
        return Path(env)
    for p in [HERE, *HERE.parents]:
        if (p / "data" / "03_derived").is_dir():
            return p / "data"
    return Path.cwd() / "data"


DATA = data_root()
SYNTH_DIR = DATA / "01_interim" / "llm_synthetic"          # dữ liệu tổng hợp (máy sinh)
VGP_DIR = DATA / "03_derived" / "llm_sft" / "v3_persons"   # bộ VGP theo schema persons/relations
ADAPTER_DIR = DATA / "03_derived" / "models" / "giapha_lora_adapter"
RUNS_DIR = DATA / "03_derived" / "models" / "giapha_lora_runs"
