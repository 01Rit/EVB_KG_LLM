# L2 Import Refactoring Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Refactor L2 import to create proper three-layer architecture (L2_Document, L2_Entity, L3_Term) with cross-layer relationships, without creating L1 nodes.

**Architecture:** The existing `/import/l2` endpoint is refactored to extract entity types and create properly labeled nodes. A new entity extraction prompt produces entity_type and source_evidence fields. Cross-layer relationships are built during import.

**Tech Stack:** FastAPI, Neo4j, LLMClient, EntityExtractor

---

## File Structure

```
src/
├── api/
│   ├── import_routes.py         # Modify: refactor /import/l2 endpoint
│   └── schemas.py                # Create: L2/L3 Pydantic schemas
├── importer/
│   ├── entity_extractor.py      # Modify: add entity_type-aware extraction
│   └── l2_importer.py           # Create: L2 import orchestration logic
└── kg/
    └── client.py                # Modify: add cross-layer query helpers

tests/
├── api/
│   └── test_import_routes.py    # Modify: add L2 import tests
└── importer/
    └── test_l2_importer.py      # Create: unit tests for L2 importer
```

---

## Task 1: Add L2/L3 Pydantic Schemas

**Files:**
- Modify: `src/api/schemas.py`

- [ ] **Step 1: Create L2/L3 schemas in schemas.py**

```python
from pydantic import BaseModel
from typing import List, Optional, Dict, Any


class L2EntityData(BaseModel):
    name: str
    entity_type: str  # component|tool|action|parameter|safety|material|definition
    source_evidence: Optional[str] = None
    properties: Dict[str, Any] = {}


class L2DocumentData(BaseModel):
    title: str
    filename: str
    chapter: Optional[str] = None
    full_text: str
    entities: List[L2EntityData] = []
    terms: List[Dict[str, str]] = []  # term_id, definition


class L3TermData(BaseModel):
    term_id: str
    name: str
    definition: str
    source_document_id: Optional[str] = None


class L2ImportResponse(BaseModel):
    code: int
    message: str
    doc_id: str
    entities_created: int
    terms_created: int
    relations_created: int
    errors: List[str] = []
```

- [ ] **Step 2: Run schema validation test**

Run: `cd D:\KG_project\Final4.14 && python -c "from src.api.schemas import L2EntityData, L2DocumentData, L3TermData; print('OK')"`
Expected: OK

- [ ] **Step 3: Commit**

```bash
git add src/api/schemas.py
git commit -m "feat(api): add L2/L3 Pydantic schemas"
```

---

## Task 2: Refactor EntityExtractor to Support Entity Types

**Files:**
- Modify: `src/importer/entity_extractor.py:38-94`

- [ ] **Step 1: Add new method for type-aware entity extraction**

Add after `extract_triplets` (around line 95):

```python
def extract_entities_with_types(self, text: str, filename: str = '', max_items: int = 100) -> Dict[str, Any]:
    """
    Extract entities with type classification and source evidence.
    Returns: {entities: [...], terms: [...]}
    """
    text = text[:4000]

    battery_model = self._detect_battery_model(text, filename)
    logger.info(f"Detected battery model: {battery_model}")

    prompt = f'''从以下电池拆卸手册中提取实体知识，构建三层知识图谱。

文档内容：
{text}

提取要求：
1. 识别所有可拆卸部件（component）：电池包、模组、电芯、冷却板等
2. 识别工具（tool）：扭矩扳手、绝缘工具、拆卸夹具等
3. 识别动作（action）：拆卸、拧松、拔出、分离、检测等
4. 识别技术参数（parameter）：扭矩值25Nm、电压阈值、绝缘电阻等
5. 识别安全规范（safety）：高压安全距离、IP67防护等级、防触电措施等
6. 识别材料/属性（material）：阻燃材料、铝合金外壳、冷却液类型等
7. 识别定义（definition）：预紧力、力矩标准、拆卸顺序规则等

返回JSON：
{{
  "entities": [
    {{
      "name": "实体名称",
      "entity_type": "component|tool|action|parameter|safety|material|definition",
      "source_evidence": "原文摘录",
      "battery_model": "{battery_model or 'unknown'}"
    }}
  ],
  "terms": [
    {{
      "term_id": "术语ID",
      "name": "术语名称",
      "definition": "术语定义"
    }}
  ]
}}

只返回JSON数组：'''

    try:
        result = self.llm.generate(prompt)
        data = self._parse_json_object(result)
        entities = data.get('entities', [])
        terms = data.get('terms', [])
        logger.info(f"Extracted {len(entities)} entities, {len(terms)} terms for {battery_model or 'unknown'}")
        return {'entities': entities[:max_items], 'terms': terms[:max_items]}
    except Exception as e:
        logger.error(f"Entity type extraction failed: {e}")
        return {'entities': [], 'terms': []}


def _parse_json_object(self, response: str) -> Dict[str, Any]:
    """Parse a JSON object from LLM response."""
    import json
    response = response.strip()
    if response.startswith("```"):
        lines = response.split("\n")
        json_content = []
        in_code_block = False
        for line in lines:
            if line.startswith("```"):
                in_code_block = not in_code_block
                continue
            if in_code_block:
                json_content.append(line)
        response = "\n".join(json_content)
    try:
        return json.loads(response)
    except:
        return {}
```

- [ ] **Step 2: Run extraction test**

Run: `cd D:\KG_project\Final4.14 && python -c "from src.importer.entity_extractor import EntityExtractor; from src.utils.llm_client import LLMClient; from src.config import settings; e = EntityExtractor(LLMClient(settings.openai_api_key, settings.openai_base_url, settings.llm_model)); result = e.extract_entities_with_types('拆卸电池包步骤：1. 使用扭矩扳手拧松高压连接器，扭矩25Nm。2. 拔出电芯。'); print(f'entities={len(result[\"entities\"])}, terms={len(result[\"terms\"])}')"`
Expected: entities>0 or terms>0

- [ ] **Step 3: Commit**

```bash
git add src/importer/entity_extractor.py
git commit -m "feat(extractor): add type-aware entity extraction"
```

---

## Task 3: Create L2Importer Orchestration Class

**Files:**
- Create: `src/importer/l2_importer.py`

- [ ] **Step 1: Write L2Importer class**

```python
from src.kg.client import Neo4jClient
from src.importer.entity_extractor import EntityExtractor
from src.utils.llm_client import LLMClient
from typing import Dict, Any, List, Tuple
import uuid
import logging

logger = logging.getLogger(__name__)


class L2Importer:
    def __init__(self, neo4j_client: Neo4jClient, llm_client: LLMClient):
        self.neo4j = neo4j_client
        self.extractor = EntityExtractor(llm_client)

    def import_pdf(self, full_text: str, filename: str) -> Dict[str, Any]:
        extraction = self.extractor.extract_entities_with_types(full_text, filename=filename)
        entities = extraction.get('entities', [])
        terms = extraction.get('terms', [])

        doc_id = str(uuid.uuid4())
        self._create_l2_document(doc_id, filename, full_text)

        entities_created = self._create_l2_entities(doc_id, entities)
        terms_created = self._create_l3_terms(doc_id, terms)
        relations = self._create_cross_layer_relations(doc_id, entities, terms)

        return {
            'doc_id': doc_id,
            'entities_created': entities_created,
            'terms_created': terms_created,
            'relations_created': relations,
            'errors': []
        }

    def _create_l2_document(self, doc_id: str, filename: str, full_text: str) -> None:
        cypher = '''
        CREATE (d:L2_Document {
            doc_id: $doc_id,
            name: $name,
            source: $source,
            content: $content,
            node_type: 'L2_Document'
        })
        '''
        self.neo4j.execute_query(cypher, {
            'doc_id': doc_id,
            'name': filename or 'unknown',
            'source': filename or 'unknown',
            'content': full_text[:50000]
        })

    def _create_l2_entities(self, doc_id: str, entities: List[Dict]) -> int:
        if not entities:
            return 0
        cypher = '''
        MATCH (d:L2_Document {doc_id: $doc_id})
        UNWIND $entities as ent
        CREATE (e:L2_Entity {
            id: $id,
            name: ent.name,
            entity_type: ent.entity_type,
            source_evidence: ent.source_evidence,
            battery_model: ent.battery_model,
            node_type: 'L2_Entity'
        })
        CREATE (d)-[:CONTAINS]->(e)
        RETURN count(e) as cnt
        '''
        entity_data = [{
            'id': str(uuid.uuid4()),
            'name': e.get('name', ''),
            'entity_type': e.get('entity_type', 'component'),
            'source_evidence': e.get('source_evidence', ''),
            'battery_model': e.get('battery_model', '')
        } for e in entities]

        result = self.neo4j.execute_query(cypher, {'doc_id': doc_id, 'entities': entity_data})
        return result[0].get('cnt', 0) if result else 0

    def _create_l3_terms(self, doc_id: str, terms: List[Dict]) -> int:
        if not terms:
            return 0
        cypher = '''
        MATCH (d:L2_Document {doc_id: $doc_id})
        UNWIND $terms as trm
        CREATE (t:L3_Term {
            id: $id,
            term_id: trm.term_id,
            name: trm.name,
            definition: trm.definition,
            source_document_id: $doc_id,
            node_type: 'L3_Term'
        })
        CREATE (d)-[:CONTAINS]->(t)
        RETURN count(t) as cnt
        '''
        term_data = [{
            'id': str(uuid.uuid4()),
            'term_id': t.get('term_id', ''),
            'name': t.get('name', ''),
            'definition': t.get('definition', '')
        } for t in terms]

        result = self.neo4j.execute_query(cypher, {'doc_id': doc_id, 'terms': term_data})
        return result[0].get('cnt', 0) if result else 0

    def _create_cross_layer_relations(self, doc_id: str, entities: List[Dict], terms: List[Dict]) -> int:
        """Create DEFINED_AS for definition-type entities, USES_TOOL for tool-using entities."""
        relations = 0

        entity_names = {e.get('name') for e in entities if e.get('entity_type') == 'definition'}
        for term in terms:
            term_name = term.get('name', '')
            if term_name in entity_names:
                cypher = '''
                MATCH (e:L2_Entity {name: $entity_name, doc_id: $doc_id})
                MATCH (t:L3_Term {name: $term_name, source_document_id: $doc_id})
                MERGE (e)-[r:DEFINED_AS]->(t)
                RETURN count(r) as cnt
                '''
                result = self.neo4j.execute_query(cypher, {
                    'entity_name': term_name,
                    'term_name': term_name,
                    'doc_id': doc_id
                })
                relations += result[0].get('cnt', 0) if result else 0

        tool_entities = [e for e in entities if e.get('entity_type') == 'tool']
        component_entities = [e for e in entities if e.get('entity_type') == 'component']
        for comp in component_entities:
            for tool in tool_entities:
                cypher = '''
                MATCH (c:L2_Entity {name: $comp_name, doc_id: $doc_id})
                MATCH (t:L2_Entity {name: $tool_name, doc_id: $doc_id})
                MERGE (c)-[r:USES_TOOL]->(t)
                RETURN count(r) as cnt
                '''
                result = self.neo4j.execute_query(cypher, {
                    'comp_name': comp.get('name'),
                    'tool_name': tool.get('name'),
                    'doc_id': doc_id
                })
                relations += result[0].get('cnt', 0) if result else 0

        for term in terms:
            cypher = '''
            MATCH (t:L3_Term {name: $name, source_document_id: $doc_id})
            MATCH (d:L2_Document {doc_id: $doc_id})
            MERGE (t)-[r:ORIGINATED_FROM]->(d)
            RETURN count(r) as cnt
            '''
            result = self.neo4j.execute_query(cypher, {
                'name': term.get('name'),
                'doc_id': doc_id
            })
            relations += result[0].get('cnt', 0) if result else 0

        for entity in entities:
            cypher = '''
            MATCH (e:L2_Entity {name: $name, doc_id: $doc_id})
            MATCH (d:L2_Document {doc_id: $doc_id})
            MERGE (e)-[r:REFERENCED_IN]->(d)
            RETURN count(r) as cnt
            '''
            result = self.neo4j.execute_query(cypher, {
                'name': entity.get('name'),
                'doc_id': doc_id
            })
            relations += result[0].get('cnt', 0) if result else 0

        return relations
```

- [ ] **Step 2: Run import test with mock**

Run: `cd D:\KG_project\Final4.14 && python -c "from src.importer.l2_importer import L2Importer; print('L2Importer imports OK')"`
Expected: L2Importer imports OK

- [ ] **Step 3: Commit**

```bash
git add src/importer/l2_importer.py
git commit -m "feat(l2): add L2Importer orchestration class"
```

---

## Task 4: Refactor /import/l2 Endpoint

**Files:**
- Modify: `src/api/import_routes.py:335-465`

- [ ] **Step 1: Replace import_l2 function**

Replace the existing `import_l2` function (lines 335-465) with:

```python
@router.post('/import/l2')
async def import_l2(file: UploadFile = File(...)):
    content = await file.read()

    if len(content) > MAX_FILE_SIZE:
        raise HTTPException(status_code=413, detail='File too large')

    import fitz
    import tempfile
    import os

    with tempfile.NamedTemporaryFile(delete=False, suffix='.pdf') as tmp:
        tmp.write(content)
        tmp_path = tmp.name

    try:
        doc = fitz.open(tmp_path)
        full_text = ''
        for page in doc:
            full_text += page.get_text()
        doc.close()
    finally:
        if os.path.exists(tmp_path):
            os.unlink(tmp_path)

    if not full_text.strip():
        raise HTTPException(status_code=400, detail='PDF is empty or could not extract text')

    from src.importer.l2_importer import L2Importer
    from src.kg.client import Neo4jClient
    from src.utils.llm_client import LLMClient
    from src.config import settings

    if not settings.openai_api_key:
        raise HTTPException(status_code=500, detail='OpenAI API key not configured')

    neo4j = Neo4jClient(settings.neo4j_uri, settings.neo4j_user, settings.neo4j_password)
    llm = LLMClient(
        api_key=settings.openai_api_key,
        base_url=settings.openai_base_url,
        model=settings.llm_model
    )

    try:
        importer = L2Importer(neo4j, llm)
        result = importer.import_pdf(full_text, file.filename or 'unknown')

        return {
            'code': 0,
            'message': f'L2 import completed: {result["entities_created"]} entities, {result["terms_created"]} terms, {result["relations_created"]} relations',
            'doc_id': result['doc_id'],
            'entities': result['entities_created'],
            'terms': result['terms_created'],
            'relations': result['relations_created'],
            'errors': result.get('errors', [])
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"L2 import failed: {e}")
        raise HTTPException(status_code=500, detail=f'L2 import failed: {str(e)}')
    finally:
        neo4j.close()
```

- [ ] **Step 2: Run import test**

Run: `cd D:\KG_project\Final4.14 && python -c "from src.api.import_routes import import_l2; print('import_l2 imports OK')"`
Expected: import_l2 imports OK

- [ ] **Step 3: Commit**

```bash
git add src/api/import_routes.py
git commit -m "feat(api): refactor /import/l2 to use L2Importer"
```

---

## Task 5: Write Unit Tests for L2Importer

**Files:**
- Create: `tests/importer/test_l2_importer.py`

- [ ] **Step 1: Write tests**

```python
import pytest
from unittest.mock import Mock, MagicMock
from src.importer.l2_importer import L2Importer


def test_l2_importer_init():
    mock_neo4j = Mock()
    mock_llm = Mock()
    importer = L2Importer(mock_neo4j, mock_llm)
    assert importer.neo4j is mock_neo4j
    assert importer.extractor is not None


def test_create_l2_document():
    mock_neo4j = Mock()
    mock_llm = Mock()
    importer = L2Importer(mock_neo4j, mock_llm)

    importer._create_l2_document('test-doc-id', 'test.pdf', 'full text')

    mock_neo4j.execute_query.assert_called_once()
    call_args = mock_neo4j.execute_query.call_args
    assert call_args[0][0] == '''CREATE (d:L2_Document {doc_id: $doc_id, name: $name, source: $source, content: $content, node_type: 'L2_Document'})'''


def test_create_l2_entities():
    mock_neo4j = Mock()
    mock_neo4j.execute_query.return_value = [{'cnt': 2}]
    mock_llm = Mock()
    importer = L2Importer(mock_neo4j, mock_llm)

    entities = [
        {'name': '电池包', 'entity_type': 'component', 'source_evidence': '原文', 'battery_model': 'test'},
        {'name': '扭矩扳手', 'entity_type': 'tool', 'source_evidence': '原文', 'battery_model': 'test'}
    ]

    count = importer._create_l2_entities('test-doc-id', entities)

    assert count == 2
    mock_neo4j.execute_query.assert_called_once()


def test_create_l3_terms():
    mock_neo4j = Mock()
    mock_neo4j.execute_query.return_value = [{'cnt': 1}]
    mock_llm = Mock()
    importer = L2Importer(mock_neo4j, mock_llm)

    terms = [{'term_id': 'T1', 'name': '预紧力', 'definition': 'definition text'}]

    count = importer._create_l3_terms('test-doc-id', terms)

    assert count == 1
    mock_neo4j.execute_query.assert_called_once()


def test_create_cross_layer_relations():
    mock_neo4j = Mock()
    mock_neo4j.execute_query.return_value = [{'cnt': 1}]
    mock_llm = Mock()
    importer = L2Importer(mock_neo4j, mock_llm)

    entities = [
        {'name': '预紧力定义', 'entity_type': 'definition', 'source_evidence': '', 'battery_model': ''},
        {'name': '电池包', 'entity_type': 'component', 'source_evidence': '', 'battery_model': ''},
        {'name': '扭矩扳手', 'entity_type': 'tool', 'source_evidence': '', 'battery_model': ''}
    ]
    terms = [{'term_id': 'T1', 'name': '预紧力', 'definition': '预紧力定义'}]

    relations = importer._create_cross_layer_relations('test-doc-id', entities, terms)

    assert relations > 0
```

- [ ] **Step 2: Run tests**

Run: `pytest tests/importer/test_l2_importer.py -v`
Expected: All tests PASS

- [ ] **Step 3: Commit**

```bash
git add tests/importer/test_l2_importer.py
git commit -m "test(l2): add unit tests for L2Importer"
```

---

## Task 6: Add API Integration Tests for /import/l2

**Files:**
- Modify: `tests/api/test_routes.py`

- [ ] **Step 1: Add import route tests**

Add to `tests/api/test_routes.py`:

```python
def test_import_l2_schema_validation():
    from src.api.schemas import L2EntityData, L2DocumentData, L3TermData
    entity = L2EntityData(name='电池包', entity_type='component', source_evidence='原文')
    assert entity.name == '电池包'
    assert entity.entity_type == 'component'

    term = L3TermData(term_id='T1', name='预紧力', definition='定义')
    assert term.name == '预紧力'
```

- [ ] **Step 2: Run tests**

Run: `pytest tests/api/test_routes.py -v`
Expected: All tests PASS

- [ ] **Step 3: Commit**

```bash
git add tests/api/test_routes.py
git commit -m "test(api): add L2 schema validation tests"
```

---

## Task 7: Verify End-to-End with Sample PDF

**Files:**
- None (manual verification)

- [ ] **Step 1: Run lint and typecheck**

Run: `cd D:\KG_project\Final4.14 && python -m pytest tests/ -v --tb=short 2>&1 | head -50`
Expected: All tests pass

- [ ] **Step 2: Verify cross-layer query works**

Run in Neo4j browser after importing:
```cypher
MATCH (d:L2_Document)-[:CONTAINS]->(e:L2_Entity)-[:DEFINED_AS]->(t:L3_Term)
RETURN d.name, e.name, t.name LIMIT 20
```

- [ ] **Step 3: Verify no L1 nodes created by L2 import**

```cypher
MATCH (n) WHERE n.node_type IN ['L2_Document', 'L2_Entity', 'L3_Term']
RETURN count(n)
```

---

## Self-Review Checklist

- [ ] Spec coverage: L2 import creates L2_Document, L2_Entity, L3_Term nodes
- [ ] Cross-layer relations (CONTAINS, DEFINED_AS, USES_TOOL, REFERENCED_IN, ORIGINATED_FROM) implemented
- [ ] No placeholders in code
- [ ] Type consistency: `node_type` field used consistently (L2_Document, L2_Entity, L3_Term)
- [ ] Tests cover L2Importer, schema validation
- [ ] Existing L1 import flow unchanged

---

**Plan complete.** Two execution options:

**1. Subagent-Driven (recommended)** - I dispatch a fresh subagent per task, review between tasks, fast iteration

**2. Inline Execution** - Execute tasks in this session using executing-plans, batch execution with checkpoints

Which approach?