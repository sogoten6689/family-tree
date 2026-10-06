# Dual-Model Genealogy Extraction Plan (SikuBERT + Phobert)

## 1. Overview

Replace regex MVP (60% accuracy) with two specialized NER models:
- **SikuBERT** (fine-tuned): Classical Chinese/Hán-Nôm genealogy extraction
- **Phobert** (fine-tuned): Vietnamese genealogy extraction

Run in **parallel** - detect language, route to appropriate model.

**Target accuracy:** 90%+ on both languages  
**Timeline:** Phase 2 (after regex MVP stable in production)

---

## 2. Architecture

```
User Input (text)
    ↓
Language Detection (Chinese or Vietnamese)
    ↓
┌─────────────────────────────────────┐
│  If Vietnamese:                     │
│  → Phobert (fine-tuned) NER        │
│  → Extract persons, relations       │
│  → Vietnamese genealogy parser      │
└─────────────────────────────────────┘
                ↓
        Unified JSON output
        (persons, relations, years)
                ↓
            Tree Builder
                ↓
          Frontend render
        
┌─────────────────────────────────────┐
│  If Hán/Chinese:                    │
│  → SikuBERT (fine-tuned) NER        │
│  → Extract persons, relations       │
│  → Chinese genealogy parser         │
└─────────────────────────────────────┘
```

---

## 3. Phase Breakdown

### Phase 3.1: Data Preparation (2-3 weeks)

**Task 3.1.1: Vietnamese genealogy dataset**
- Source: `data/vietnamgiapha/` existing corpus
- Action: Extract ~500-1000 texts, manually annotate entities
  - `PERSON` (tên người)
  - `RELATION_SPOUSE` (vợ/chồng)
  - `RELATION_PARENT` (cha/mẹ)
  - `RELATION_SIBLING` (anh/chị/em)
  - `YEAR` (năm sinh/mất)
- Format: **IOB2 or Prodigy** for NER annotation
- Tool: Prodigy (if budget allows) or manual CSV tagging
- **Effort:** 1-2 person-weeks
- **Deliverable:** `data/training/vietnamese_genealogy_ner.conll2003`

**Task 3.1.2: Chinese (Hán-Nôm) genealogy dataset**
- Source: Existing Hán-Nôm research corpus or collect from:
  - `research/model_survey/` references
  - Public 族谱 (Chinese genealogy) datasets
- Action: Extract/translate ~500-1000 texts, annotate same entities
  - Handle traditional/simplified variants
  - Keep Hán-Nôm glyphs as-is (don't normalize)
- Format: **IOB2 or Prodigy**
- **Effort:** 2-3 person-weeks (sourcing harder than Vietnamese)
- **Deliverable:** `data/training/hannom_genealogy_ner.conll2003`

### Phase 3.2: Fine-tuning Setup (1 week)

**Task 3.2.1: Phobert fine-tune infrastructure**
- Model: Phobert-base or Phobert-large (HuggingFace)
- Framework: Hugging Face `transformers` + `datasets` library
- Hardware: Colab GPU T4 or RunPod RTX 4090
- Script location: `nlp_family_extractor/tools/finetune_phobert.py`
- Training config:
  - Epochs: 3-5
  - Batch size: 16-32
  - Learning rate: 2e-5
  - Warmup: 500 steps
- **Deliverable:** 
  - Trained model → `models/phobert_genealogy_ner/`
  - Training logs → `docs/training_logs/phobert_*.json`

**Task 3.2.2: SikuBERT fine-tune infrastructure**
- Model: SikuBERT (HuggingFace: SIKU-BERT/sikubert)
- Framework: Same as Phobert
- Hardware: Same (Colab/RunPod)
- Script location: `nlp_family_extractor/tools/finetune_sikubert.py`
- Training config: Same as Phobert
- **Deliverable:**
  - Trained model → `models/sikubert_genealogy_ner/`
  - Training logs → `docs/training_logs/sikubert_*.json`

### Phase 3.3: Backend Integration (1-2 weeks)

**Task 3.3.1: Language detection module**
- Input: text (genealogy string)
- Output: 'vietnamese' | 'chinese' | 'mixed'
- Implementation: Simple heuristic (regex) or langdetect library
- Location: `nlp_family_extractor/app/genealogy/language_detector.py`
- **Deliverable:** `language_detector.py`

**Task 3.3.2: Dual NER inference**
- Refactor `genealogy_parser.py`:
  - Keep regex as fallback (L0 error handling)
  - Add `NER_INFER_VIETNAMESE` (Phobert) path
  - Add `NER_INFER_CHINESE` (SikuBERT) path
- Location: `nlp_family_extractor/app/genealogy/genealogy_parser_v2_ml.py`
- Inference pipeline:
  ```python
  1. Load language
  2. Load appropriate model (phobert_genealogy_ner or sikubert_genealogy_ner)
  3. Tokenize + run NER
  4. Parse NER output → extract names, relations, years
  5. Return unified JSON
  ```
- **Deliverable:** `genealogy_parser_v2_ml.py`

**Task 3.3.3: API endpoint update**
- Endpoint: `POST /api/genealogy/extract` (existing)
- Add runtime parameter: `--model-version` (default: 'regex', optional: 'ml')
- Response identical to regex MVP (backward compatible)
- Location: `nlp_family_extractor/api.py`
- **Deliverable:** Updated `/api/genealogy/extract` with `model_version` param

**Task 3.3.4: Model loading & caching**
- Download models on startup
- Cache in memory (if fit) or disk
- Lazy-load if memory tight
- Location: `nlp_family_extractor/app/genealogy/model_manager.py`
- **Deliverable:** `model_manager.py`

### Phase 3.4: Frontend Updates (3-4 days)

**Task 3.4.1: UI for model selection**
- Add dropdown in `GenealogyExtractorPage.tsx`:
  - "Regex MVP (60%, fast)"
  - "ML (SikuBERT + Phobert, 90%+, slower)"
- Default: Regex MVP
- Send `model_version` in API request
- **Deliverable:** Updated `GenealogyExtractorPage.tsx`

**Task 3.4.2: Performance indicators**
- Show model name + expected accuracy in UI
- Show inference time after extraction
- **Deliverable:** Updated results panel

### Phase 3.5: Testing & Validation (1-2 weeks)

**Task 3.5.1: Vietnamese test suite**
- Baseline: existing 3 examples + 7 diverse tests from summary
- Add 20-30 new Vietnamese genealogy texts
- Measure:
  - Person extraction accuracy (P/R/F1)
  - Relation type accuracy (spouse/parent/sibling)
  - Year extraction accuracy
- Target: ≥90% F1
- Location: `tests/test_genealogy_ml_vietnamese.py`

**Task 3.5.2: Chinese/Hán-Nôm test suite**
- Source test data: 20-30 Hán-Nôm genealogy samples
- Same metrics as Vietnamese
- Target: ≥90% F1
- Location: `tests/test_genealogy_ml_chinese.py`

**Task 3.5.3: Cross-lingual edge cases**
- Mixed text (Vietnamese + Hán-Nôm in same input)
- Language switching across sentences
- Character encoding edge cases (UTF-8, traditional/simplified)
- Location: `tests/test_genealogy_ml_mixed.py`

**Task 3.5.4: Performance benchmarks**
- Inference time (Phobert vs SikuBERT)
- Memory usage with models loaded
- GPU vs CPU performance
- Location: `docs/performance_benchmark.md`

### Phase 3.6: Deployment & Rollout (1 week)

**Task 3.6.1: CI/CD setup**
- Add model download to `requirements.txt` or `setup.py`
- Test on GitHub Actions (CPU only, or skip GPU-heavy tests)
- Location: `.github/workflows/test.yml`

**Task 3.6.2: Docker optimization**
- Add model caching layer in Docker image
- Update `infra/Dockerfile` if exists
- **Deliverable:** Updated Docker image with both models

**Task 3.6.3: Documentation**
- README section: which model to use when
- API docs: `model_version` parameter
- Location: `nlp_family_extractor/README.md`

**Task 3.6.4: Gradual rollout**
- Week 1: ML models available, opt-in via UI (default regex)
- Week 2-3: Monitor production metrics
- Week 4: Consider making ML default if ≥95% accuracy observed

---

## 4. Resource Requirements

### Training Infrastructure
- **Colab GPU:** Free, ~2 hours per model × 2 = 4 hours total
  - Or RunPod RTX 4090: ~$0.44/hr × 4 = ~$1.76 (cheap)
- **Storage:** ~1GB per model (SikuBERT + Phobert final weights)

### Annotation Effort
- Vietnamese: 1-2 person-weeks (500-1000 texts)
- Chinese: 2-3 person-weeks (sourcing + annotation)
- **Total:** 3-5 person-weeks of labeling

### Development Effort
- Backend integration: 1-2 weeks
- Frontend: 3-4 days
- Testing: 1-2 weeks
- **Total:** 3-4 weeks engineering

### Timeline
- **Start:** After regex MVP stable (current date + 2 weeks)
- **Data prep:** Weeks 1-3
- **Model training:** Weeks 2-3 (parallel)
- **Integration:** Weeks 3-4
- **Testing:** Weeks 4-5
- **Deployment:** Week 6
- **Total: ~6-8 weeks end-to-end**

---

## 5. Risks & Mitigation

| Risk | Impact | Mitigation |
|---|---|---|
| Annotation quality low → model weak | High | Use inter-annotator agreement (IAA) ≥0.85, seed with expert samples |
| Hán-Nôm training data hard to source | High | Start with synthetic data + public 族谱 datasets, plan for domain adaptation |
| Model overfits to training domain | Medium | Add regularization (dropout 0.2), test on held-out genealogy texts |
| Inference too slow for API | Medium | Batch inference, model quantization (int8), GPU acceleration |
| Models bloat deployment size | Low | Compress models (onnx, quantization), lazy-load on first use |

---

## 6. Success Criteria

✅ **Phase completion:**
- Vietnamese: ≥90% F1 on test set
- Chinese: ≥90% F1 on test set
- Inference time: <500ms per text (API acceptable)
- Accuracy improvement: regex 60% → ML 90%+

✅ **Production readiness:**
- All tests passing (unit + integration)
- Documentation complete
- Backward compatible API (regex still available)
- No breaking changes to frontend

---

## 7. Open Questions

1. **Training data sourcing:**
   - Do we have ground-truth Hán-Nôm genealogy corpus already?
   - Permission to use vietnamgiapha dataset for ML?
   - Any existing annotation guidelines?

2. **Deployment:**
   - Will models be deployed to production immediately, or A/B test first?
   - Storage constraints on server (do we have 2GB free)?

3. **Maintenance:**
   - Who maintains/updates models after Phase 3.6?
   - How often to re-train on new genealogy data?

---

## Appendix: Model Comparison

| Model | Language | Accuracy (est.) | Speed | License | Maintenance |
|---|---|---|---|---|---|
| **Regex MVP (current)** | Vietnamese only | 60% | <1ms | N/A | Low |
| **Phobert fine-tuned** | Vietnamese | 90%+ | ~200ms | MIT (model) | Medium |
| **SikuBERT fine-tuned** | Hán-Nôm | 90%+ | ~300ms | Apache-2.0 | Medium |
| **Dual system** | Both | 90%+ | ~250ms avg | MIT + Apache-2.0 | Medium-High |

---

**Document version:** 0.1 (proposal)  
**Last updated:** 2026-10-06  
**Status:** Ready for L1+ review and resource planning
