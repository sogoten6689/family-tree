"""Đường dẫn corpus theo tầng nghiên cứu (00_raw … 05_ops).

Shortcut ở `data/vgp_corpus` (symlink) trỏ vào đây — lệnh cũ vẫn chạy.
"""

from __future__ import annotations

from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
DATA_ROOT = REPO_ROOT / "data"

# --- 00 raw ---
RAW_VGP_CORPUS = DATA_ROOT / "00_raw" / "vgp_corpus"
RAW_HANNOM = DATA_ROOT / "00_raw" / "hannom"
RAW_HANNOM_MOI = DATA_ROOT / "00_raw" / "du_lieu_han_nom_moi"
RAW_GIAPHATPHCM = DATA_ROOT / "00_raw" / "giaphatphcm"
HANNOM_CATALOG = RAW_HANNOM / "books_catalog.json"

# --- 01 interim ---
INTERIM_GEMINI_LABELS = DATA_ROOT / "01_interim" / "gemini_labels"
INTERIM_PRELABELS = DATA_ROOT / "01_interim" / "prelabels"
INTERIM_SYNTHETIC = DATA_ROOT / "01_interim" / "synthetic_pha_ky"
INTERIM_GIAPHATPHCM = DATA_ROOT / "01_interim" / "giaphatphcm"

# --- 02 gold ---
GOLD_LABELS = DATA_ROOT / "02_gold" / "gold_labels"
GOLD_STRATIFIED = GOLD_LABELS / "stratified_sample.json"
GOLD_V1_HUMAN = GOLD_LABELS / "v1_human"

# --- 03 derived ---
DERIVED_GIA_PHA = DATA_ROOT / "03_derived" / "gia_pha"
DERIVED_REVIEW_CORPUS = DATA_ROOT / "03_derived" / "review_corpus"
DERIVED_LABELED_CORPUS = DATA_ROOT / "03_derived" / "labeled_corpus"
DERIVED_MANIFESTS = DATA_ROOT / "03_derived" / "manifests"
CORPUS_INVENTORY_MD = DATA_ROOT / "DATA_INVENTORY.md"
CORPUS_INVENTORY_JSON = DERIVED_MANIFESTS / "corpus_inventory.json"

# --- 04 external ---
EXTERNAL_SACH = DATA_ROOT / "04_external" / "sach"

# --- 05 ops ---
OPS_LABEL_STUDIO = DATA_ROOT / "05_ops" / "label_studio"
OPS_SOURCES_DISCOVERY = DATA_ROOT / "05_ops" / "sources_discovery"
