# Phase 1: Annotation Data - Quick Start Guide

✅ **Doccano đã install xong!** Bắt đầu annotation ngay.

---

## 🚀 Quick Start (5 phút)

### 1️⃣ Start Doccano Server
```bash
cd nlp_family_extractor
source .venv/bin/activate
doccano init
doccano createuser --noinput --username admin --email admin@example.com --password admin123
doccano runserver 0.0.0.0:8001
```

Mở browser: **http://localhost:8001**

### 2️⃣ Đăng Nhập
- **Username:** `admin`
- **Password:** `admin123`

### 3️⃣ Tạo Project
1. Click **Create** → **New Project**
2. **Name:** `genealogy_vietnamese_v1`
3. **Type:** `Sequence labeling`
4. Click **Create**

### 4️⃣ Thêm Entity Labels
Project Settings → Labels:
```
PERSON           (Blue)
YEAR             (Orange)
RELATION_SPOUSE  (Cyan)
RELATION_PARENT  (Green)
RELATION_SIBLING (Purple)
```

### 5️⃣ Upload Sample Texts
Dataset → Import → Chọn `data/training/sample_vietnamese_texts.jsonl`

### 6️⃣ Bắt Đầu Annotate
Mở text đầu tiên → Highlight words → Chọn label → Save

---

## 📋 Entity Guidelines

### PERSON
- Tên người: "Nguyễn Văn An", "Trần Thị Hạnh"
- Highlight tên đầy đủ (cả mấy từ)

### YEAR
- Năm sinh/mất: "1945", "2000"
- Năm lunar: "嘉隆二十五年"
- Highlight toàn bộ năm

### RELATION_SPOUSE
- Chỉ tag từ chỉ vợ/chồng: "vợ", "chồng", "kết hôn", "lấy", "cưới"
- Không tag tên người

### RELATION_PARENT
- Chỉ tag từ chỉ cha/mẹ: "cha", "mẹ", "bố", "mẹ"
- Không tag tên người

### RELATION_SIBLING
- Chỉ tag từ chỉ anh/em: "anh", "em", "chị", "em trai", "anh trai"
- Không tag tên người

---

## ✅ Ví Dụ Annotation

### Original Text:
```
Ông Nguyễn Văn An sinh năm 1945, kết hôn với bà Trần Thị Hạnh sinh năm 1948.
```

### Correct Annotation:
```
Ông                      O
Nguyễn                   B-PERSON
Văn                      I-PERSON
An                       I-PERSON
sinh                     O
năm                      O
1945                     B-YEAR
,                        O
kết                      O
hôn                      O
với                      O
bà                       O
Trần                     B-PERSON
Thị                      I-PERSON
Hạnh                     I-PERSON
sinh                     O
năm                      O
1948                     B-YEAR
.                        O
```

---

## 🔄 Workflow

### Phase 1a: Calibration (1 tuần)
1. Upload 50 sample texts
2. 3-5 người cùng annotate
3. Tính Cohen's kappa (agreement)
4. Khi kappa ≥ 0.85 → Proceed

### Phase 1b: Main Annotation (3-4 tuần)
1. Upload 500-1000 Vietnamese texts
2. Team annotate cùng lúc
3. Doccano hỗ trợ collaborative

### Phase 1c: QA + Export (2-3 ngày)
1. Review annotations
2. Fix inconsistencies
3. Export JSONL → Convert CONLL

---

## 📊 Export & Convert to CONLL

### Step 1: Export from Doccano
Project → **Download** button → Format: **JSONL**

Save as: `vietnamese_annotations.jsonl`

### Step 2: Convert to CONLL 2003
```bash
cd nlp_family_extractor
source .venv/bin/activate

python tools/convert_doccano_to_conll.py \
  --input ../data/training/vietnamese_annotations.jsonl \
  --output ../data/training/vietnamese_genealogy_ner.conll2003
```

### Step 3: Verify CONLL Format
```bash
head -50 data/training/vietnamese_genealogy_ner.conll2003
```

Output sẽ là:
```
Nguyễn B-PERSON
Văn I-PERSON
An I-PERSON
sinh O
năm O
1945 B-YEAR
,    O
...
```

---

## 🎯 Success Criteria

**Calibration Round:**
- ✅ 50 texts annotated by 3+ people
- ✅ Cohen's kappa ≥ 0.85
- ✅ All entity types covered

**Main Annotation:**
- ✅ 500-1000 Vietnamese texts annotated
- ✅ CONLL file generated
- ✅ Ready for data prep pipeline (Phase 2)

---

## 📚 Next Steps

1. **Now:** Tạo project → Upload sample texts → Start calibration
2. **After calibration:** Upload full 1000 texts → Main annotation
3. **After annotation:** Export JSONL → Convert CONLL
4. **Phase 2:** Run data prep pipeline (tokenize, split, create .arrow)
5. **Phase 3:** Fine-tune models on GPU

---

## 🔗 Resources

- **Doccano Setup:** `docs/training/DOCCANO_SETUP.md`
- **Annotation Guidelines:** `docs/training/ANNOTATION_GUIDELINES.md`
- **Sample Texts:** `data/training/sample_vietnamese_texts.jsonl`
- **Conversion Script:** `nlp_family_extractor/tools/convert_doccano_to_conll.py`

---

## ❓ Troubleshooting

### Doccano không chạy
```bash
doccano runserver 0.0.0.0:8001
```

### Quên password
```bash
doccano changepassword admin
```

### Upload thất bại
- Check file format (JSONL)
- Check encoding (UTF-8)
- Check 1 text per line

---

**Bắt đầu ngay!** 🚀  
Chạy lệnh ở bước 1️⃣ để start Doccano server.
