# Kế hoạch build Rule-based Model cho bài toán trích xuất gia phả

## 1. Mục tiêu của Phase 1

Phase đầu tiên tập trung vào việc xây dựng một **rule-based extraction engine** bằng Python để trích xuất quan hệ gia phả từ văn bản tiếng Việt hiện đại.

Mục tiêu chính:

- Trích xuất được tên người trong câu.
- Xác định được quan hệ giữa các nhân vật.
- Chuẩn hóa output về dạng JSON hoặc graph edge.
- Tạo bộ test case và expected result.
- Làm baseline cho Phase 2: fine-tune model.

Ví dụ input:

```text
Nguyễn Văn A là cha của Nguyễn Văn B.
```

Expected output:

```json
{
  "source_person": "Nguyễn Văn A",
  "relation": "father_of",
  "target_person": "Nguyễn Văn B",
  "confidence": 1.0,
  "evidence": "Nguyễn Văn A là cha của Nguyễn Văn B"
}
```

---

## 2. Vì sao nên bắt đầu bằng Rule-based

Rule-based phù hợp với bài toán gia phả vì nhiều câu có cấu trúc rõ ràng:

```text
A là cha của B.
A là mẹ của B.
A là con của B.
A kết hôn với B.
A có con là B.
A sinh ra B.
A và B là anh em ruột.
```

Ưu điểm:

- Dễ kiểm soát logic.
- Dễ debug.
- Có thể tạo baseline ban đầu nhanh.
- Có thể dùng output rule-based để hỗ trợ tạo labeled dataset cho fine-tune.
- Giúp hiểu rõ pattern ngôn ngữ trong domain gia phả trước khi train model.

---

## 3. Phase tổng thể của dự án

Đề xuất chia thành 3 phase:

```text
Phase 1: Build rule-based extraction engine + labeled dataset
Phase 2: Fine-tune relation extraction model
Phase 3: Hybrid extraction + validation + graph construction
```

Trong đó:

- **Phase 1**: xây rule, schema, test cases, expected result.
- **Phase 2**: fine-tune model dựa trên dữ liệu đã chuẩn bị.
- **Phase 3**: kết hợp rule-based và model để tăng độ chính xác.

Hybrid flow đề xuất:

```text
Rule-based xử lý câu chắc chắn
Model xử lý câu phức tạp hoặc mơ hồ
Validator kiểm tra output cuối cùng
Graph builder dựng cây gia phả
```

---

## 4. Pipeline xử lý

Pipeline cơ bản:

```text
Input text
   ↓
Text normalization
   ↓
Sentence splitting
   ↓
Name / entity extraction
   ↓
Rule-based relation extraction
   ↓
Relation normalization
   ↓
Graph building
   ↓
Validation
   ↓
Output JSON / Database
```

Giải thích từng bước:

| Step                   | Mục đích                                              |
| ---------------------- | ----------------------------------------------------- |
| Text normalization     | Chuẩn hóa dấu câu, khoảng trắng, chữ hoa/thường       |
| Sentence splitting     | Tách đoạn văn thành từng câu                          |
| Entity extraction      | Nhận diện tên người                                   |
| Relation extraction    | Dùng regex/rule để bắt quan hệ                        |
| Relation normalization | Chuẩn hóa `cha`, `bố`, `ba` thành `father_of`         |
| Graph building         | Chuyển quan hệ thành node-edge                        |
| Validation             | Kiểm tra quan hệ bị trùng, sai chiều, thiếu thông tin |

---

---

## 5. Step 1: Define output schema

Trước khi viết rule, cần chốt schema output.

Schema đề xuất:

```json
{
  "source_person": "Nguyễn Văn A",
  "relation": "father_of",
  "target_person": "Nguyễn Văn B",
  "confidence": 1.0,
  "evidence": "Nguyễn Văn A là cha của Nguyễn Văn B",
  "rule_name": "father_of_pattern"
}
```

Python schema bằng Pydantic:

```python
from pydantic import BaseModel
from typing import Optional

class RelationExtracted(BaseModel):
    source_person: str
    relation: str
    target_person: str
    confidence: float = 1.0
    evidence: str
    rule_name: Optional[str] = None
```

Lý do nên có `evidence` và `rule_name`:

- Dễ debug rule nào đang bắt sai.
- Dễ trace lại câu gốc.
- Hữu ích khi tạo labeled dataset cho fine-tune.

---

## 6. Step 2: Define relation list

Ở MVP đầu tiên, chỉ nên bắt đầu với các quan hệ cơ bản.

```python
RELATION_TYPES = [
    "father_of",
    "mother_of",
    "child_of",
    "parent_of",
    "spouse_of",
    "sibling_of",
    "grandfather_of",
    "grandmother_of"
]
```

Sau này có thể mở rộng:

```python
EXTENDED_RELATION_TYPES = [
    "older_brother_of",
    "younger_brother_of",
    "older_sister_of",
    "younger_sister_of",
    "uncle_of",
    "aunt_of",
    "ancestor_of",
    "descendant_of"
]
```

Khuyến nghị:

- Phase đầu chỉ nên làm khoảng 5-8 relation.
- Ưu tiên độ chính xác trước.
- Không nên mở rộng quá sớm khi chưa có evaluator.

---

## 7. Step 3: Chuẩn hóa mapping quan hệ tiếng Việt

Tạo mapping giữa từ tiếng Việt và relation chuẩn.

```python
RELATION_KEYWORDS = {
    "father_of": ["cha", "bố", "ba", "thân phụ"],
    "mother_of": ["mẹ", "má", "thân mẫu"],
    "parent_of": ["phụ huynh", "cha mẹ"],
    "child_of": ["con", "con trai", "con gái"],
    "spouse_of": ["vợ", "chồng", "kết hôn", "lập gia đình"],
    "sibling_of": ["anh em", "chị em", "anh chị em"],
    "grandfather_of": ["ông nội", "ông ngoại"],
    "grandmother_of": ["bà nội", "bà ngoại"]
}
```

Lưu ý về chiều quan hệ:

```text
A là cha của B
=> A father_of B

A là con của B
=> A child_of B
```

Ở giai đoạn đầu, nên giữ relation theo đúng câu nói. Sau đó bước graph/validator có thể suy ra chiều ngược.

Ví dụ:

```text
A child_of B
=> B parent_of A
```

---

## 8. Step 4: Tạo test cases trước khi viết rule

Tạo file `data/test_cases.json`.

Ví dụ:

```json
[
  {
    "input": "Nguyễn Văn A là cha của Nguyễn Văn B.",
    "expected": [
      {
        "source_person": "Nguyễn Văn A",
        "relation": "father_of",
        "target_person": "Nguyễn Văn B"
      }
    ]
  },
  {
    "input": "Trần Thị C là mẹ của Nguyễn Văn B.",
    "expected": [
      {
        "source_person": "Trần Thị C",
        "relation": "mother_of",
        "target_person": "Nguyễn Văn B"
      }
    ]
  },
  {
    "input": "Nguyễn Văn A kết hôn với Trần Thị C.",
    "expected": [
      {
        "source_person": "Nguyễn Văn A",
        "relation": "spouse_of",
        "target_person": "Trần Thị C"
      }
    ]
  }
]
```

Nên bắt đầu với 30-50 câu hiện đại đơn giản.

Nhóm câu test đầu tiên:

```text
A là cha của B.
A là bố của B.
A là mẹ của B.
A là con của B.
A là vợ của B.
A là chồng của B.
A kết hôn với B.
A có con là B.
A sinh ra B.
A và B là anh em ruột.
```

---

## 9. Step 5: Viết rule regex đơn giản

Ví dụ file `extractor/relation_rules.py`:

```python
import re
from typing import List
from schemas.relation_schema import RelationExtracted

RULES = [
    {
        "name": "father_of_pattern",
        "pattern": r"(?P<source>[\w\sÀ-ỹ]+)\s+là\s+(cha|bố|ba)\s+của\s+(?P<target>[\w\sÀ-ỹ]+)",
        "relation": "father_of",
    },
    {
        "name": "mother_of_pattern",
        "pattern": r"(?P<source>[\w\sÀ-ỹ]+)\s+là\s+(mẹ|má)\s+của\s+(?P<target>[\w\sÀ-ỹ]+)",
        "relation": "mother_of",
    },
    {
        "name": "spouse_pattern",
        "pattern": r"(?P<source>[\w\sÀ-ỹ]+)\s+(kết hôn với|là vợ của|là chồng của)\s+(?P<target>[\w\sÀ-ỹ]+)",
        "relation": "spouse_of",
    }
]


def clean_person_name(name: str) -> str:
    return name.strip(" .,:;!?\"'")


def extract_relations(text: str) -> List[RelationExtracted]:
    results = []

    for rule in RULES:
        matches = re.finditer(rule["pattern"], text, flags=re.IGNORECASE)

        for match in matches:
            source = clean_person_name(match.group("source"))
            target = clean_person_name(match.group("target"))

            results.append(
                RelationExtracted(
                    source_person=source,
                    relation=rule["relation"],
                    target_person=target,
                    confidence=1.0,
                    evidence=match.group(0),
                    rule_name=rule["name"]
                )
            )

    return results
```

---

## 10. Step 6: MVP đầu tiên nên xử lý 5 dạng câu

MVP đầu tiên chỉ cần xử lý được các dạng sau:

```text
1. A là cha của B
2. A là mẹ của B
3. A là con của B
4. A là vợ/chồng của B
5. A có con là B
```

Ví dụ input:

```text
Ông Nguyễn Văn Nam là cha của Nguyễn Văn Bình.
Bà Trần Thị Hoa là mẹ của Nguyễn Văn Bình.
Nguyễn Văn Bình là con của Nguyễn Văn Nam.
Nguyễn Văn Nam có con là Nguyễn Văn Bình.
Nguyễn Văn Nam kết hôn với Trần Thị Hoa.
```

Expected output:

```json
[
  {
    "source_person": "Nguyễn Văn Nam",
    "relation": "father_of",
    "target_person": "Nguyễn Văn Bình"
  },
  {
    "source_person": "Trần Thị Hoa",
    "relation": "mother_of",
    "target_person": "Nguyễn Văn Bình"
  },
  {
    "source_person": "Nguyễn Văn Bình",
    "relation": "child_of",
    "target_person": "Nguyễn Văn Nam"
  },
  {
    "source_person": "Nguyễn Văn Nam",
    "relation": "parent_of",
    "target_person": "Nguyễn Văn Bình"
  },
  {
    "source_person": "Nguyễn Văn Nam",
    "relation": "spouse_of",
    "target_person": "Trần Thị Hoa"
  }
]
```

---

## 11. Step 7: Thêm NER sau khi rule cơ bản chạy được

Ban đầu có thể dùng regex đơn giản để bắt tên người. Sau đó mới thêm NER.

Một số thư viện có thể dùng cho tiếng Việt:

```text
underthesea
VnCoreNLP
pyvi
spaCy custom NER
```

Khuyến nghị:

- Phase đầu chưa cần NER phức tạp.
- Ưu tiên làm rule và evaluator trước.
- Khi rule bắt đầu sai do tên người phức tạp thì mới cải thiện entity extraction.

---

## 12. Step 8: Evaluation bằng precision / recall

Cần có script evaluate để đo chất lượng rule.

Công thức:

```text
Precision = Correct extracted relations / Total extracted relations
Recall = Correct extracted relations / Total expected relations
```

Ví dụ:

```text
Total expected relations: 100
Extracted relations: 90
Correct relations: 80

Precision = 80 / 90 = 88.9%
Recall = 80 / 100 = 80%
```

Với rule-based, nên ưu tiên:

```text
Precision cao trước
Recall tăng dần sau
```

Tức là rule extract ra ít cũng được, nhưng extract ra phải đúng.

---

## 13. Step 9: Build graph output

Sau khi đã extract relation, có thể chuyển sang graph.

Ví dụ relation JSON:

```json
{
  "source_person": "Nguyễn Văn Nam",
  "relation": "father_of",
  "target_person": "Nguyễn Văn Bình"
}
```

Graph edge:

```json
{
  "from": "Nguyễn Văn Nam",
  "to": "Nguyễn Văn Bình",
  "edge": "father_of"
}
```

Có thể dùng `networkx` để dựng graph trong Python.

Ví dụ:

```python
import networkx as nx

G = nx.DiGraph()

G.add_edge(
    "Nguyễn Văn Nam",
    "Nguyễn Văn Bình",
    relation="father_of"
)
```

---

---

## 14. Checklist bắt đầu implementation

```text
[ ] Chốt output schema
[ ] Chốt danh sách relation types
[ ] Tạo relation keyword mapping
[ ] Tạo 30-50 test cases đầu tiên
[ ] Viết normalizer
[ ] Viết sentence splitter
[ ] Viết 5 rule đầu tiên
[ ] Viết relation extractor
[ ] Viết evaluation script
[ ] Đo precision / recall
[ ] Thêm rule cho câu nhiều người con
[ ] Build graph output
[ ] Lưu failure cases để chuẩn bị fine-tune
```

---

## 15. Kết luận

Hướng triển khai phù hợp nhất là:

```text
1. Chốt schema output
2. Chốt danh sách relation
3. Tạo test cases
4. Viết rule regex đơn giản
5. Viết evaluator
6. Mở rộng rule dần
7. Build graph output
8. Dùng kết quả rule-based để tạo dataset fine-tune
```

MVP đầu tiên nên là:

```text
Input: một đoạn text tiếng Việt hiện đại
Output: danh sách quan hệ gia phả dạng JSON
```

Sau khi MVP rule-based ổn định, có thể chuyển sang Phase 2 là fine-tune model để xử lý các câu phức tạp hơn.
