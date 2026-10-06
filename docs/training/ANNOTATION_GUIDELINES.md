# NER Annotation Guidelines for Genealogy Extraction

**Version:** 1.0  
**For models:** Phobert (Vietnamese) + SikuBERT (Hán-Nôm)  
**Format:** IOB2 with entity types  
**Confidence threshold:** Mark uncertain entities with `[?]` for review

---

## 1. Entity Types

### 1.1 PERSON - Tên người / 人名

**Definition:** Individual human names in genealogy text.

**Vietnamese examples:**
```
B-PERSON: Nguyễn Văn An
B-PERSON: Trần Thị Hạnh
B-PERSON: Lê Thị Hoa
```

**Hán-Nôm examples:**
```
B-PERSON: 阮文成 (traditional)
B-PERSON: 阮文成 (Hán-Nôm with special chars)
B-PERSON: 貴妃 (royal title + name, count as PERSON)
```

**Rules:**
- Include given name + surname together as one entity
- Include all name parts (even if 2-3 components)
- Do NOT include titles (官, 夫人) as part of person name
- Exception: 女 (female), 男 (male) as gender markers — skip them

**Edge cases:**
- Nicknames/aliases: mark as separate entity if listed separately
  ```
  Nguyễn Văn An, tên lóng Gò Vạc
  → B-PERSON: Nguyễn Văn An
  → B-PERSON: Gò Vạc
  ```
- Multiple names (phục hưng): treat as ONE entity if connected by "hay" (or)
  ```
  Nguyễn Văn An hay Nguyễn Gò Vạc
  → B-PERSON: Nguyễn Văn An
  (single annotation, do NOT split)
  ```

---

### 1.2 YEAR - Năm sinh/mất / 年

**Definition:** Birth or death year in genealogy.

**Vietnamese examples:**
```
B-YEAR: 1945 (in "sinh năm 1945")
B-YEAR: 2001 (in "mất năm 2001")
```

**Hán-Nôm examples:**
```
B-YEAR: 康熙五十年 (Kangxi 50th year = 1711)
B-YEAR: 1850 (direct numeral)
```

**Rules:**
- Only mark the **year number itself**, NOT "sinh", "mất", "năm", "年", "生", "卒"
- Include full year phrase if it's non-standard (e.g., "康熙五十年")
- Do NOT include age (e.g., "61 tuổi" → skip "61")

**Edge cases:**
- Lunar calendar dates: mark the year component
  ```
  陰曆五月初一 → no year marker (skip)
  康熙五十年五月 → B-YEAR: 康熙五十年
  ```
- Approximate years (e.g., "around 1900"): still mark
  ```
  khoảng năm 1900 → B-YEAR: 1900
  ```

---

### 1.3 RELATION_SPOUSE - Vợ/chồng quan hệ / 配偶

**Definition:** Marriage/spousal relationship between two people.

**Vietnamese keywords:**
- "kết hôn" (married)
- "cưới" (married, less formal)
- "lấy" (married, colloquial)
- "vợ của" (wife of)
- "chồng của" (husband of)

**Hán-Nôm keywords:**
- "配偶" (spouse)
- "妻" (wife)
- "妻曰" (his wife is named...)
- "娶" (took as wife)
- "嫁" (married to)

**Annotation example:**
```
Vietnamese:
"Nguyễn Văn An sinh năm 1945, kết hôn với bà Trần Thị Hạnh sinh năm 1948"
→ RELATION_SPOUSE: (Nguyễn Văn An, Trần Thị Hạnh)

Hán-Nôm:
"阮文成娶陈氏"
→ RELATION_SPOUSE: (阮文成, 陈氏)
```

**Rules:**
- Mark relationship between person1 and person2
- Store as tuple: `(head_person, relation_type, tail_person)`
- Order: person who takes action first (e.g., "娶" = groom comes first)

**Edge cases:**
- Remarriage: annotate as separate RELATION_SPOUSE each time
  ```
  Nguyễn Văn An cưới Trần Thị Hạnh, sau lấy Lê Thị Hoa
  → RELATION_SPOUSE: (Nguyễn Văn An, Trần Thị Hạnh)
  → RELATION_SPOUSE: (Nguyễn Văn An, Lê Thị Hoa)
  ```
- Vague reference: skip if names not explicit
  ```
  "người anh ấy kết hôn" (no spouse name) → skip
  ```

---

### 1.4 RELATION_PARENT - Cha/mẹ quan hệ / 亲子

**Definition:** Parent-child biological relationship.

**Vietnamese keywords:**
- "có con" (has child)
- "là con của" (is child of)
- "sinh" (gave birth to, when subject is parent)
- "cha/mẹ của" (father/mother of)
- "con trai/gái" (son/daughter)

**Hán-Nôm keywords:**
- "有子" (has son)
- "之子" (is son/child of)
- "生" (gave birth to, parent as subject)
- "父" (father of)
- "母" (mother of)

**Annotation example:**
```
Vietnamese:
"Nguyễn Văn An và Trần Thị Hạnh có con là Nguyễn Văn Bình sinh năm 1972"
→ RELATION_PARENT: (Nguyễn Văn An, Nguyễn Văn Bình)
→ RELATION_PARENT: (Trần Thị Hạnh, Nguyễn Văn Bình)

Hán-Nôm:
"阮文成生子德重"
→ RELATION_PARENT: (阮文成, 德重)
```

**Rules:**
- If both parents mentioned, create TWO separate relations (one per parent)
- Order: parent → child (always parent comes first)
- Include **adoptive children** with [ADOPTED] marker if stated
  ```
  "Nguyễn Văn An nuôi (adopted) Nguyễn Văn Cường"
  → RELATION_PARENT_ADOPTED: (Nguyễn Văn An, Nguyễn Văn Cường)
  ```

**Edge cases:**
- Illegitimate children: still mark as RELATION_PARENT (no distinction)
- Step-children: mark as RELATION_PARENT_STEP if explicit
  ```
  "con riêng của" (child from previous relationship)
  → RELATION_PARENT_STEP: (...)
  ```
- Multiple siblings from same parents: create N relations (one per child)

---

### 1.5 RELATION_SIBLING - Anh/chị/em quan hệ / 兄弟姐妹

**Definition:** Sibling relationship (brothers, sisters).

**Vietnamese keywords:**
- "là anh em" (are siblings)
- "anh trai/em trai" (brother)
- "chị gái/em gái" (sister)
- "là con của <same parent>" (children of same parent)
- "và ... là anh em trong gia đình"

**Hán-Nôm keywords:**
- "兄" (older brother)
- "弟" (younger brother)
- "姐" (older sister)
- "妹" (younger sister)
- "同胞" (full siblings)

**Annotation example:**
```
Vietnamese:
"Nguyễn Văn Bình và Nguyễn Thị Lan là anh em trong gia đình"
→ RELATION_SIBLING: (Nguyễn Văn Bình, Nguyễn Thị Lan)

Hán-Nôm:
"阮文成与阮文智为兄弟"
→ RELATION_SIBLING: (阮文成, 阮文智)
```

**Rules:**
- Order: arbitrary (sibling is bidirectional), but mark older first if stated
- Do NOT create duplicate: if A-B marked, skip B-A
- If 3+ siblings: create edges for all pairs? **YES**, but see below

**Edge cases:**
- Half-siblings: mark as RELATION_SIBLING_HALF
  ```
  "anh em khác mẹ" (same father, different mothers)
  → RELATION_SIBLING_HALF: (...)
  ```
- Adopted siblings: mark as RELATION_SIBLING_ADOPTED
- Multiple siblings: **only mark explicitly stated pairs**
  ```
  "Nguyễn Văn Bình, Nguyễn Thị Lan và Nguyễn Văn Cường là anh em"
  → If text groups all 3 together:
     RELATION_SIBLING: (Nguyễn Văn Bình, Nguyễn Thị Lan)
     RELATION_SIBLING: (Nguyễn Thị Lan, Nguyễn Văn Cường)
     [Do NOT add Bình-Cường unless explicitly stated]
  ```

---

## 2. Format: IOB2 Tagging

**IOB2 scheme:**
- `B-ENTITY_TYPE`: Beginning of entity
- `I-ENTITY_TYPE`: Inside (continuation) of entity
- `O`: Outside any entity

**Example tokenization (Vietnamese):**

```
Input: "Nguyễn Văn An sinh năm 1945, kết hôn với Trần Thị Hạnh."

Tokenized:
Nguyễn    B-PERSON
Văn       I-PERSON
An        I-PERSON
sinh      O
năm       O
1945      B-YEAR
,         O
kết       O
hôn       O
với       O
Trần      B-PERSON
Thị       I-PERSON
Hạnh      I-PERSON
.         O

Relations:
RELATION_SPOUSE: (Nguyễn Văn An, Trần Thị Hạnh)
```

**Example for Hán-Nôm:**

```
Input: "阮文成娶陈氏，生子德重。"

阮        B-PERSON
文        I-PERSON
成        I-PERSON
娶        O
陈        B-PERSON
氏        I-PERSON
，        O
生        O
子        O
德        B-PERSON
重        I-PERSON
。        O

Relations:
RELATION_SPOUSE: (阮文成, 陈氏)
RELATION_PARENT: (阮文成, 德重)
```

---

## 3. Special Cases & Conventions

### 3.1 Characters not in standard encodings (Nôm glyphs)

- **Do NOT normalize** Nôm glyphs to modern Vietnamese
- Keep original character as-is in text
- Example:
  ```
  ❌ "Nguyễn" (convert from Nôm glyph)
  ✅ "阮" (keep original)
  ```

### 3.2 Traditional vs. Simplified Chinese

- **Do NOT convert** between traditional and simplified
- Annotate in original script
- Mark as [TRADITIONAL] or [SIMPLIFIED] if mixed document:
  ```
  "阮文成娶陈氏" [TRADITIONAL]
  "阮文成娶陈氏" [SIMPLIFIED] — same meaning, different glyphs
  ```

### 3.3 Ambiguous or Uncertain Entities

- Mark with `[?]` suffix for manual review
- Example:
  ```
  "Ông Nguyễn" (unclear if full name)
  → Nguyễn [?] B-PERSON or skip?
  
  Decision: Mark as B-PERSON, flag [?] for review
  ```

### 3.4 Titles, Honorifics, & Roles

- **Do NOT include** as part of PERSON entity:
  ```
  ❌ "Đại Thần Nguyễn Văn An" → B-PERSON: Đại Thần Nguyễn Văn An
  ✅ "Đại Thần Nguyễn Văn An" → B-PERSON: Nguyễn Văn An
  ```
- Separate annotation for titles (optional, for future):
  ```
  Đại Thần = TITLE: Đại Thần (out of scope for Phase 1)
  ```

### 3.5 Broken Genealogy Chains

- If parent-child relation broken (missing name), do NOT infer
  ```
  "Nguyễn Văn An's children: 1. Nguyễn Văn Bình, 2. ???, 3. Nguyễn Thị Lan"
  → Only mark relations for Bình and Lan, skip ??? (no name)
  ```

---

## 4. Quality Assurance

### 4.1 Inter-Annotator Agreement (IAA)

- **Target IAA (Cohen's kappa):** ≥ 0.85
- **Procedure:**
  1. Annotator A tags 100 texts
  2. Annotator B tags same 100 texts independently
  3. Calculate kappa on overlapping texts
  4. Discuss disagreements, refine guidelines
  5. Re-tag conflicting texts
  6. Recalculate IAA until ≥0.85

### 4.2 Spot-check Protocol

- Randomly select 10% of annotated texts
- Senior reviewer (expert in genealogy) verifies
- If >5% errors found in sample → re-annotate that batch

### 4.3 Common Mistakes to Avoid

| Mistake | Example | Correction |
|---|---|---|
| Including title in name | "官 Nguyễn Văn An" → PERSON: "官 Nguyễn Văn An" | Remove title: "Nguyễn Văn An" |
| Splitting multi-word name | "Nguyễn Văn" (B) + "An" (separate) | Keep together: "Nguyễn Văn An" (B-I-I) |
| Missing relations | Names mentioned but no explicit relation marked | Create relation even if implicit (e.g., "father of" if not stated but context clear) |
| Duplicate relations | Marking A→B and B→A for siblings | Mark only once (A→B or B→A, not both) |
| Uncertain entities | Marking "[?]" names but not flagging | Flag with [?] AND add to review list |

---

## 5. Tools & Workflow

### 5.1 Annotation Tool Options

**Option A: Prodigy (Paid, Recommended)**
- Web UI for fast annotation
- Keyboard shortcuts for entity tagging
- Built-in IAA tracking
- Setup: `prodigy ner.manual genealogy-vietnamese en_core_web_sm --patterns patterns.jsonl`

**Option B: Doccano (Free, Open Source)**
- Web UI similar to Prodigy
- Community support
- Setup: docker run -d -p 8000:8000 doccano/doccano

**Option C: Manual CSV/Excel (Simplest)**
- Spreadsheet with columns: `[text] [entity_start] [entity_end] [entity_type]`
- Low overhead, but slower annotation
- Good for small datasets (<100 texts)

### 5.2 Export Format

**Target format:** **CONLL 2003** (standard for NER)

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
Trần B-PERSON
Thị I-PERSON
Hạnh I-PERSON
. O

(blank line = new sentence)
```

---

## 6. Annotation Checklist

**Before starting:**
- [ ] Read this guideline fully
- [ ] Review 5 example genealogy texts
- [ ] Tag 1 example together with senior reviewer for calibration
- [ ] Ask questions on unclear cases

**During annotation:**
- [ ] Check tokenization (avoid splitting names)
- [ ] Verify relations are captured (not just entities)
- [ ] Flag uncertain entities with [?]
- [ ] Save progress after every 50 texts

**After completing batch:**
- [ ] Run IAA check (if >1 annotator)
- [ ] Export to CONLL format
- [ ] Run spot-check (10% random sample)
- [ ] Resolve [?] flagged entities with reviewer

---

## 7. Examples to Practice

**Vietnamese genealogy example 1:**

```
Text:
"Ông Nguyễn Văn An sinh năm 1945, kết hôn với bà Trần Thị Hạnh sinh năm 1948.
Họ có hai con: Nguyễn Văn Bình sinh năm 1972 và Nguyễn Thị Lan sinh năm 1975.
Nguyễn Văn Bình cưới Lê Thị Hoa năm 1998, có con trai là Nguyễn Minh Đức sinh năm 2000."

Expected tags:
Nguyễn      B-PERSON
Văn         I-PERSON
An          I-PERSON
sinh        O
năm         O
1945        B-YEAR
kết         O
hôn         O
với         O
bà          O
Trần        B-PERSON
Thị         I-PERSON
Hạnh        I-PERSON
sinh        O
năm         O
1948        B-YEAR
...

Expected relations:
RELATION_SPOUSE: (Nguyễn Văn An, Trần Thị Hạnh)
RELATION_PARENT: (Nguyễn Văn An, Nguyễn Văn Bình)
RELATION_PARENT: (Trần Thị Hạnh, Nguyễn Văn Bình)
RELATION_PARENT: (Nguyễn Văn An, Nguyễn Thị Lan)
RELATION_PARENT: (Trần Thị Hạnh, Nguyễn Thị Lan)
RELATION_SIBLING: (Nguyễn Văn Bình, Nguyễn Thị Lan)
RELATION_SPOUSE: (Nguyễn Văn Bình, Lê Thị Hoa)
RELATION_PARENT: (Nguyễn Văn Bình, Nguyễn Minh Đức)
RELATION_PARENT: (Lê Thị Hoa, Nguyễn Minh Đức)
```

---

**Hán-Nôm genealogy example (simplified for clarity):**

```
Text:
"阮文成生於康熙五十年，娶陈氏，生子德重。"

Expected tags:
阮         B-PERSON
文         I-PERSON
成         I-PERSON
生         O
於         O
康         B-YEAR
熙         I-YEAR
五         I-YEAR
十         I-YEAR
年         I-YEAR
娶         O
陈         B-PERSON
氏         I-PERSON
生         O
子         O
德         B-PERSON
重         I-PERSON

Expected relations:
RELATION_SPOUSE: (阮文成, 陈氏)
RELATION_PARENT: (阮文成, 德重)
```

---

## Document version history

| Version | Date | Author | Change |
|---|---|---|---|
| 0.1 | 2026-10-06 | Claude | Initial draft |
| 1.0 | 2026-10-06 | — | Approved for Phase 1 |

---

**For questions:** Refer to section 4.3 (Common Mistakes) or flag with [?] during annotation.
