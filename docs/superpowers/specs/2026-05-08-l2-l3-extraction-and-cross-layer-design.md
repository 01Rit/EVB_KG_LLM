# L2-L3 Extraction and Cross-Layer Connection Design

**Date**: 2026-05-08
**Status**: Approved
**Type**: Bug Fix / Enhancement

## Problem Statement

Two issues were identified:

1. **L3 extraction too few**: After importing L2 documents, too few L3 terms are extracted due to text length limitations
2. **Cross-layer connections not created**: L2 document import does not trigger the full CrossLayerLinker pipeline for creating inter-layer connections

## Solution Overview

Apply **Approach A: Lightweight Fix** - minimal changes to fix both issues:
- Improve L3 extraction via multi-chunk processing
- Integrate CrossLayerLinker into L2 import flow
- Keep manual trigger API for flexibility

## Section 1: L3 Extraction Improvement

### Goal
Extract more L3 terms from L2 documents by processing multiple text chunks

### Changes

**File**: `src/importer/entity_extractor.py`

| Parameter | Before | After |
|-----------|--------|-------|
| Text chunk size | 2000 chars, single | 2000 chars with 200 char overlap, multiple |
| Max entities | 30 | 50 |
| Max terms | 30 | 50 |

### Data Flow

```
Document text
    ↓
split_into_chunks(text, chunk_size=2000, overlap=200)
    ↓
For each chunk:
  extract_entities_with_types(chunk) → entities[], terms[]
    ↓
merge_and_deduplicate(all_entities, all_terms)
    ↓
Return {entities: [...], terms: [...]}
```

### Implementation

Add new method `extract_entities_chunked()` in `EntityExtractor`:

```python
def extract_entities_chunked(self, text: str, filename: str = '',
                             max_items: int = 50,
                             chunk_size: int = 2000,
                             overlap: int = 200) -> Dict:
    chunks = self._split_text(text, chunk_size, overlap)
    all_entities = []
    all_terms = []

    for i, chunk in enumerate(chunks):
        try:
            result = self.extract_entities_with_types(chunk, filename, max_items)
            all_entities.extend(result.get('entities', []))
            all_terms.extend(result.get('terms', []))
        except Exception as e:
            logger.warning(f"Chunk {i} extraction failed: {e}")
            continue

    entities = self._deduplicate_by_name(all_entities)
    terms = self._deduplicate_by_name(all_terms)

    return {
        'entities': entities[:max_items],
        'terms': terms[:max_items]
    }
```

### Error Handling
- Single chunk failure does not block other chunks
- Log chunk index and error for debugging
- Return partial results if some chunks fail

---

## Section 2: Cross-Layer Connection Integration

### Goal
Automatically trigger CrossLayerLinker pipeline when L2 documents are imported

### Changes

**File**: `src/importer/l2_importer.py`

Modify `import_pdf()` and `import_markdown()` to use chunked extraction and call `_create_definition_of_via_linker()`:

```python
def import_pdf(self, full_text: str, filename: str) -> Dict[str, Any]:
    ...
    extraction = self.extractor.extract_entities_chunked(full_text, filename=filename)
    ...
```

### Cross-Layer Relation Types

| Relation | Source Layer | Target Layer | High Threshold | Low Threshold |
|----------|--------------|--------------|----------------|---------------|
| DEFINITION_OF | L2 (Entity) | L3 (Term) | 0.90 | 0.75 |
| REFERENCE_OF | L1 (Component) | L2 (Entity) | 0.92 | 0.80 |

### 4-Step Pipeline

1. **Embed Recall**: Search Milvus for candidate matches
2. **Hard Rule Filter**: Validate layer direction and entity type
3. **LLM Judge**: For medium-confidence candidates, ask LLM
4. **Write Policy**: Filter by threshold, apply top-K

---

## Section 3: API and Error Handling

### API Endpoints

| Endpoint | Method | Purpose |
|----------|--------|---------|
| `/api/v1/import/l2` | POST | Import L2 document (auto-triggers cross-layer) |
| `/api/v1/import/l2/markdown` | POST | Import L2 markdown (auto-triggers cross-layer) |
| `/api/v1/cross-layer/trigger` | POST | Manual trigger for specific document |
| `/api/v1/cross-layer/build-all` | POST | Batch rebuild all cross-layer connections |

### Error Handling Strategy

| Error Type | Handling |
|------------|----------|
| CrossLayerLinker failure | Log error, continue import, return warning |
| LLM Judge timeout | Auto-pass high-confidence (≥0.92), retry medium once |
| Neo4j write failure | Retry 3 times, then log and skip |
| Milvus unavailable | Fall back to name matching only |

### Logging

Log all cross-layer operations:

```
[CrossLayer] Entity {id} -> Term {id}: DEFINITION_OF (confidence=0.95)
[CrossLayer] Entity {id} -> Term {id}: DEFINITION_OF FAILED: {error}
[CrossLayer] Batch complete: {success_count} created, {failure_count} failed
```

---

## Files to Modify

1. `src/importer/entity_extractor.py` - Add chunked extraction
2. `src/importer/l2_importer.py` - Integrate CrossLayerLinker, use chunked extraction
3. `src/cross_layer/linker.py` - Add batch processing method (optional)

## Testing Plan

1. Import a 20-page PDF, verify L3 term count > 50
2. Import L2 doc, verify DEFINITION_OF edges exist in Neo4j
3. Manual trigger API returns correct connection count
4. Error handling: simulate Milvus failure, verify graceful degradation

## Success Criteria

1. L2 document import produces ≥50 L3 terms (quality-deduplicated)
2. L2→L3 DEFINITION_OF connections are created automatically
3. Manual trigger API works correctly
4. No blocking errors during import when cross-layer fails
