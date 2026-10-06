# Doccano Setup Guide - NER Annotation

## ⚙️ Setup Doccano

### Option 1: Docker (Recommended)
```bash
docker run -d --name doccano -p 8001:8000 doccano/doccano:1.9.2
```

Truy cập: http://localhost:8001

### Option 2: Pip Installation
```bash
pip install doccano
doccano init
doccano createuser --noinput --username admin --email admin@example.com --password admin123
doccano runserver 0.0.0.0:8001
```

Truy cập: http://localhost:8001

### Option 3: Windows/Mac
https://github.com/doccano/doccano/releases → Download .exe/.dmg

---

## 📝 Tạo Project Cho Annotation

### Bước 1: Đăng Nhập
- URL: `http://localhost:8001`
- Username: `admin`
- Password: `admin123`

### Bước 2: Tạo Project Mới
1. Click **Create** → **New Project**
2. **Project Name:** `genealogy_vietnamese_v1`
3. **Description:** `Vietnamese genealogy NER annotation (CONLL 2003)`
4. **Task Type:** `Sequence labeling`
5. **Collaborative?** `Yes` (nếu team annotation)
6. Click **Create**

### Bước 3: Tạo Entity Labels

Tại project settings, thêm labels:

| Label | Color |
|---|---|
| **PERSON** | Blue (#1890ff) |
| **YEAR** | Orange (#ff7a45) |
| **RELATION_SPOUSE** | Cyan (#13c2c2) |
| **RELATION_PARENT** | Green (#52c41a) |
| **RELATION_SIBLING** | Purple (#722ed1) |
| **O** | (Không cần - default) |

---

## 📤 Upload Texts Để Annotate

### Chuẩn Bị File
Tạo `vietnamese_texts.jsonl`:
```jsonl
{"text": "Ông Nguyễn Văn An sinh năm 1945, kết hôn với bà Trần Thị Hạnh sinh năm 1948."}
{"text": "Nguyễn Văn Bình cưới Lê Thị Hoa năm 1998. Họ có con là Nguyễn Minh Đức sinh năm 2000."}
{"text": "Bà Phạm Thị H (sinh năm 1930) kết hôn với ông Trần Văn K. Bà H mất năm 2001."}
```

### Upload
1. Tại project → **Dataset** tab
2. Click **Import** → Chọn file `.jsonl`
3. Click **Upload**

---

## 🏷️ Annotation Workflow

### Tại Doccano Interface

1. **Trang Home** → Click project
2. **Click dòng text** để mở annotation editor
3. **Highlight text** → Chọn entity label
   - Ví dụ: Highlight "Nguyễn Văn An" → Click "PERSON"
   - Highlight "1945" → Click "YEAR"
   - Highlight "vợ" → Click "RELATION_SPOUSE"

4. **Entities sẽ hiển thị** bên phải:
   ```
   Nguyễn Văn An (PERSON)
   1945 (YEAR)
   vợ (RELATION_SPOUSE)
   Trần Thị Hạnh (PERSON)
   1948 (YEAR)
   ```

5. **Bấm Save** khi xong → Sang text tiếp theo

### Tips Annotation
- ✅ Highlight toàn bộ tên (nếu "Nguyễn Văn An" thì highlight cả 3 từ)
- ✅ Năm lunar: "嘉隆二十五年" → highlight toàn bộ = YEAR
- ✅ Vợ/chồng: chỉ tag từ "vợ", "chồng", "kết hôn", "lấy", "娶"
- ✅ Cha/mẹ: chỉ tag từ "cha", "mẹ", "bố", "mẹ", "父", "母"
- ✅ Không tag "là", "và", "có", "sinh"

---

## 📊 Calibration Round (QA)

### Mục tiêu
- 3-5 người annotate **50 cùng 1 texts**
- Tính **Cohen's kappa** (agreement level)
- Fix guidelines nếu kappa < 0.85

### Cách Tính
```python
from sklearn.metrics import cohen_kappa_score

# Ví dụ: 2 annotators, 50 texts
# result1, result2 = lists of entity sequences
kappa = cohen_kappa_score(result1, result2)
print(f"Cohen's kappa: {kappa:.2f}")

# 0.85+ = Excellent ✅
# 0.70-0.85 = Good (fix guidelines)
# < 0.70 = Redo calibration
```

### Output Calibration
Khi kappa ✅ ≥ 0.85:
- Agree trên annotation style
- Bắt đầu main annotation phase

---

## 💾 Export Data Để Convert CONLL

### Từ Doccano
1. Project → **Download** button
2. Format: `JSONL` or `CSV`
3. Download → `vietnamese_annotations.jsonl`

### Convert to CONLL 2003
```bash
python convert_doccano_to_conll.py \
  --input vietnamese_annotations.jsonl \
  --output vietnamese_genealogy_ner.conll2003
```

(Script trong `tools/` folder)

---

## 🔄 Workflow Tóm Tắt

```
1. Setup Doccano
   ↓
2. Tạo project → Upload 50 test texts
   ↓
3. Calibration: 3-5 người annotate → Tính kappa
   ↓
4. Nếu kappa >= 0.85 → Proceed
   Nếu < 0.85 → Fix guidelines → Redo calibration
   ↓
5. Main Annotation: Upload 1000 texts → Team annotate
   ↓
6. Export → Convert CONLL → Ready for data prep pipeline
```

---

## 🐛 Troubleshooting

### Doccano không chạy
```bash
# Check Docker
docker ps

# Hoặc chạy qua pip
pip install doccano
doccano runserver
```

### Quên password
```bash
doccano changepassword admin
```

### Port 8001 bị dùng
```bash
# Thay port khác (8888, 9000, etc.)
docker run -d -p 9000:8000 doccano/doccano
```

### Upload file thất bại
- Format phải là `.jsonl` (1 text per line)
- Encoding: UTF-8
- Không có invalid JSON

---

## 📚 Tài Liệu Thêm

- Doccano Docs: https://doccano.github.io/doccano/
- CONLL 2003 Format: https://www.aclweb.org/anthology/W03-0419/
- Vietnamese NER: https://github.com/datquocnguyen/PhoNER_COVID

---

**Status:** Ready to annotate ✅  
**Next:** Upload test texts → Start calibration round
