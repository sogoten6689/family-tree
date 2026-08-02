# family-tree-data

Dữ liệu gia phả crawl từ [vietnamgiapha.com](https://vietnamgiapha.com) — phục vụ pipeline NER + Relation Extraction (dự án HCMUS Family Tree).

**Repo code:** [family-tree](https://github.com/sogoten6689/family-tree) (pipeline crawl, Gemini, Label Studio)

---

## Cấu trúc

```
gia_pha/
├── index.json                 # Danh mục toàn bộ cây đã export
└── {tree_id}/
    ├── metadata.json          # Metadata: URLs, stats, assessment, labeling
    ├── pha_ky.txt             # Phả ký — văn bản Quốc ngữ
    ├── pha_ky_fix.txt         # (optional) Phả ký đã chỉnh tay
    ├── pha_he.json            # Phả hệ — nodes + relationships
    ├── pha_he.txt             # Sơ đồ dạng text phẳng
    ├── assessment.json        # Đánh giá chất lượng Phả ký
    └── labels/                # Gemini pre-annotation (nếu có)
        ├── entities.json
        ├── ls_task.json
        └── cross_check.json

manifests/
├── labeled_trees.json         # 38 cây đã import Label Studio
├── labelable_trees.json       # Cây đạt assessment (suitable)
├── assessment_summary.json    # Tổng hợp điểm assessment
└── import_registry.json       # Registry cây đã import LS

gemini_labels/
├── import_registry.json       # SSOT — cây đã import Label Studio
└── {tree_id}/
    ├── pha_ky.entities.json   # Raw Gemini NER + relations
    ├── pha_ky.ls_task.json    # Label Studio task + predictions
    ├── cross_check.json       # So khớp tên vs sơ đồ pha_he
    └── import_status.json     # Trạng thái import (nếu có)

vgp_corpus/                    # Raw crawl VGP (SSOT trước export)
└── {tree_id}/
    ├── meta.json / metadata.json
    ├── pha_ky.txt
    ├── pha_he.json
    ├── pha_he.txt
    └── pha_ky.assessment.json

hannom/                        # Gia phả Hán-Nôm (Nom Foundation)
├── nomfoundation/
│   ├── catalog.json           # Danh mục volume
│   ├── summary.json
│   └── volumes/{volume_id}/
│       ├── metadata.json
│       ├── manifest.json
│       └── pages/*.jpg        # Ảnh scan trang gốc
└── family_trees/              # JSON trích xuất từ OCR Nom
    └── nom-{volume_id}.json
```

---

## Thống kê (2026-08-02)

| Chỉ số | Giá trị |
|--------|---------|
| Gia phả export (`gia_pha/`) | **342** cây |
| Raw crawl (`vgp_corpus/`) | **~1.263** thư mục |
| Gemini labels (`gemini_labels/`) | **69** cây |
| Hán-Nôm volumes (`hannom/nomfoundation/`) | **5** volume |
| Đã import Label Studio | **38** cây |
| Đạt assessment (labelable) | **23** cây |

---

## Nguồn & license

- Nguồn: vietnamgiapha.com — dùng cho nghiên cứu / luận văn
- Không phân phối thương mại nội dung gia phả gốc

---

## Cập nhật dữ liệu

Từ repo `family-tree`:

```bash
# Export toàn bộ corpus hợp lệ → gia_pha/
python -m label_studio_pipeline.export_giapha --all-valid

# Export manifest
cp data/vgp_corpus/labeled_trees.json data/manifests/
cp data/vgp_corpus/labelable_trees.json data/manifests/
cp data/vgp_corpus/assessment_summary.json data/manifests/
cp data/gemini_labels/import_registry.json data/manifests/

# gemini_labels/ — sync trực tiếp từ pipeline (đã nằm trong data/)

# Hán-Nôm — copy từ nlp_family_extractor/data/
rsync -a nlp_family_extractor/data/nomfoundation/ data/hannom/nomfoundation/
rsync -a nlp_family_extractor/data/family_trees/ data/hannom/family_trees/
```
