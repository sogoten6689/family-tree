# Data Preparation for Fine-tuning SikuBERT & Phobert

**Purpose:** Convert annotated data → model-ready datasets  
**Outputs:** HuggingFace `datasets.Dataset` ready for `transformers` training  
**Languages:** Vietnamese (Phobert) + Hán-Nôm (SikuBERT)

---

## 1. Overview: Data Pipeline

```
Raw annotated texts (CONLL2003)
        ↓
Parse CONLL → Extract tokens + NER tags
        ↓
Tokenize with model tokenizer (Phobert/SikuBERT)
        ↓
Align NER tags to subword tokens
        ↓
Split train/val/test (80/10/10)
        ↓
Create HuggingFace Dataset
        ↓
Save to .arrow format (cache)
        ↓
Ready for training!
```

---

## 2. Step 1: Parse CONLL2003 Annotated Files

### 2.1 CONLL Format Review

**Input file:** `data/training/vietnamese_genealogy_ner.conll2003`

```
Nguyễn B-PERSON
Văn I-PERSON
An I-PERSON
sinh O
năm O
1945 B-YEAR
, O
kết O
hôn O
với O
bà O
Trần B-PERSON
Thị I-PERSON
Hạnh I-PERSON
. O

(blank line = sentence boundary)

Bà O
Phạm B-PERSON
...
```

### 2.2 Parsing Script

**File:** `nlp_family_extractor/tools/parse_conll_to_dataset.py`

```python
#!/usr/bin/env python3
"""
Parse CONLL2003 format → list of (tokens, ner_tags)
"""

from pathlib import Path
from typing import List, Tuple

def parse_conll_file(filepath: str) -> List[Tuple[List[str], List[str]]]:
    """
    Read CONLL file, return list of sentences.
    
    Returns:
        [(tokens, ner_tags), ...]
    """
    sentences = []
    current_tokens = []
    current_tags = []
    
    with open(filepath, 'r', encoding='utf-8') as f:
        for line in f:
            line = line.strip()
            
            if not line:  # Blank line = sentence boundary
                if current_tokens:
                    sentences.append((current_tokens, current_tags))
                    current_tokens = []
                    current_tags = []
                continue
            
            parts = line.split('\t')
            if len(parts) != 2:
                continue  # Skip malformed lines
            
            token, tag = parts
            current_tokens.append(token)
            current_tags.append(tag)
        
        # Don't forget last sentence if file doesn't end with blank line
        if current_tokens:
            sentences.append((current_tokens, current_tags))
    
    return sentences

# Usage
if __name__ == '__main__':
    data = parse_conll_file('data/training/vietnamese_genealogy_ner.conll2003')
    print(f"Parsed {len(data)} sentences")
    print(f"Example 1: {data[0]}")
```

**Output format:**
```python
[
    (['Nguyễn', 'Văn', 'An', 'sinh', 'năm', '1945', ',', ...], 
     ['B-PERSON', 'I-PERSON', 'I-PERSON', 'O', 'O', 'B-YEAR', 'O', ...]),
    
    (['Bà', 'Phạm', 'Thị', 'H', ...],
     ['O', 'B-PERSON', 'I-PERSON', 'I-PERSON', ...]),
    ...
]
```

---

## 3. Step 2: Tokenization & Alignment to Subword Tokens

**Problem:** Models like Phobert use **subword tokenizers** (WordPiece, SentencePiece)
- Input: `["Nguyễn", "Văn", "An"]` (word-level)
- Output: `["Nguyễn", "Văn", "An"]` (same, if words in vocab)
- **OR** `["Ng", "uyễn", "Văn", "An"]` (if Nguyễn not in vocab)

**Solution:** Align word-level NER tags to subword tokens

### 3.1 Tokenization & Alignment Script

**File:** `nlp_family_extractor/tools/tokenize_and_align.py`

```python
#!/usr/bin/env python3
"""
Tokenize sentences with model tokenizer.
Align word-level NER tags to subword tokens.
"""

from transformers import AutoTokenizer
from typing import List, Tuple, Dict

def tokenize_and_align_labels(
    sentences: List[Tuple[List[str], List[str]]],
    model_name: str = "vinai/phobert-base"  # or "SIKU-BERT/sikubert" for Chinese
) -> List[Dict]:
    """
    Tokenize + align NER tags.
    
    Args:
        sentences: [(tokens, ner_tags), ...]
        model_name: HuggingFace model ID
    
    Returns:
        [{"input_ids": [...], "attention_mask": [...], "labels": [...]}, ...]
    """
    
    tokenizer = AutoTokenizer.from_pretrained(model_name)
    
    # Build label→ID mapping
    label2id = {
        "O": 0,
        "B-PERSON": 1,
        "I-PERSON": 2,
        "B-YEAR": 3,
        "I-YEAR": 4,
        "B-RELATION_SPOUSE": 5,
        "B-RELATION_PARENT": 6,
        "B-RELATION_SIBLING": 7,
        "I-RELATION_SPOUSE": 8,
        "I-RELATION_PARENT": 9,
        "I-RELATION_SIBLING": 10,
    }
    id2label = {v: k for k, v in label2id.items()}
    
    processed = []
    
    for tokens, ner_tags in sentences:
        # Tokenize with word_ids tracking
        tokenized = tokenizer(
            tokens,
            truncation=True,
            max_length=512,
            is_split_into_words=True,  # Already word-tokenized
            return_tensors=None
        )
        
        # Get mapping: subword token index → word index
        word_ids = tokenized.word_ids()
        
        # Align labels
        labels = []
        previous_word_idx = None
        
        for word_idx in word_ids:
            if word_idx is None:
                # Special tokens ([CLS], [SEP], [PAD])
                labels.append(-100)  # Ignore in loss
            elif word_idx != previous_word_idx:
                # First subword of a word → use B- label
                original_tag = ner_tags[word_idx]
                labels.append(label2id[original_tag])
            else:
                # Continuation subword → use I- label (or same tag)
                original_tag = ner_tags[word_idx]
                if original_tag.startswith("B-"):
                    # Convert B- to I- for continuation
                    tag = "I-" + original_tag[2:]
                else:
                    tag = original_tag
                labels.append(label2id[tag])
            
            previous_word_idx = word_idx
        
        processed.append({
            "input_ids": tokenized["input_ids"],
            "attention_mask": tokenized["attention_mask"],
            "labels": labels,
            "token_type_ids": tokenized.get("token_type_ids", [0] * len(tokenized["input_ids"]))
        })
    
    return processed, label2id, id2label

# Usage
if __name__ == '__main__':
    from parse_conll_to_dataset import parse_conll_file
    
    sentences = parse_conll_file('data/training/vietnamese_genealogy_ner.conll2003')
    tokenized, label2id, id2label = tokenize_and_align_labels(
        sentences,
        model_name="vinai/phobert-base"
    )
    
    print(f"Tokenized {len(tokenized)} samples")
    print(f"Sample 1: {tokenized[0]}")
    print(f"Label mapping: {label2id}")
```

**Output format:**
```python
{
    "input_ids": [101, 16682, 11739, 6918, 8080, 5208, 16699, ...],  # [CLS] + token IDs
    "attention_mask": [1, 1, 1, 1, 1, 1, 1, ...],
    "labels": [-100, 1, 2, 2, 0, 0, 3, ...],  # -100 = ignore, 1=B-PERSON, 2=I-PERSON, etc.
    "token_type_ids": [0, 0, 0, ...]
}
```

**Key points:**
- Special tokens `[CLS]`, `[SEP]` → label `-100` (ignored in loss)
- First subword of word → original tag (B-PERSON, B-YEAR, etc.)
- Continuation subwords → I-variant (I-PERSON, I-YEAR, etc.)
- Max length → 512 (Phobert/SikuBERT limit)

---

## 4. Step 3: Train/Val/Test Split

**File:** `nlp_family_extractor/tools/split_dataset.py`

```python
#!/usr/bin/env python3
"""
Split dataset: 80% train, 10% val, 10% test.
Preserve sentence integrity (don't split within sentence).
"""

import random
from typing import List, Dict, Tuple

def split_dataset(
    tokenized_samples: List[Dict],
    train_ratio: float = 0.8,
    val_ratio: float = 0.1,
    test_ratio: float = 0.1,
    seed: int = 42
) -> Tuple[List[Dict], List[Dict], List[Dict]]:
    """
    Split dataset ensuring reproducibility.
    
    Args:
        tokenized_samples: List of tokenized samples
        train_ratio, val_ratio, test_ratio: Split proportions
        seed: Random seed for reproducibility
    
    Returns:
        (train_samples, val_samples, test_samples)
    """
    
    random.seed(seed)
    total = len(tokenized_samples)
    
    # Shuffle
    shuffled = tokenized_samples.copy()
    random.shuffle(shuffled)
    
    # Split indices
    train_end = int(total * train_ratio)
    val_end = train_end + int(total * val_ratio)
    
    train = shuffled[:train_end]
    val = shuffled[train_end:val_end]
    test = shuffled[val_end:]
    
    print(f"Train: {len(train)} ({len(train)/total*100:.1f}%)")
    print(f"Val:   {len(val)} ({len(val)/total*100:.1f}%)")
    print(f"Test:  {len(test)} ({len(test)/total*100:.1f}%)")
    
    return train, val, test
```

---

## 5. Step 4: Create HuggingFace Dataset

**File:** `nlp_family_extractor/tools/create_hf_dataset.py`

```python
#!/usr/bin/env python3
"""
Create HuggingFace Dataset from tokenized samples.
Save to .arrow format for caching.
"""

from datasets import Dataset, DatasetDict
from pathlib import Path

def create_huggingface_dataset(
    train_samples,
    val_samples,
    test_samples,
    label2id,
    id2label,
    output_dir: str = "data/datasets"
) -> DatasetDict:
    """
    Create HuggingFace DatasetDict.
    Save to disk for faster loading.
    """
    
    # Create datasets
    train_dataset = Dataset.from_dict({
        "input_ids": [s["input_ids"] for s in train_samples],
        "attention_mask": [s["attention_mask"] for s in train_samples],
        "token_type_ids": [s["token_type_ids"] for s in train_samples],
        "labels": [s["labels"] for s in train_samples],
    })
    
    val_dataset = Dataset.from_dict({
        "input_ids": [s["input_ids"] for s in val_samples],
        "attention_mask": [s["attention_mask"] for s in val_samples],
        "token_type_ids": [s["token_type_ids"] for s in val_samples],
        "labels": [s["labels"] for s in val_samples],
    })
    
    test_dataset = Dataset.from_dict({
        "input_ids": [s["input_ids"] for s in test_samples],
        "attention_mask": [s["attention_mask"] for s in test_samples],
        "token_type_ids": [s["token_type_ids"] for s in test_samples],
        "labels": [s["labels"] for s in test_samples],
    })
    
    # Combine into DatasetDict
    dataset_dict = DatasetDict({
        "train": train_dataset,
        "validation": val_dataset,
        "test": test_dataset,
    })
    
    # Save to disk
    Path(output_dir).mkdir(parents=True, exist_ok=True)
    dataset_dict.save_to_disk(output_dir)
    
    # Save metadata
    import json
    with open(f"{output_dir}/label_mappings.json", "w") as f:
        json.dump({"label2id": label2id, "id2label": id2label}, f, indent=2)
    
    print(f"Saved dataset to {output_dir}")
    print(f"Load with: datasets.load_from_disk('{output_dir}')")
    
    return dataset_dict
```

**Usage:**
```python
from datasets import load_from_disk

# Load saved dataset
dataset = load_from_disk("data/datasets/vietnamese_genealogy")

print(dataset)
# DatasetDict({
#     train: Dataset({...})
#     validation: Dataset({...})
#     test: Dataset({...})
# })

# Access a sample
print(dataset["train"][0])
```

---

## 6. Step 5: Data Validation Checklist

Before passing to training, verify:

```python
#!/usr/bin/env python3
"""
Validate dataset integrity.
"""

def validate_dataset(dataset_dict, label2id):
    """Check for common issues."""
    
    for split_name, split_data in dataset_dict.items():
        print(f"\n=== {split_name.upper()} ===")
        
        # Check 1: All samples have same keys
        keys = split_data.column_names
        assert keys == ["input_ids", "attention_mask", "token_type_ids", "labels"], \
            f"Unexpected columns: {keys}"
        
        # Check 2: Sequence lengths match
        for i, sample in enumerate(split_data):
            n_tokens = len(sample["input_ids"])
            n_mask = len(sample["attention_mask"])
            n_labels = len(sample["labels"])
            
            if not (n_tokens == n_mask == n_labels):
                print(f"ERROR: Sample {i} length mismatch!")
                print(f"  input_ids: {n_tokens}, attention_mask: {n_mask}, labels: {n_labels}")
                return False
        
        # Check 3: Valid label IDs
        all_labels = set()
        for sample in split_data:
            all_labels.update([l for l in sample["labels"] if l >= 0])
        
        max_label = max(all_labels)
        assert max_label < len(label2id), \
            f"Label {max_label} out of range (max: {len(label2id)-1})"
        
        # Check 4: Label distribution
        label_counts = {i: 0 for i in range(len(label2id))}
        for sample in split_data:
            for label in sample["labels"]:
                if label >= 0:
                    label_counts[label] += 1
        
        print(f"Samples: {len(split_data)}")
        print(f"Label distribution:")
        for label_id, count in label_counts.items():
            label_name = label2id[label_id] if label_id < len(label2id) else "UNK"
            print(f"  {label_name}: {count}")
    
    print("\n✓ Dataset validation passed!")
    return True
```

---

## 7. Complete Pipeline Script

**File:** `nlp_family_extractor/tools/prepare_training_data.py`

```python
#!/usr/bin/env python3
"""
End-to-end data preparation pipeline.
Usage: python prepare_training_data.py --input path/to/annotations.conll2003 \
                                       --output data/datasets/vietnamese_genealogy \
                                       --model vinai/phobert-base
"""

import argparse
from pathlib import Path

from parse_conll_to_dataset import parse_conll_file
from tokenize_and_align import tokenize_and_align_labels
from split_dataset import split_dataset
from create_hf_dataset import create_huggingface_dataset
from validate_dataset import validate_dataset

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", required=True, help="CONLL2003 file path")
    parser.add_argument("--output", required=True, help="Output directory for HF dataset")
    parser.add_argument("--model", default="vinai/phobert-base", 
                        help="Model name for tokenizer")
    parser.add_argument("--max-length", type=int, default=512)
    parser.add_argument("--seed", type=int, default=42)
    args = parser.parse_args()
    
    print("=" * 60)
    print("STEP 1: Parse CONLL file")
    print("=" * 60)
    sentences = parse_conll_file(args.input)
    print(f"✓ Parsed {len(sentences)} sentences")
    
    print("\n" + "=" * 60)
    print("STEP 2: Tokenize & align")
    print("=" * 60)
    tokenized, label2id, id2label = tokenize_and_align_labels(
        sentences,
        model_name=args.model
    )
    print(f"✓ Tokenized {len(tokenized)} samples")
    print(f"✓ Labels: {label2id}")
    
    print("\n" + "=" * 60)
    print("STEP 3: Split train/val/test")
    print("=" * 60)
    train, val, test = split_dataset(tokenized, seed=args.seed)
    
    print("\n" + "=" * 60)
    print("STEP 4: Create HuggingFace dataset")
    print("=" * 60)
    dataset_dict = create_huggingface_dataset(
        train, val, test,
        label2id, id2label,
        output_dir=args.output
    )
    
    print("\n" + "=" * 60)
    print("STEP 5: Validate")
    print("=" * 60)
    validate_dataset(dataset_dict, label2id)
    
    print("\n" + "=" * 60)
    print("✓ DONE! Ready for training")
    print("=" * 60)
    print(f"\nLoad dataset with:")
    print(f"  from datasets import load_from_disk")
    print(f"  dataset = load_from_disk('{args.output}')")

if __name__ == "__main__":
    main()
```

**Usage:**
```bash
# Vietnamese
python nlp_family_extractor/tools/prepare_training_data.py \
  --input data/training/vietnamese_genealogy_ner.conll2003 \
  --output data/datasets/vietnamese_genealogy \
  --model vinai/phobert-base

# Hán-Nôm
python nlp_family_extractor/tools/prepare_training_data.py \
  --input data/training/hannom_genealogy_ner.conll2003 \
  --output data/datasets/hannom_genealogy \
  --model SIKU-BERT/sikubert
```

---

## 8. Output Structure

```
data/datasets/
├── vietnamese_genealogy/
│   ├── dataset_info.json
│   ├── label_mappings.json
│   ├── train/
│   │   ├── dataset.arrow
│   │   ├── dataset_info.json
│   │   └── state.json
│   ├── validation/
│   │   └── ...
│   └── test/
│       └── ...
│
└── hannom_genealogy/
    ├── dataset_info.json
    ├── label_mappings.json
    ├── train/, validation/, test/
    └── ...
```

---

## 9. Data Preparation Checklist

Before training, verify:

- [ ] CONLL file parsed correctly (check sample sentences)
- [ ] Tokenization alignment successful (subword tokens match words)
- [ ] No -100 labels in middle of sequences (only at special tokens)
- [ ] Train/val/test split 80/10/10
- [ ] No data leakage (same text not in multiple splits)
- [ ] All labels have valid IDs (0 to len(label2id)-1)
- [ ] Dataset saved to disk (`.arrow` files exist)
- [ ] label_mappings.json created
- [ ] Validation script passed ✓

---

## 10. Next: Training Script

Once data is ready, use:

```python
# See: nlp_family_extractor/tools/finetune_phobert.py (to create)
# See: nlp_family_extractor/tools/finetune_sikubert.py (to create)

from transformers import (
    AutoModelForTokenClassification,
    TrainingArguments,
    Trainer,
    DataCollatorForTokenClassification
)
from datasets import load_from_disk

dataset = load_from_disk("data/datasets/vietnamese_genealogy")
# ... training code ...
```

---

**Document version:** 0.1  
**Status:** Ready for implementation  
**Timeline:** After annotation complete (Week 4+)
