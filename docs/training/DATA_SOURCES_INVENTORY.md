# Training Data Sources Inventory

**Purpose:** Identify & catalog genealogy texts for NER annotation  
**Target:** 500-1000 Vietnamese + 500-1000 Hán-Nôm texts  
**Status:** In progress (Phase 1)

---

## 1. Vietnamese Genealogy Sources

### 1.1 Internal: `data/vietnamgiapha/`

**Location:** `/Users/forestlam/Documents/projects/cao_hoc/source/family-tree/data/vietnamgiapha/`

**Contents (to verify):**
- [ ] Text files (.txt) or PDFs of Vietnamese genealogy
- [ ] Extracted genealogy passages from research corpus
- [ ] Scope: Family records, genealogy tables, historical texts

**Estimated count:** TBD (needs audit)

**Action items:**
- [ ] Run `find data/vietnamgiapha -type f | wc -l` to count files
- [ ] Sample 10-20 files to check format & quality
- [ ] Estimate total unique genealogy texts vs. duplicates

**Quality check:**
```bash
cd data/vietnamgiapha/
du -sh *                    # Size per file/folder
head -c 100 $(ls -1 | head -1)  # Preview format
file *                      # Check encoding (UTF-8?)
```

**Expected quality:**
- UTF-8 encoding (assume, needs verification)
- Contains person names, relationships, dates
- May have OCR errors (if scanned documents)

---

### 1.2 Internal: Research Corpus

**Location:** `research/`, `docs/`, existing notebooks

**Contents:**
- Existing genealogy annotation examples from previous work
- Meeting notes with family data examples
- Literature on Vietnamese genealogy structure

**Estimated count:** ~50-100 texts (scattered across docs)

**Action items:**
- [ ] Search for genealogy references: `grep -r "sinh năm\|kết hôn\|có con" research/ docs/`
- [ ] Extract unique genealogy passages
- [ ] De-duplicate

---

### 1.3 External: Public Vietnamese Genealogy Resources

**Candidates (need sourcing):**

| Source | Format | Size (est.) | Legal status | Effort |
|---|---|---|---|---|
| **Kimdien genealogy website** | HTML + PDF | ~500-1000 texts | Public data | High (scrape + clean) |
| **Vietnamese historical archives** | PDF + scans | ~100-200 texts | Public domain? | Medium (contact) |
| **genealogyasia.com** | HTML | ~200-500 texts | Public? | Medium (scrape) |
| GitHub genealogy projects | .txt, JSON | ~50-200 texts | MIT/GPL | Low (clone + extract) |

**Action items:**
- [ ] Check if Kimdien (kim từ điển) has public data export
- [ ] Search GitHub: `language:vietnamese genealogy site:github.com`
- [ ] Contact institutional archives (if permissions needed)

---

## 2. Hán-Nôm / Classical Chinese Genealogy Sources

### 2.1 Internal: Research Corpus

**Location:** `research/model_survey/` (CHAT_models evaluation)

**Contents:**
- `trial/houcunxiansheng.png` (Hán cổ scanned genealogy image)
- Evaluation logs with extracted Hán text
- Citations to 族谱 (Chinese genealogy) references

**Estimated count:** ~10-50 texts (mostly examples, not full corpus)

**Action items:**
- [ ] Extract Hán text from `EVALUATION.md` logs
- [ ] Look for OCR output from CHAT_models (if readable)
- [ ] Count unique genealogy passages

---

### 2.2 External: Public Hán Genealogy Repositories

**Candidates (harder to source):**

| Source | Format | Size (est.) | Legal status | Effort |
|---|---|---|---|---|
| **Chinese Genealogy Database** (族谱数字化) | JSON + CSV | ~500-2000 texts | Public domain (国家) | Medium (API access?) |
| **Wikisource 族谱** | Plain text (wiki) | ~100-300 texts | CC-by-SA 4.0 | Low (download) |
| **民国时期族谱** (Republican era) | PDF scans | ~200-500 texts | Historical archive | Medium-High (OCR) |
| **藏书阁 (digital library)** | PDF + ePub | ~500-1000+ texts | Copyright? | High (unclear) |

**Action items:**
- [ ] Search `site:wikisource.org 族谱` for downloadable texts
- [ ] Check if Chinese National Archives has genealogy collection
- [ ] Reach out to sinology/genealogy research groups for datasets

**Sourcing constraints:**
- Many Chinese genealogy databases are behind paywalls
- Copyright unclear on historical documents (pre-1949)
- May require institutional affiliation to access

---

## 3. Data Preparation Roadmap

### Phase 3.1a: Vietnamese Data (Week 1)

**Step 1: Audit internal sources**
```bash
# Count files in vietnamgiapha
find data/vietnamgiapha -type f \( -name "*.txt" -o -name "*.pdf" \) | wc -l

# Check encoding
file data/vietnamgiapha/* | grep -v "UTF-8"

# Search for genealogy keywords
grep -r "sinh năm\|kết hôn\|có con\|cha mẹ" data/vietnamgiapha | wc -l
```

**Expected outcome:** Estimate of usable Vietnamese texts from internal sources

**Step 2: Extract & deduplicate**
- Use `tools/extract_genealogy_texts.py` (to create)
- Output: `data/training/vietnamese_raw_texts.txt` (one genealogy passage per line)

**Step 3: Sample review**
- Randomly select 20 passages
- Read manually, check quality
- Estimate % OCR errors, missing data

**Target:** 500-1000 Vietnamese texts ready for annotation by end of Week 1

---

### Phase 3.1b: Hán-Nôm Data (Week 2-3)

**Step 1: Audit internal Hán sources**
- Extract from `research/model_survey/EVALUATION.md`
- Count readable passages
- Expected: ~20-50 texts

**Step 2: External sourcing**
- Query Wikisource for 族谱 downloads
- Contact sinology research groups (suggest: UC Berkeley East Asia Library, Beijing University)
- Document any licensing requirements

**Step 3: Data cleaning**
- Convert PDF scans → text (if OCR needed)
- Normalize character encoding (GBK → UTF-8)
- Flag uncertain/corrupted passages as [?]

**Target:** 500-1000 Hán texts (mix of sourced + synthesized) by end of Week 3

---

## 4. Data Format Specification

### 4.1 Raw Text Files

**Format:** Plain text, UTF-8 encoding, one genealogy passage per line

**File:** `data/training/vietnamese_raw_texts.txt`

```
Example:
Ông Nguyễn Văn An sinh năm 1945, kết hôn với bà Trần Thị Hạnh sinh năm 1948. Ông Nguyễn Văn An và bà Trần Thị Hạnh có con là Nguyễn Văn Bình sinh năm 1972, Nguyễn Thị Lan sinh năm 1975. Nguyễn Văn Bình cưới Lê Thị Hoa năm 1998, có con là Nguyễn Minh Đức sinh năm 2000.
Bà Phạm Thị H sinh năm 1930 kết hôn với ông Trần Văn K. Bà H mất năm 2001.
...
```

**Metadata file:** `data/training/vietnamese_raw_texts_meta.csv`

```
text_id,source,license,quality,notes
1,vietnamgiapha/file_001.txt,internal,high,
2,kimdien_scraped,cc-by,medium,OCR artifact in line 2
3,archive_contact,public_domain,high,Historical record 1850-1920
...
```

### 4.2 Annotated Files (Post-Annotation)

**Format:** CONLL 2003 for entities

**File:** `data/training/vietnamese_genealogy_ner.conll2003`

```
Nguyễn B-PERSON
Văn I-PERSON
An I-PERSON
sinh O
năm O
1945 B-YEAR
,  O
kết O
hôn O
với O
bà O
Trần B-PERSON
Thị I-PERSON
Hạnh I-PERSON
.  O

(blank line)

Bà O
Phạm B-PERSON
Thị I-PERSON
H I-PERSON
sinh O
...
```

**Relations file:** `data/training/vietnamese_genealogy_relations.jsonl`

```json
{"text_id": 1, "relation": {"type": "SPOUSE", "head": "Nguyễn Văn An", "tail": "Trần Thị Hạnh", "confidence": 1.0}}
{"text_id": 1, "relation": {"type": "PARENT", "head": "Nguyễn Văn An", "tail": "Nguyễn Văn Bình", "confidence": 1.0}}
...
```

---

## 5. Quality Metrics

### 5.1 Data Completeness

| Metric | Target | Vietnamese | Hán-Nôm |
|---|---|---|---|
| Total unique texts | 1000 total | 500 | 500 |
| Avg text length (words) | 50-200 | TBD | TBD |
| Coverage (% contain ≥1 person) | ≥90% | TBD | TBD |
| Coverage (% contain relations) | ≥80% | TBD | TBD |

### 5.2 Data Quality Checks

**Pre-annotation:**
- [ ] All texts UTF-8 encoded
- [ ] No encoding artifacts (mojibake)
- [ ] Sentence count ≥ 1 per text
- [ ] No duplicate texts

**Post-annotation:**
- [ ] IAA ≥ 0.85 (Cohen's kappa)
- [ ] 0 missing PERSON entities
- [ ] Relations correspond to actual entities
- [ ] Years are 4-digit or valid lunar calendar

---

## 6. Annotation Workload Estimate

### Vietnamese

**Effort:**
- 500 texts × ~5 min/text (experienced annotator) = 2500 min = ~42 hours
- With 2 annotators (IAA + speed): ~21 hours = ~5 person-days

**Tools:** Prodigy (recommended) or Doccano

**Cost:**
- Prodigy license: $400/year (split among team, negligible per person)
- Or free: Doccano (open source)

### Hán-Nôm

**Effort:**
- 500 texts × ~8 min/text (Hán slower due to character complexity) = 4000 min = ~67 hours
- With 2 annotators: ~33 hours = ~8 person-days

**Bottleneck:** Sourcing data (sourcing > annotation effort here)

**Total annotation:** ~5 + 8 = **13 person-days** for both languages

---

## 7. Action Items & Timeline

### Week 1 (Vietnamese audit)
- [ ] Count files in `data/vietnamgiapha/`
- [ ] Sample 20 files, assess quality
- [ ] Create `tools/extract_genealogy_texts.py`
- [ ] Run extraction → `vietnamese_raw_texts.txt`
- [ ] Target: 500 Vietnamese texts ready

### Week 2-3 (Hán sourcing + Vietnamese annotation prep)
- [ ] Extract Hán texts from research corpus
- [ ] Contact external sources (Wikisource, archives)
- [ ] Set up annotation tool (Prodigy or Doccano)
- [ ] Calibration round: annotate 50 Vietnamese texts with team
- [ ] Calculate IAA, refine guidelines if needed
- [ ] Target: 500 Hán texts sourced, Vietnamese annotation infrastructure ready

### Week 4+ (Annotation phase)
- [ ] Annotate remaining Vietnamese texts (parallel with Hán sourcing)
- [ ] Monitor IAA weekly
- [ ] Spot-check 10% of completed texts
- [ ] Export to CONLL format

---

## Appendix: Tools & Scripts (To Create)

### `tools/extract_genealogy_texts.py`

```python
#!/usr/bin/env python3
"""
Extract genealogy passages from raw corpus.
Input: directory of .txt files
Output: one genealogy passage per line
"""

import os
import re
from pathlib import Path

def is_genealogy_passage(text):
    """Heuristic: contains names + dates/relations"""
    keywords = [
        r'sinh năm|mất năm|kết hôn|cưới|lấy',  # Vietnamese
        r'有子|娶|生|配偶|父母'  # Chinese
    ]
    return any(re.search(kw, text) for kw in keywords)

def extract_passages(text):
    """Split by sentence, keep genealogy-relevant ones"""
    sentences = re.split(r'[。！？\.\!\?]\s*', text)
    return [s.strip() for s in sentences if is_genealogy_passage(s)]

if __name__ == '__main__':
    input_dir = 'data/vietnamgiapha/'
    output_file = 'data/training/vietnamese_raw_texts.txt'
    
    passages = []
    for filepath in Path(input_dir).glob('**/*.txt'):
        with open(filepath, 'r', encoding='utf-8', errors='ignore') as f:
            text = f.read()
            passages.extend(extract_passages(text))
    
    with open(output_file, 'w', encoding='utf-8') as f:
        for passage in passages:
            f.write(passage + '\n')
    
    print(f"Extracted {len(passages)} passages → {output_file}")
```

---

## Document Status

| Section | Status | Notes |
|---|---|---|
| Vietnamese sources | ⏳ TBD | Awaiting `data/vietnamgiapha/` audit |
| Hán-Nôm sources | ⏳ TBD | Awaiting external sourcing effort |
| Annotation guidelines | ✅ DONE | See `ANNOTATION_GUIDELINES.md` |
| Extraction scripts | 🔲 TODO | Create `tools/extract_genealogy_texts.py` |
| Workload estimate | ✅ DONE | ~13 person-days total |

---

**Version:** 0.1  
**Last updated:** 2026-10-06  
**Requires:** L1+ (file creation + external research) for execution
