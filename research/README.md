# Research — code thí nghiệm (không phải app production)

| Package | Việc |
|---------|------|
| `label_studio_pipeline/` | Gán nhãn NER/RE, gold |
| `source_discovery/` | Firecrawl tìm nguồn |

Chạy **từ root repo** (path `data/…` tính từ gốc):

```bash
PYTHONPATH=research python -m label_studio_pipeline.audit_ls_tasks
PYTHONPATH=research python -m label_studio_pipeline.build_corpus_inventory
PYTHONPATH=research python -m source_discovery map
```

Trong Cursor, terminal workspace đã gắn `PYTHONPATH=research`.
