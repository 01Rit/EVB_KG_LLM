# 阶段2：混合图输出 + 拆卸序列规划 + 人机协作分配 实现计划

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 实现PDF数据导入、拆卸序列规划、人机协作分配、混合图输出功能

**Architecture:** PyMuPDF解析 + Tarjan环路检测 + 拓扑排序 + MTM时间估算 + LLM 9因素打分 + AS自动化得分

**Tech Stack:** Python 3.11+, PyMuPDF(fitz), networkx, Neo4j, OpenAI GPT-4o

---

## 文件结构

```
src/
├── importer/
│   ├── __init__.py
│   ├── pdf_parser.py
│   ├── path_classifier.py
│   ├── entity_extractor.py
│   └── importer.py
├── sequence/
│   ├── __init__.py
│   ├── planner.py
│   ├── cycle_detector.py
│   ├── topological_sort.py
│   └── time_estimator.py
├── allocator/
│   ├── __init__.py
│   ├── scorer.py
│   ├── as_calculator.py
│   └── allocator.py
├── graph_output/
│   ├── __init__.py
│   ├── mermaid_gen.py
│   ├── json_builder.py
│   └── generator.py
```

---

### Task 1: 数据导入模块 - 路径分类器

**Files:**
- Create: `src/importer/__init__.py`
- Create: `src/importer/path_classifier.py`
- Create: `tests/importer/test_path_classifier.py`

- [ ] **Step 1: 创建 src/importer/__init__.py**

```python
```

- [ ] **Step 2: 创建 src/importer/path_classifier.py**

```python
import re
from pathlib import Path
from typing import Dict, Any


class PathClassifier:
    SOURCE_PATTERNS = {
        'patent': [r'专利', r'CN\d', r'WO\d', r'\d+发明专利'],
        'standard': [r'国标', r'GBT', r'GB/T', r'\d+-+\d+'],
        'paper': [r'学术论文', r'论文', r'journal', r'IEEE']
    }

    def classify(self, file_path: str) -> Dict[str, Any]:
        path = Path(file_path)
        filename = path.stem

        for source, patterns in self.SOURCE_PATTERNS.items():
            for pattern in patterns:
                if re.search(pattern, file_path, re.IGNORECASE):
                    return {
                        'source': source,
                        'source_type': 'pdf',
                        'file_name': filename,
                        'target_layers': ['L2', 'L3']
                    }

        return {
            'source': 'other',
            'source_type': 'pdf',
            'file_name': filename,
            'target_layers': ['L2', 'L3']
        }

    def get_metadata(self, file_path: str) -> Dict[str, Any]:
        path = Path(file_path)
        return {
            'file_name': path.stem,
            'file_extension': path.suffix,
            'file_size': path.stat().st_size if path.exists() else 0
        }
```

- [ ] **Step 3: 创建 tests/importer/test_path_classifier.py**

```python
import pytest
from src.importer.path_classifier import PathClassifier


def test_path_classifier_import():
    assert PathClassifier is not None


def test_patent_classification():
    classifier = PathClassifier()
    result = classifier.classify('D:/data/专利_动力电池拆卸.pdf')
    assert result['source'] == 'patent'


def test_standard_classification():
    classifier = PathClassifier()
    result = classifier.classify('D:/data/GBT_12345.pdf')
    assert result['source'] == 'standard'


def test_paper_classification():
    classifier = PathClassifier()
    result = classifier.classify('D:/data/学术论文_电池回收.pdf')
    assert result['source'] == 'paper'


def test_other_classification():
    classifier = PathClassifier()
    result = classifier.classify('D:/data/unknown_file.pdf')
    assert result['source'] == 'other'
```

- [ ] **Step 4: 运行测试验证失败**

```bash
cd D:/KG_project/Final4.14
python -m pytest tests/importer/test_path_classifier.py -v
```

- [ ] **Step 5: Commit**

```bash
git add src/importer/ tests/importer/
git commit -m feat: add Path Classifier module
```

---

### Task 2: 数据导入模块 - PDF解析器

**Files:**
- Create: `src/importer/pdf_parser.py`
- Create: `tests/importer/test_pdf_parser.py`

- [ ] **Step 1: 创建 src/importer/pdf_parser.py**

```python
import fitz
from typing import Dict, Any, List, Optional
import logging

logger = logging.getLogger(__name__)


class PDFParser:
    def __init__(self, extract_images: bool = False):
        self.extract_images = extract_images

    def parse(self, file_path: str) -> Dict[str, Any]:
        try:
            doc = fitz.open(file_path)
        except Exception as e:
            logger.error(f"Failed to open PDF {file_path}: {e}")
            raise

        text_content = []
        for page_num, page in enumerate(doc):
            text = page.get_text()
            text_content.append({
                'page': page_num + 1,
                'text': text
            })

        doc.close()

        return {
            'file_path': file_path,
            'page_count': len(text_content),
            'pages': text_content,
            'full_text': '\n\n'.join([p['text'] for p in text_content])
        }

    def extract_metadata(self, file_path: str) -> Dict[str, Any]:
        doc = fitz.open(file_path)
        metadata = {
            'title': doc.metadata.get('title', ''),
            'author': doc.metadata.get('author', ''),
            'subject': doc.metadata.get('subject', ''),
            'creator': doc.metadata.get('creator', ''),
            'page_count': len(doc)
        }
        doc.close()
        return metadata

    def extract_images(self, file_path: str) -> List[Dict[str, Any]]:
        if not self.extract_images:
            return []

        images = []
        doc = fitz.open(file_path)

        for page_num, page in enumerate(doc):
            image_list = page.get_images()
            for img_index, img in enumerate(image_list):
                images.append({
                    'page': page_num + 1,
                    'index': img_index,
                    'xref': img[0]
                })

        doc.close()
        return images
```

- [ ] **Step 2: 创建 tests/importer/test_pdf_parser.py**

```python
import pytest
from src.importer.pdf_parser import PDFParser


def test_pdf_parser_import():
    assert PDFParser is not None


def test_pdf_parser_initialization():
    parser = PDFParser()
    assert parser.extract_images is False


def test_pdf_parser_with_images():
    parser = PDFParser(extract_images=True)
    assert parser.extract_images is True
```

- [ ] **Step 3: 运行测试**

```bash
python -m pytest tests/importer/test_pdf_parser.py -v
```

- [ ] **Step 4: Commit**

```bash
git add src/importer/pdf_parser.py tests/importer/
git commit -m feat: add PDF Parser module
```

---

### Task 3: 数据导入模块 - 实体提取器

**Files:**
- Create: `src/importer/entity_extractor.py`
- Create: `tests/importer/test_entity_extractor.py`

- [ ] **Step 1: 创建 src/importer/entity_extractor.py**

```python
from src.utils.llm_client import LLMClient
from typing import Dict, List, Any, Optional
import logging
import json
import re

logger = logging.getLogger(__name__)


class EntityExtractor:
    def __init__(self, llm_client: LLMClient):
        self.llm = llm_client

    def extract_components(self, text: str, max_items: int = 50) -> List[Dict[str, Any]]:
        prompt = f'''从以下技术文档中提取所有可拆卸部件（L2层Document）。

提取要求：
- 部件名称
- 所属类别（如电池包、模组、外壳等）
- 拆卸工具
- 安全等级（1-5）
- 依赖关系（如果有）

返回JSON数组格式。

文档内容：
{text[:3000]}

返回格式：
[
  {{"name": "部件名", "category": "类别", "tools": ["工具1"], "safety_level": 1, "dependencies": ["依赖部件"]}}
]'''

        try:
            result = self.llm.generate(prompt)
            components = self._parse_json_array(result)
            logger.info(f"Extracted {len(components)} components")
            return components[:max_items]
        except Exception as e:
            logger.error(f"Component extraction failed: {e}")
            return []

    def extract_terms(self, text: str, max_items: int = 100) -> List[Dict[str, Any]]:
        prompt = f'''从以下技术文档中提取所有专业术语（L3层Term）。

提取要求：
- 术语名称
- 定义/解释
- 英文缩写（如果有）

返回JSON数组格式。

文档内容：
{text[:3000]}

返回格式：
[
  {{"term_id": "术语名", "definition": "定义", "units": "单位或null"}}
]'''

        try:
            result = self.llm.generate(prompt)
            terms = self._parse_json_array(result)
            logger.info(f"Extracted {len(terms)} terms")
            return terms[:max_items]
        except Exception as e:
            logger.error(f"Term extraction failed: {e}")
            return []

    def _parse_json_array(self, response: str) -> List[Dict[str, Any]]:
        response = response.strip()

        if response.startswith('['):
            try:
                return json.loads(response)
            except:
                pass

        lines = response.split('\n')
        items = []
        json_str = '['
        for line in lines:
            if '{' in line:
                json_str = line
            elif '}' in line and json_str != '[':
                json_str += '}'
                try:
                    items.append(json.loads(json_str))
                    json_str = '['
                except:
                    json_str = '['

        return items
```

- [ ] **Step 2: 创建 tests/importer/test_entity_extractor.py**

```python
import pytest
from src.importer.entity_extractor import EntityExtractor


def test_entity_extractor_import():
    assert EntityExtractor is not None


class MockLLM:
    def generate(self, prompt):
        return '[{"name": "BatteryCover", "category": "外壳", "tools": ["螺丝刀"], "safety_level": 1, "dependencies": []}]'


def test_entity_extractor_initialization():
    extractor = EntityExtractor(MockLLM())
    assert extractor.llm is not None


def test_extract_components():
    extractor = EntityExtractor(MockLLM())
    result = extractor.extract_components("test text")
    assert len(result) > 0
    assert result[0]['name'] == 'BatteryCover'
```

- [ ] **Step 3: 运行测试**

```bash
python -m pytest tests/importer/test_entity_extractor.py -v
```

- [ ] **Step 4: Commit**

```bash
git add src/importer/entity_extractor.py tests/importer/
git commit -m feat: add Entity Extractor module
```

---

### Task 4: 数据导入模块 - 导入主逻辑

**Files:**
- Create: `src/importer/importer.py`
- Create: `tests/importer/test_importer.py`

- [ ] **Step 1: 创建 src/importer/importer.py**

```python
from src.importer.path_classifier import PathClassifier
from src.importer.pdf_parser import PDFParser
from src.importer.entity_extractor import EntityExtractor
from src.kg.client import Neo4jClient
from src.utils.llm_client import LLMClient
from typing import Optional, Dict, Any
import logging
import uuid

logger = logging.getLogger(__name__)


class ImportResult:
    def __init__(self, success: bool, doc_id: str = '', message: str = '', components: int = 0, terms: int = 0):
        self.success = success
        self.doc_id = doc_id
        self.message = message
        self.components = components
        self.terms = terms


class DataImporter:
    def __init__(self, neo4j_client: Neo4jClient, llm_client: LLMClient):
        self.neo4j = neo4j_client
        self.classifier = PathClassifier()
        self.parser = PDFParser()
        self.extractor = EntityExtractor(llm_client)

    def import_pdf(self, file_path: str) -> ImportResult:
        classification = self.classifier.classify(file_path)
        file_metadata = self.classifier.get_metadata(file_path)

        try:
            parsed = self.parser.parse(file_path)
        except Exception as e:
            logger.error(f"PDF parsing failed: {e}")
            return ImportResult(False, message=str(e))

        doc_id = str(uuid.uuid4())

        try:
            components = self.extractor.extract_components(parsed['full_text'])
            terms = self.extractor.extract_terms(parsed['full_text'])
        except Exception as e:
            logger.warning(f"Entity extraction failed: {e}")
            components = []
            terms = []

        self._save_to_graph(doc_id, classification, file_metadata, parsed, components, terms)

        return ImportResult(
            success=True,
            doc_id=doc_id,
            components=len(components),
            terms=len(terms)
        )

    def _save_to_graph(self, doc_id: str, classification: Dict, file_metadata: Dict,
                  parsed: Dict, components: List[Dict], terms: List[Dict]):
        cypher = '''
        CREATE (d:Document {
            doc_id: $doc_id,
            title: $title,
            source: $source,
            source_type: $source_type,
            content: $content,
            file_path: $file_path,
            metadata: $metadata
        })
        '''

        self.neo4j.execute_query(cypher, {
            'doc_id': doc_id,
            'title': file_metadata['file_name'],
            'source': classification['source'],
            'source_type': classification['source_type'],
            'content': parsed['full_text'][:50000],
            'file_path': parsed['file_path'],
            'metadata': str(file_metadata)
        })

        for comp in components:
            self._create_component(doc_id, comp)

        for term in terms:
            self._create_term(doc_id, term)

    def _create_component(self, doc_id: str, component: Dict):
        cypher = '''
        MATCH (d:Document {doc_id: $doc_id})
        CREATE (c:Component {
            id: $id,
            name: $name,
            category: $category,
            tool_required: $tools,
            safety_level: $safety,
            source_doc_id: $doc_id
        })
        CREATE (d)-[:CONTAINS]->(c)
        '''

        self.neo4j.execute_query(cypher, {
            'id': str(uuid.uuid4()),
            'name': component.get('name', ''),
            'category': component.get('category', ''),
            'tools': str(component.get('tools', [])),
            'safety': component.get('safety_level', 1),
            'doc_id': doc_id
        })

    def _create_term(self, doc_id: str, term: Dict):
        cypher = '''
        MATCH (d:Document {doc_id: $doc_id})
        CREATE (t:Term {
            term_id: $term_id,
            definition: $definition,
            units: $units,
            source_doc_id: $doc_id
        })
        CREATE (d)-[:CONTAINS]->(t)
        '''

        self.neo4j.execute_query(cypher, {
            'term_id': term.get('term_id', ''),
            'definition': term.get('definition', ''),
            'units': term.get('units'),
            'doc_id': doc_id
        })

    def promote_to_component(self, doc_id: str, component_data: Dict) -> bool:
        cypher = '''
        MATCH (d:Document {doc_id: $doc_id})
        SET d.source_type = 'manual'
        CREATE (c:Component {
            id: $id,
            name: $name,
            battery_model: $battery_model,
            tool_required: $tools,
            safety_level: $safety,
            source_type: 'manual',
            precedence: $precedence
        })
        CREATE (d)-[:PROMOTED_TO]->(c)
        RETURN c
        '''

        try:
            result = self.neo4j.execute_query(cypher, {
                'doc_id': doc_id,
                'id': str(uuid.uuid4()),
                'name': component_data.get('name', ''),
                'battery_model': component_data.get('battery_model', ''),
                'tools': str(component_data.get('tool_required', [])),
                'safety': component_data.get('safety_level', 1),
                'precedence': str(component_data.get('precedence', []))
            })
            return len(result) > 0
        except Exception as e:
            logger.error(f"Promotion failed: {e}")
            return False
```

- [ ] **Step 2: 创建 tests/importer/test_importer.py**

```python
import pytest
from src.importer.importer import DataImporter, ImportResult


def test_importer_import():
    assert DataImporter is not None


def test_import_result_success():
    result = ImportResult(True, 'test-id', 'success', 5, 10)
    assert result.success is True
    assert result.doc_id == 'test-id'
    assert result.components == 5
    assert result.terms == 10


def test_import_result_failure():
    result = ImportResult(False, '', 'Error message', 0, 0)
    assert result.success is False
    assert result.message == 'Error message'
```

- [ ] **Step 3: 运行测试**

```bash
python -m pytest tests/importer/test_importer.py -v
```

- [ ] **Step 4: Commit**

```bash
git add src/importer/importer.py tests/importer/
git commit -m feat: add Data Importer module
```

---

### Task 5: 管理界面API

**Files:**
- Create: `src/api/admin_routes.py`
- Modify: `src/main.py`

- [ ] **Step 1: 创建 src/api/admin_routes.py**

```python
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional, List
import logging

logger = logging.getLogger(__name__)

router = APIRouter()


class PromoteRequest(BaseModel):
    doc_id: str
    name: str
    battery_model: str
    tool_required: List[str] = []
    safety_level: int = 1
    precedence: List[str] = []


class DocumentResponse(BaseModel):
    doc_id: str
    title: str
    source: str
    component_count: int


class ComponentResponse(BaseModel):
    id: str
    name: str
    battery_model: str


@router.get('/api/v1/admin/documents')
async def list_documents():
    from src.kg.client import Neo4jClient
    from src.config import settings

    neo4j = Neo4jClient(settings.neo4j_uri, settings.neo4j_user, settings.neo4j_password)
    cypher = '''
    MATCH (d:Document)
    OPTIONAL MATCH (d)-[:CONTAINS]->(c:Component)
    RETURN d.doc_id as doc_id, d.title as title, d.source as source,
           count(c) as component_count
    ORDER BY d.title
    '''
    results = neo4j.execute_query(cypher)

    return [DocumentResponse(
        doc_id=r['doc_id'],
        title=r['title'],
        source=r['source'],
        component_count=r['component_count']
    ) for r in results]


@router.post('/api/v1/admin/components/promote')
async def promote_document(request: PromoteRequest):
    from src.kg.client import Neo4jClient
    from src.utils.llm_client import LLMClient
    from src.config import settings
    from src.importer.importer import DataImporter

    neo4j = Neo4jClient(settings.neo4j_uri, settings.neo4j_user, settings.neo4j_password)
    llm = LLMClient(settings.openai_api_key, settings.openai_base_url)

    importer = DataImporter(neo4j, llm)
    component_data = {
        'name': request.name,
        'battery_model': request.battery_model,
        'tool_required': request.tool_required,
        'safety_level': request.safety_level,
        'precedence': request.precedence
    }

    success = importer.promote_to_component(request.doc_id, component_data)

    if not success:
        raise HTTPException(status_code=500, detail='Promotion failed')

    return {'code': 0, 'message': 'Component promoted successfully'}


@router.get('/api/v1/admin/components')
async def list_components():
    from src.kg.client import Neo4jClient
    from src.config import settings

    neo4j = Neo4jClient(settings.neo4j_uri, settings.neo4j_user, settings.neo4j_password)
    cypher = '''
    MATCH (c:Component {source_type: 'manual'})
    RETURN c.id as id, c.name as name, c.battery_model as battery_model
    ORDER BY c.name
    '''
    results = neo4j.execute_query(cypher)

    return [ComponentResponse(
        id=r['id'],
        name=r['name'],
        battery_model=r['battery_model']
    ) for r in results]
```

- [ ] **Step 2: 更新src/main.py导入admin路由**

```python
from fastapi import FastAPI
from src.api.routes import router
from src.api.middleware import logging_middleware
from src.api.admin_routes import router as admin_router
from src.logs import logger

app = FastAPI(title='动力电池拆卸知识图谱推理系统', version='1.0.0')

app.middleware('http')(logging_middleware)

app.include_router(router)
app.include_router(admin_router, prefix='/admin')


@app.on_event('shutdown')
async def shutdown_event():
    logger.info('Shutting down application')
    neo4j_client.close()
    if milvus_client:
        milvus_client.close()


if __name__ == '__main__':
    import uvicorn
    uvicorn.run(app, host='0.0.0.0', port=8000)
```

- [ ] **Step 3: Commit**

```bash
git add src/api/admin_routes.py src/main.py
git commit -m feat: add admin routes for L1 component promotion
```

---

### Task 6: 拆卸序列模块 - Tarjan环路检测

**Files:**
- Create: `src/sequence/__init__.py`
- Create: `src/sequence/cycle_detector.py`
- Create: `tests/sequence/test_cycle_detector.py`

- [ ] **Step 1: 创建 src/sequence/__init__.py**

```python
```

- [ ] **Step 2: 创建 src/sequence/cycle_detector.py**

```python
import networkx as nx
from typing import List, Tuple, Dict, Any
import logging

logger = logging.getLogger(__name__)


class CycleDetector:
    def __init__(self):
        self.graph = None

    def build_graph(self, components: List[Dict]) -> nx.DiGraph:
        graph = nx.DiGraph()

        for comp in components:
            comp_id = comp.get('id') or comp.get('name', '')
            graph.add_node(comp_id, **comp)

        for comp in components:
            comp_id = comp.get('id') or comp.get('name', '')
            dependencies = comp.get('precedence', []) or comp.get('dependencies', [])

            for dep in dependencies:
                graph.add_edge(comp_id, dep)

        self.graph = graph
        return graph

    def find_strongly_connected_components(self) -> List[List[str]]:
        if not self.graph:
            raise RuntimeError("Graph not built")

        sccs = list(nx.strongly_connected_components(self.graph))
        sccs = [scc for scc in sccs if len(scc) > 1]

        logger.info(f"Found {len(sccs)} strongly connected components (cycles)")
        return sccs

    def has_cycles(self) -> bool:
        if not self.graph:
            raise RuntimeError("Graph not built")

        try:
            nx.find_cycle(self.graph)
            return True
        except nx.NetworkXNoCycle:
            return False

    def detect_cycles(self) -> List[List[str]]:
        if not self.graph:
            raise RuntimeError("Graph not built")

        cycles = []
        try:
            for cycle in nx.simple_cycles(self.graph):
                if len(cycle) > 1:
                    cycles.append(cycle)
        except:
            pass

        logger.info(f"Detected {len(cycles)} cycles")
        return cycles

    def break_cycles(self, method: str = 'remove_last') -> nx.DiGraph:
        if not self.graph:
            raise RuntimeError("Graph not built")

        broken_graph = self.graph.copy()

        cycles = list(nx.simple_cycles(broken_graph))

        for cycle in cycles:
            if len(cycle) > 1:
                if method == 'remove_last':
                    broken_graph.remove_edge(cycle[-1], cycle[0])
                elif method == 'remove_first':
                    broken_graph.remove_edge(cycle[0], cycle[1])
                elif method == 'break_all':
                    for i in range(len(cycle) - 1):
                        broken_graph.remove_edge(cycle[i], cycle[(i + 1) % len(cycle)])

        broken_graph.remove_nodes_from(list(nx.isolates(broken_graph)))

        logger.info(f"Broke cycles using {method}")
        return broken_graph
```

- [ ] **Step 3: 创建 tests/sequence/test_cycle_detector.py**

```python
import pytest
from src.sequence.cycle_detector import CycleDetector


def test_cycle_detector_import():
    assert CycleDetector is not None


def test_build_graph():
    detector = CycleDetector()
    components = [
        {'id': 'A', 'precedence': ['B']},
        {'id': 'B', 'precedence': []},
    ]
    graph = detector.build_graph(components)
    assert graph.number_of_nodes() == 2
    assert graph.number_of_edges() == 1


def test_detect_cycles():
    detector = CycleDetector()
    components = [
        {'id': 'A', 'precedence': ['B']},
        {'id': 'B', 'precedence': ['A']},
    ]
    detector.build_graph(components)
    cycles = detector.detect_cycles()
    assert len(cycles) > 0


def test_has_cycles():
    detector = CycleDetector()
    components = [
        {'id': 'A', 'precedence': ['B']},
        {'id': 'B', 'precedence': ['A']},
    ]
    detector.build_graph(components)
    assert detector.has_cycles() is True


def test_no_cycles():
    detector = CycleDetector()
    components = [
        {'id': 'A', 'precedence': []},
        {'id': 'B', 'precedence': ['A']},
    ]
    detector.build_graph(components)
    assert detector.has_cycles() is False


def test_break_cycles():
    detector = CycleDetector()
    components = [
        {'id': 'A', 'precedence': ['B']},
        {'id': 'B', 'precedence': ['A']},
    ]
    detector.build_graph(components)
    broken = detector.break_cycles()
    assert broken.number_of_edges() < detector.graph.number_of_edges()
```

- [ ] **Step 4: 运行测试**

```bash
python -m pytest tests/sequence/test_cycle_detector.py -v
```

- [ ] **Step 5: Commit**

```bash
git add src/sequence/cycle_detector.py tests/sequence/
git commit -m feat: add Tarjan cycle detector
```

---

### Task 7: 拆卸序列模块 - 拓扑排序

**Files:**
- Create: `src/sequence/topological_sort.py`
- Create: `tests/sequence/test_topological_sort.py`

- [ ] **Step 1: 创建 src/sequence/topological_sort.py**

```python
import networkx as nx
from typing import List, Optional
import logging

logger = logging.getLogger(__name__)


class TopologicalSort:
    def __init__(self):
        self.graph = None

    def set_graph(self, graph: nx.DiGraph):
        self.graph = graph

    def sort(self) -> List[str]:
        if not self.graph:
            raise RuntimeError("Graph not set")

        try:
            sorted_list = list(nx.topological_sort(self.graph))
            logger.info(f"Topological sort produced {len(sorted_list)} items")
            return sorted_list
        except nx.NetworkXError as e:
            logger.error(f"Topological sort failed: {e}")
            raise

    def get_parallel_groups(self) -> List[List[str]]:
        if not self.graph:
            raise RuntimeError("Graph not set")

        inDegree = {}
        for node in self.graph.nodes():
            inDegree[node] = self.graph.in_degree(node)

        groups = []
        processed = set()

        while len(processed) < self.graph.number_of_nodes():
            current_group = []

            for node in self.graph.nodes():
                if node not in processed and inDegree[node] == 0:
                    current_group.append(node)

            if not current_group:
                break

            groups.append(current_group)

            for node in current_group:
                processed.add(node)
                for neighbor in self.graph.successors(node):
                    inDegree[neighbor] -= 1

        logger.info(f"Generated {len(groups)} parallel groups")
        return groups

    def reverse_sort(self) -> List[str]:
        if not self.graph:
            raise RuntimeError("Graph not set")

        reversed_graph = self.graph.reverse()

        try:
            sorted_list = list(nx.topological_sort(reversed_graph))
            return sorted_list
        except nx.NetworkXError as e:
            logger.error(f"Reverse topological sort failed: {e}")
            raise
```

- [ ] **Step 2: 创建 tests/sequence/test_topological_sort.py**

```python
import pytest
from src.sequence.topological_sort import TopologicalSort
import networkx as nx


def test_topological_sort_import():
    assert TopologicalSort is not None


def test_sort_linear():
    sorter = TopologicalSort()
    graph = nx.DiGraph()
    graph.add_edges_from([('A', 'B'), ('B', 'C')])
    sorter.set_graph(graph)
    result = sorter.sort()
    assert len(result) == 3


def test_get_parallel_groups():
    sorter = TopologicalSort()
    graph = nx.DiGraph()
    graph.add_edges_from([('A', 'C'), ('B', 'C')])
    sorter.set_graph(graph)
    groups = sorter.get_parallel_groups()
    assert len(groups) >= 2


def test_reverse_sort():
    sorter = TopologicalSort()
    graph = nx.DiGraph()
    graph.add_edges_from([('A', 'B'), ('B', 'C')])
    sorter.set_graph(graph)
    result = sorter.reverse_sort()
    assert len(result) == 3
```

- [ ] **Step 3: 运行测试**

```bash
python -m pytest tests/sequence/test_topological_sort.py -v
```

- [ ] **Step 4: Commit**

```bash
git add src/sequence/topological_sort.py tests/sequence/
git commit -m feat: add topological sort module
```

---

### Task 8: 拆卸序列模块 - MTM时间估算

**Files:**
- Create: `src/sequence/time_estimator.py`
- Create: `tests/sequence/test_time_estimator.py`

- [ ] **Step 1: 创建 src/sequence/time_estimator.py**

```python
from typing import Dict, List, Any
import logging

logger = logging.getLogger(__name__)


class TimeEstimator:
    MTM_BASE_SECONDS = 85

    TOOL_SWITCH_TIMES = {
        'screwdriver': 5,
        'wrench': 5,
        'plier': 3,
        'hammer': 2,
        'heat_gun': 10,
        'extractor': 8,
        'none': 0
    }

    POSITION_TIMES = {
        'easy': 5,
        'medium': 15,
        'difficult': 30
    }

    def __init__(self):
        self.default_tool_switch = 5
        self.default_position = 15

    def calculate_time(self, operation_time_score: float = 1.0,
                   tool_switch_time: int = 0,
                   position_move_time: int = 0) -> int:
        if tool_switch_time == 0:
            tool_switch_time = self.default_tool_switch
        if position_move_time == 0:
            position_move_time = self.default_position

        score = operation_time_score

        time_seconds = (score / 5) * self.MTM_BASE_SECONDS + tool_switch_time + position_move_time

        return int(time_seconds)

    def estimate_from_component(self, component: Dict) -> int:
        operation_score = component.get('operation_time_score', 1.0)

        tools = component.get('tool_required', [])
        tool_time = max(
            [self.TOOL_SWITCH_TIMES.get(t.lower(), self.default_tool_switch) for t in tools],
            default=0
        )

        position = component.get('position_difficulty', 'medium')
        position_time = self.POSITION_TIMES.get(position.lower(), self.default_position)

        return self.calculate_time(operation_score, tool_time, position_time)

    def estimate_sequence_time(self, components: List[Dict]) -> Dict:
        total_time = 0
        details = []

        for comp in components:
            comp_id = comp.get('id', '') or comp.get('name', '')
            time = self.estimate_from_component(comp)
            total_time += time
            details.append({'component': comp_id, 'time': time})

        return {
            'total_seconds': total_time,
            'total_minutes': round(total_time / 60, 1),
            'details': details
        }
```

- [ ] **Step 2: 创建 tests/sequence/test_time_estimator.py**

```python
import pytest
from src.sequence.time_estimator import TimeEstimator


def test_time_estimator_import():
    assert TimeEstimator is not None


def test_calculate_time():
    estimator = TimeEstimator()
    result = estimator.calculate_time(1.0, 5, 15)
    assert result > 0


def test_calculate_time_defaults():
    estimator = TimeEstimator()
    result = estimator.calculate_time(1.0)
    assert result > 0


def test_estimate_from_component():
    estimator = TimeEstimator()
    component = {'id': 'A', 'tool_required': ['screwdriver']}
    result = estimator.estimate_from_component(component)
    assert result > 0


def test_estimate_sequence_time():
    estimator = TimeEstimator()
    components = [
        {'id': 'A', 'tool_required': ['screwdriver']},
        {'id': 'B', 'tool_required': ['wrench']},
    ]
    result = estimator.estimate_sequence_time(components)
    assert result['total_seconds'] > 0
    assert len(result['details']) == 2
```

- [ ] **Step 3: 运行测试**

```bash
python -m pytest tests/sequence/test_time_estimator.py -v
```

- [ ] **Step 4: Commit**

```bash
git add src/sequence/time_estimator.py tests/sequence/
git commit -m feat: add MTM time estimator
```

---

### Task 9: 拆卸序列模块 - 序列规划主逻辑

**Files:**
- Create: `src/sequence/planner.py`
- Create: `tests/sequence/test_planner.py`

- [ ] **Step 1: 创建 src/sequence/planner.py**

```python
from src.sequence.cycle_detector import CycleDetector
from src.sequence.topological_sort import TopologicalSort
from src.sequence.time_estimator import TimeEstimator
from src.kg.client import Neo4jClient
from pydantic import BaseModel
from typing import List, Optional, Dict, Any
import logging

logger = logging.getLogger(__name__)


class DisassemblySequence(BaseModel):
    battery_model: str
    steps: List[Dict[str, Any]]
    parallel_groups: List[List[str]]
    total_time_seconds: int
    cycle_count: int


class SequencePlanner:
    def __init__(self, neo4j_client: Optional[Neo4jClient] = None):
        self.neo4j = neo4j_client
        self.cycle_detector = CycleDetector()
        self.topological_sort = TopologicalSort()
        self.time_estimator = TimeEstimator()

    def plan(self, battery_model: str, components: List[Dict] = None) -> DisassemblySequence:
        if components is None:
            components = self._load_components(battery_model)

        if not components:
            logger.warning(f"No components found for {battery_model}")
            return DisassemblySequence(
                battery_model=battery_model,
                steps=[],
                parallel_groups=[],
                total_time_seconds=0,
                cycle_count=0
            )

        self.cycle_detector.build_graph(components)
        cycles = self.cycle_detector.detect_cycles()
        cycle_count = len(cycles)

        if cycles:
            broken_graph = self.cycle_detector.break_cycles()
        else:
            broken_graph = self.cycle_detector.graph

        self.topological_sort.set_graph(broken_graph)
        sorted_ids = self.topological_sort.sort()
        parallel_groups = self.topological_sort.get_parallel_groups()

        component_map = {c.get('id', ''): c for c in components}
        component_map.update({c.get('name', ''): c for c in components})

        steps = []
        for step_num, comp_id in enumerate(sorted_ids, 1):
            comp = component_map.get(comp_id, {})
            time = self.time_estimator.estimate_from_component(comp)
            steps.append({
                'step': step_num,
                'component': comp_id,
                'component_name': comp.get('name', comp_id),
                'time_seconds': time,
                'tool_required': comp.get('tool_required', []),
                'safety_level': comp.get('safety_level', 1)
            })

        total_time = sum(s['time_seconds'] for s in steps)

        result = DisassemblySequence(
            battery_model=battery_model,
            steps=steps,
            parallel_groups=parallel_groups,
            total_time_seconds=total_time,
            cycle_count=cycle_count
        )

        logger.info(f"Generated sequence with {len(steps)} steps, {cycle_count} cycles")
        return result

    def _load_components(self, battery_model: str) -> List[Dict]:
        if not self.neo4j:
            return []

        cypher = '''
        MATCH (c:Component {battery_model: $model})
        RETURN c.id as id, c.name as name, c.tool_required as tool_required,
               c.safety_level as safety_level, c.precedence as precedence
        '''

        results = self.neo4j.execute_query(cypher, {'model': battery_model})

        components = []
        for r in results:
            precedence = []
            if r.get('precedence'):
                try:
                    precedence = eval(r['precedence']) if isinstance(r['precedence'], str) else r['precedence']
                except:
                    precedence = []

            components.append({
                'id': r.get('id', ''),
                'name': r.get('name', ''),
                'tool_required': r.get('tool_required', []),
                'safety_level': r.get('safety_level', 1),
                'precedence': precedence
            })

        return components
```

- [ ] **Step 2: 创建 tests/sequence/test_planner.py**

```python
import pytest
from src.sequence.planner import SequencePlanner, DisassemblySequence


def test_planner_import():
    assert SequencePlanner is not None


def test_disassembly_sequence_model():
    seq = DisassemblySequence(
        battery_model='test-model',
        steps=[{'step': 1, 'component': 'A', 'time_seconds': 30}],
        parallel_groups=[['A']],
        total_time_seconds=30,
        cycle_count=0
    )
    assert seq.battery_model == 'test-model'
    assert len(seq.steps) == 1


def test_plan_empty_components():
    planner = SequencePlanner()
    result = planner.plan('test-model', [])
    assert result.battery_model == 'test-model'
    assert len(result.steps) == 0


def test_plan_with_components():
    planner = SequencePlanner()
    components = [
        {'id': 'A', 'name': 'Cover', 'precedence': []},
        {'id': 'B', 'name': 'Screw', 'precedence': ['A']},
    ]
    result = planner.plan('test-model', components)
    assert len(result.steps) == 2
```

- [ ] **Step 3: 运行测试**

```bash
python -m pytest tests/sequence/test_planner.py -v
```

- [ ] **Step 4: Commit**

```bash
git add src/sequence/planner.py tests/sequence/
git commit -m feat: add Sequence Planner module
```

---

### Task 10: 人机协作模块 - LLM 9因素打分

**Files:**
- Create: `src/allocator/__init__.py`
- Create: `src/allocator/scorer.py`
- Create: `tests/allocator/test_scorer.py`

- [ ] **Step 1: 创建 src/allocator/__init__.py**

```python
```

- [ ] **Step 2: 创建 src/allocator/scorer.py**

```python
from src.utils.llm_client import LLMClient
from typing import Dict
import logging
import json

logger = logging.getLogger(__name__)


class HumanFactorScorer:
    FACTORS = ['visibility', 'space_limit', 'object_movement', 'ergonomic_impact', 'repetitiveness']

    SAFETY_FACTORS = ['high_voltage', 'chemical_risk', 'fire_explosion', 'personal_injury']

    def __init__(self, llm_client: LLMClient):
        self.llm = llm_client

    def score_human_factors(self, component_name: str, context: str = '') -> Dict[str, float]:
        prompt = f'''评估部件 {component_name} 的人力操作难度。

上下文信息：{context}

请对以下5个人力因素给出0-1的评分（0=非常容易，1=非常困难）：
1. 可视性(visibility)：操作时是否容易看到
2. 空间限制(space_limit)：操作空间是否受限
3. 物体移动要求(object_movement)：是否需要移动重物
4. 人因工程影响(ergonomic_impact)：是否对人体工程学有挑战
5. 重复性(repetitiveness)：是否需要重复操作

返回JSON格式：
{{"visibility": 0.0-1.0, "space_limit": 0.0-1.0, "object_movement": 0.0-1.0, "ergonomic_impact": 0.0-1.0, "repetitiveness": 0.0-1.0}}
'''

        try:
            result = self.llm.generate(prompt)
            scores = json.loads(result)
            return scores
        except Exception as e:
            logger.error(f"Human factor scoring failed: {e}")
            return {f: 0.5 for f in self.FACTORS}

    def score_safety_factors(self, component_name: str, context: str = '') -> Dict[str, float]:
        prompt = f'''评估部件 {component_name} 的安全风险。

上下文信息：{context}

请对以下4个安全因素给出0-1的评分（0=无风险，1=高风险）：
1. 高压风险(high_voltage)：是否涉及高压电
2. 化学试剂风险(chemical_risk)：是否有腐蚀性/有毒化学物质
3. 火灾爆炸风险(fire_explosion)：是否有起火/爆炸风险
4. 人身伤害风险(personal_injury)：是否可能造成人身伤害

返回JSON格式：
{{"high_voltage": 0.0-1.0, "chemical_risk": 0.0-1.0, "fire_explosion": 0.0-1.0, "personal_injury": 0.0-1.0}}
'''

        try:
            result = self.llm.generate(prompt)
            scores = json.loads(result)
            return scores
        except Exception as e:
            logger.error(f"Safety factor scoring failed: {e}")
            return {f: 0.5 for f in self.SAFETY_FACTORS}

    def score_all(self, component_name: str, context: str = '') -> Dict:
        human_scores = self.score_human_factors(component_name, context)
        safety_scores = self.score_safety_factors(component_name, context)

        return {
            'component': component_name,
            'human_scores': human_scores,
            'safety_scores': safety_scores
        }
```

- [ ] **Step 3: 创建 tests/allocator/test_scorer.py**

```python
import pytest
from src.allocator.scorer import HumanFactorScorer


def test_scorer_import():
    assert HumanFactorScorer is not None


class MockLLM:
    def generate(self, prompt):
        return '{"visibility": 0.3, "space_limit": 0.5, "object_movement": 0.2, "ergonomic_impact": 0.4, "repetitiveness": 0.1}'


def test_human_factor_scorer():
    scorer = HumanFactorScorer(MockLLM())
    result = scorer.score_human_factors('BatteryCover', 'test context')
    assert 'visibility' in result
    assert 0 <= result['visibility'] <= 1


def test_safety_factor_scorer():
    scorer = HumanFactorScorer(MockLLM())
    result = scorer.score_safety_factors('BatteryCover', 'test context')
    assert 'high_voltage' in result
    assert 0 <= result['high_voltage'] <= 1


def test_score_all():
    scorer = HumanFactorScorer(MockLLM())
    result = scorer.score_all('BatteryCover', 'test context')
    assert 'human_scores' in result
    assert 'safety_scores' in result
```

- [ ] **Step 4: 运行测试**

```bash
python -m pytest tests/allocator/test_scorer.py -v
```

- [ ] **Step 5: Commit**

```bash
git add src/allocator/scorer.py tests/allocator/
git commit -m feat: add LLM 9-factor scorer
```

---

### Task 11: 人机协作模块 - AS得分计算

**Files:**
- Create: `src/allocator/as_calculator.py`
- Create: `tests/allocator/test_as_calculator.py`

- [ ] **Step 1: 创建 src/allocator/as_calculator.py**

```python
from typing import Dict, List
import logging

logger = logging.getLogger(__name__)


class ASCalculator:
    DEFAULT_H_WEIGHTS = [0.2, 0.2, 0.2, 0.2, 0.2]

    DEFAULT_S_WEIGHTS = [0.25, 0.25, 0.25, 0.25]

    def __init__(self, h_weights: List[float] = None, s_weights: List[float] = None):
        self.h_weights = h_weights or self.DEFAULT_H_WEIGHTS
        self.s_weights = s_weights or self.DEFAULT_S_WEIGHTS

    def calculate_as(self, h_scores: Dict[str, float], s_scores: Dict[str, float]) -> float:
        h_keys = ['visibility', 'space_limit', 'object_movement', 'ergonomic_impact', 'repetitiveness']
        s_keys = ['high_voltage', 'chemical_risk', 'fire_explosion', 'personal_injury']

        h_vals = [h_scores.get(k, 0.5) for k in h_keys]
        s_vals = [s_scores.get(k, 0.5) for k in s_keys]

        h_weighted = sum(v * w for v, w in zip(h_vals, self.h_weights))
        s_weighted = sum(v * w for v, w in zip(s_vals, self.s_weights))

        as_score = 0.5 * (h_weighted + s_weighted)

        logger.info(f"Calculated AS score: {as_score:.3f}")
        return round(as_score, 3)

    def calculate_as_from_combined(self, combined_scores: Dict) -> float:
        h_scores = combined_scores.get('human_scores', {})
        s_scores = combined_scores.get('safety_scores', {})

        return self.calculate_as(h_scores, s_scores)

    def determine_assignee(self, as_score: float,
                         robot_cost: float = 100.0,
                         human_cost: float = 80.0) -> str:
        if as_score > 0.6:
            return 'robot'
        elif as_score < 0.4:
            return 'human'
        else:
            return 'robot' if robot_cost < human_cost else 'human'
```

- [ ] **Step 2: 创建 tests/allocator/test_as_calculator.py**

```python
import pytest
from src.allocator.as_calculator import ASCalculator


def test_as_calculator_import():
    assert ASCalculator is not None


def test_calculate_as():
    calculator = ASCalculator()
    h_scores = {'visibility': 0.3, 'space_limit': 0.5, 'object_movement': 0.2, 'ergonomic_impact': 0.4, 'repetitiveness': 0.1}
    s_scores = {'high_voltage': 0.6, 'chemical_risk': 0.2, 'fire_explosion': 0.1, 'personal_injury': 0.3}
    result = calculator.calculate_as(h_scores, s_scores)
    assert 0 <= result <= 1


def test_determine_assignee_robot():
    calculator = ASCalculator()
    assert calculator.determine_assignee(0.7) == 'robot'


def test_determine_assignee_human():
    calculator = ASCalculator()
    assert calculator.determine_assignee(0.3) == 'human'


def test_determine_assignee_cost_based():
    calculator = ASCalculator()
    assert calculator.determine_assignee(0.5, robot_cost=100, human_cost=80) == 'human'
```

- [ ] **Step 3: 运行测试**

```bash
python -m pytest tests/allocator/test_as_calculator.py -v
```

- [ ] **Step 4: Commit**

```bash
git add src/allocator/as_calculator.py tests/allocator/
git commit -m feat: add AS score calculator
```

---

### Task 12: 人机协作模块 - 分配主逻辑

**Files:**
- Create: `src/allocator/allocator.py`
- Create: `tests/allocator/test_allocator.py`

- [ ] **Step 1: 创建 src/allocator/allocator.py**

```python
from src.allocator.scorer import HumanFactorScorer
from src.allocator.as_calculator import ASCalculator
from src.utils.llm_client import LLMClient
from src.sequence.planner import DisassemblySequence
from pydantic import BaseModel
from typing import List, Dict, Any
import logging

logger = logging.getLogger(__name__)


class AllocationResult(BaseModel):
    battery_model: str
    allocations: List[Dict[str, Any]]
    human_count: int
    robot_count: int
    total_time_seconds: int


class HumanRobotAllocator:
    def __init__(self, llm_client: LLMClient):
        self.scorer = HumanFactorScorer(llm_client)
        self.calculator = ASCalculator()

    def allocate(self, sequence: DisassemblySequence) -> AllocationResult:
        battery_model = sequence.battery_model
        allocations = []
        human_count = 0
        robot_count = 0

        for step in sequence.steps:
            component_name = step.get('component_name', '')
            context = f"操作: {step.get('action', '拆卸')}, 工具: {step.get('tool_required', [])}"

            try:
                scores = self.scorer.score_all(component_name, context)
                as_score = self.calculator.calculate_as_from_combined(scores)
                assignee = self.calculator.determine_assignee(as_score)
            except Exception as e:
                logger.warning(f"Scoring failed for {component_name}: {e}")
                as_score = 0.5
                assignee = 'human'

            if assignee == 'human':
                human_count += 1
            else:
                robot_count += 1

            allocations.append({
                'step': step.get('step'),
                'component': component_name,
                'as_score': as_score,
                'assignee': assignee,
                'time_seconds': step.get('time_seconds', 0)
            })

        total_time = sum(a['time_seconds'] for a in allocations)

        result = AllocationResult(
            battery_model=battery_model,
            allocations=allocations,
            human_count=human_count,
            robot_count=robot_count,
            total_time_seconds=total_time
        )

        logger.info(f"Allocated {human_count} human, {robot_count} robot tasks")
        return result
```

- [ ] **Step 2: 创建 tests/allocator/test_allocator.py**

```python
import pytest
from src.allocator.allocator import HumanRobotAllocator, AllocationResult
from src.sequence.planner import DisassemblySequence


def test_allocator_import():
    assert HumanRobotAllocator is not None


def test_allocation_result_model():
    result = AllocationResult(
        battery_model='test',
        allocations=[{'component': 'A', 'assignee': 'human'}],
        human_count=1,
        robot_count=0,
        total_time_seconds=30
    )
    assert result.human_count == 1


def test_allocate_with_mock():
    class MockLLM:
        def generate(self, prompt):
            return '{"visibility": 0.3, "space_limit": 0.5, "object_movement": 0.2, "ergonomic_impact": 0.4, "repetitiveness": 0.1}'

    class MockScoreSafety:
        def generate(self, prompt):
            return '{"high_voltage": 0.6, "chemical_risk": 0.2, "fire_explosion": 0.1, "personal_injury": 0.3}'

    class MockLLM2:
        def __init__(self):
            self.call_count = 0

        def generate(self, prompt):
            self.call_count += 1
            if '人力' in prompt or '操作难度' in prompt:
                return '{"visibility": 0.3, "space_limit": 0.5, "object_movement": 0.2, "ergonomic_impact": 0.4, "repetitiveness": 0.1}'
            else:
                return '{"high_voltage": 0.6, "chemical_risk": 0.2, "fire_explosion": 0.1, "personal_injury": 0.3}'

    allocator = HumanRobotAllocator(MockLLM2())
    sequence = DisassemblySequence(
        battery_model='test',
        steps=[{'step': 1, 'component': 'A', 'component_name': 'Cover', 'time_seconds': 30, 'tool_required': []}],
        parallel_groups=[['A']],
        total_time_seconds=30,
        cycle_count=0
    )
    result = allocator.allocate(sequence)
    assert result.battery_model == 'test'
```

- [ ] **Step 3: 运行测试**

```bash
python -m pytest tests/allocator/test_allocator.py -v
```

- [ ] **Step 4: Commit**

```bash
git add src/allocator/allocator.py tests/allocator/
git commit -m feat: add Human-Robot Allocator module
```

---

### Task 13: 混合图输出模块 - Mermaid生成

**Files:**
- Create: `src/graph_output/__init__.py`
- Create: `src/graph_output/mermaid_gen.py`
- Create: `tests/graph_output/test_mermaid_gen.py`

- [ ] **Step 1: 创建 src/graph_output/__init__.py**

```python
```

- [ ] **Step 2: 创建 src/graph_output/mermaid_gen.py**

```python
from src.sequence.planner import DisassemblySequence
from typing import List, Dict
import logging

logger = logging.getLogger(__name__)


class MermaidGenerator:
    def __init__(self):
        self.node_counter = 0

    def generate(self, sequence: DisassemblySequence) -> str:
        lines = ['graph TD']

        node_map = {}

        for step in sequence.steps:
            comp_name = step.get('component', '')
            if not comp_name:
                continue

            node_id = f"N{self.node_counter}"
            node_map[comp_name] = node_id
            self.node_counter += 1

            assignee = step.get('assignee', 'human')
            time = step.get('time_seconds', 0)

            color = 'green' if assignee == 'human' else 'blue'

            label = f"{comp_name}\\n({assignee[:1].upper()}) {time}s"
            lines.append(f'    {node_id}[{{{label}}}]')

        for step in sequence.steps:
            comp_name = step.get('component', '')
            if not comp_name:
                continue

            from_id = node_map.get(comp_name)
            if not from_id:
                continue

            precedence = step.get('precedence', [])
            if precedence:
                for dep in precedence:
                    to_id = node_map.get(dep)
                    if to_id:
                        lines.append(f'    {from_id} --> {to_id}')

        logger.info(f"Generated Mermaid graph with {len(node_map)} nodes")
        return '\n'.join(lines)

    def generate_parallel(self, parallel_groups: List[List[str]]) -> str:
        lines = ['graph TD']

        for group in parallel_groups:
            if len(group) > 1:
                components = ', '.join(group)
                lines.append(f'    subgraph parallel_{len(lines)}')
                lines.append(f'        {components}')
                lines.append(f'    end')

        return '\n'.join(lines)
```

- [ ] **Step 3: 创建 tests/graph_output/test_mermaid_gen.py**

```python
import pytest
from src.graph_output.mermaid_gen import MermaidGenerator
from src.sequence.planner import DisassemblySequence


def test_mermaid_gen_import():
    assert MermaidGenerator is not None


def test_generate_simple():
    gen = MermaidGenerator()
    sequence = DisassemblySequence(
        battery_model='test',
        steps=[{'step': 1, 'component': 'A', 'component_name': 'Cover', 'time_seconds': 30, 'tool_required': []}],
        parallel_groups=[['A']],
        total_time_seconds=30,
        cycle_count=0
    )
    result = gen.generate(sequence)
    assert 'graph TD' in result


def test_generate_parallel():
    gen = MermaidGenerator()
    groups = [['A', 'B'], ['C']]
    result = gen.generate_parallel(groups)
    assert 'graph TD' in result
```

- [ ] **Step 4: 运行测试**

```bash
python -m pytest tests/graph_output/test_mermaid_gen.py -v
```

- [ ] **Step 5: Commit**

```bash
git add src/graph_output/mermaid_gen.py tests/graph_output/
git commit -m feat: add Mermaid generator
```

---

### Task 14: 混合图输出模块 - JSON构建

**Files:**
- Create: `src/graph_output/json_builder.py`
- Create: `tests/graph_output/test_json_builder.py`

- [ ] **Step 1: 创建 src/graph_output/json_builder.py**

```python
from src.sequence.planner import DisassemblySequence
from typing import List, Dict, Optional
import logging

logger = logging.getLogger(__name__)


class JSONBuilder:
    def build(self, sequence: DisassemblySequence, allocations: Optional[List[Dict]] = None) -> Dict:
        nodes = []
        edges = []

        for step in sequence.steps:
            comp = step.get('component', '')
            if not comp:
                continue

            allocation = None
            if allocations:
                for a in allocations:
                    if a.get('component') == comp:
                        allocation = a
                        break

            nodes.append({
                'id': comp,
                'label': step.get('component_name', comp),
                'assignee': allocation.get('assignee', 'human') if allocation else 'human',
                'time_seconds': step.get('time_seconds', 0),
                'safety_level': step.get('safety_level', 1),
                'tool_required': step.get('tool_required', [])
            })

        for step in sequence.steps:
            comp = step.get('component', '')
            if not comp:
                continue

            precedence = step.get('precedence', [])
            for dep in precedence:
                edges.append({
                    'from': dep,
                    'to': comp,
                    'type': 'PRECEDES'
                })

        parallel_groups = []
        for group in (sequence.parallel_groups or []):
            parallel_groups.append([str(c) for c in group])

        result = {
            'battery_model': sequence.battery_model,
            'total_time_seconds': sequence.total_time_seconds,
            'total_time_minutes': round(sequence.total_time_seconds / 60, 1),
            'cycle_count': sequence.cycle_count,
            'nodes': nodes,
            'edges': edges,
            'parallel_groups': parallel_groups,
            'human_count': sum(1 for n in nodes if n['assignee'] == 'human'),
            'robot_count': sum(1 for n in nodes if n['assignee'] == 'robot')
        }

        logger.info(f"Built JSON graph with {len(nodes)} nodes, {len(edges)} edges")
        return result
```

- [ ] **Step 2: 创建 tests/graph_output/test_json_builder.py**

```python
import pytest
from src.graph_output.json_builder import JSONBuilder
from src.sequence.planner import DisassemblySequence


def test_json_builder_import():
    assert JSONBuilder is not None


def test_build_simple():
    builder = JSONBuilder()
    sequence = DisassemblySequence(
        battery_model='test',
        steps=[{'step': 1, 'component': 'A', 'component_name': 'Cover', 'time_seconds': 30, 'safety_level': 1, 'tool_required': []}],
        parallel_groups=[['A']],
        total_time_seconds=30,
        cycle_count=0
    )
    result = builder.build(sequence)
    assert result['battery_model'] == 'test'
    assert len(result['nodes']) == 1


def test_build_with_allocations():
    builder = JSONBuilder()
    sequence = DisassemblySequence(
        battery_model='test',
        steps=[{'step': 1, 'component': 'A', 'component_name': 'Cover', 'time_seconds': 30, 'safety_level': 1, 'tool_required': []}],
        parallel_groups=[['A']],
        total_time_seconds=30,
        cycle_count=0
    )
    allocations = [{'component': 'A', 'assignee': 'robot'}]
    result = builder.build(sequence, allocations)
    assert result['nodes'][0]['assignee'] == 'robot'
```

- [ ] **Step 3: 运行测试**

```bash
python -m pytest tests/graph_output/test_json_builder.py -v
```

- [ ] **Step 4: Commit**

```bash
git add src/graph_output/json_builder.py tests/graph_output/
git commit -m feat: add JSON builder
```

---

### Task 15: 混合图输出模块 - 输出主逻辑

**Files:**
- Create: `src/graph_output/generator.py`
- Create: `tests/graph_output/test_generator.py`

- [ ] **Step 1: 创建 src/graph_output/generator.py**

```python
from src.graph_output.mermaid_gen import MermaidGenerator
from src.graph_output.json_builder import JSONBuilder
from src.sequence.planner import DisassemblySequence
from pydantic import BaseModel
from typing import Optional, List, Dict
import logging

logger = logging.getLogger(__name__)


class GraphOutput(BaseModel):
    mermaid: str
    json: Dict


class GraphOutputGenerator:
    def __init__(self):
        self.mermaid_gen = MermaidGenerator()
        self.json_builder = JSONBuilder()

    def generate(self, sequence: DisassemblySequence,
                allocations: Optional[List[Dict]] = None) -> GraphOutput:
        mermaid = self.mermaid_gen.generate(sequence)

        if sequence.parallel_groups:
            parallel_mermaid = self.mermaid_gen.generate_parallel(sequence.parallel_groups)
            mermaid += '\n\n' + parallel_mermaid

        json_output = self.json_builder.build(sequence, allocations)

        return GraphOutput(
            mermaid=mermaid,
            json=json_output
        )
```

- [ ] **Step 2: 创建 tests/graph_output/test_generator.py**

```python
import pytest
from src.graph_output.generator import GraphOutputGenerator, GraphOutput
from src.sequence.planner import DisassemblySequence


def test_generator_import():
    assert GraphOutputGenerator is not None


def test_graph_output_model():
    output = GraphOutput(
        mermaid="graph TD\\n    A[...]",
        json={'nodes': [], 'edges': []}
    )
    assert output.mermaid.startswith('graph TD')


def test_generate():
    gen = GraphOutputGenerator()
    sequence = DisassemblySequence(
        battery_model='test',
        steps=[{'step': 1, 'component': 'A', 'component_name': 'Cover', 'time_seconds': 30, 'safety_level': 1, 'tool_required': []}],
        parallel_groups=[['A']],
        total_time_seconds=30,
        cycle_count=0
    )
    result = gen.generate(sequence)
    assert 'graph TD' in result.mermaid
    assert result.json['battery_model'] == 'test'
```

- [ ] **Step 3: 运行测试**

```bash
python -m pytest tests/graph_output/test_generator.py -v
```

- [ ] **Step 4: Commit**

```bash
git add src/graph_output/generator.py tests/graph_output/
git commit -m feat: add Graph Output Generator
```

---

### Task 16: API整合

**Files:**
- Modify: `src/api/routes.py`

- [ ] **Step 1: 更新routes.py添加新端点**

```python
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import List, Dict, Any, Optional

router = APIRouter()


class SequenceRequest(BaseModel):
    battery_model: str
    components: List[Dict[str, Any]] = []


class AllocateRequest(BaseModel):
    battery_model: str
    sequence: Dict[str, Any]


class GraphRequest(BaseModel):
    battery_model: str
    sequence: Dict[str, Any]
    allocations: List[Dict[str, Any]] = []


@router.post('/api/v1/disassembly/sequence')
async def create_sequence(request: SequenceRequest):
    from src.sequence.planner import SequencePlanner

    planner = SequencePlanner()
    result = planner.plan(request.battery_model, request.components)

    return {'code': 0, 'data': result.model_dump()}


@router.post('/api/v1/disassembly/allocate')
async def allocate_tasks(request: AllocateRequest):
    from src.sequence.planner import DisassemblySequence
    from src.allocator.allocator import HumanRobotAllocator
    from src.utils.llm_client import LLMClient
    from src.config import settings

    sequence = DisassemblySequence(**request.sequence)
    llm = LLMClient(settings.openai_api_key, settings.openai_base_url)
    allocator = HumanRobotAllocator(llm)
    result = allocator.allocate(sequence)

    return {'code': 0, 'data': result.model_dump()}


@router.post('/api/v1/disassembly/graph')
async def generate_graph(request: GraphRequest):
    from src.sequence.planner import DisassemblySequence
    from src.graph_output.generator import GraphOutputGenerator

    sequence = DisassemblySequence(**request.sequence)
    gen = GraphOutputGenerator()
    result = gen.generate(sequence, request.allocations)

    return {'code': 0, 'data': result.model_dump()}
```

- [ ] **Step 2: Commit**

```bash
git add src/api/routes.py
git commit -m feat: add Phase 2 API endpoints
```

---

## 验收标准

- [ ] Task 1: 路径分类器创建完成
- [ ] Task 2: PDF解析器创建完成
- [ ] Task 3: 实体提取器创建完成
- [ ] Task 4: 数据导入主逻辑创建完成
- [ ] Task 5: 管理界面API创建完成
- [ ] Task 6: Tarjan环路检测创建完成
- [ ] Task 7: 拓扑排序创建完成
- [ ] Task 8: MTM时间估算创建完成
- [ ] Task 9: 序列规划主逻辑创建完成
- [ ] Task 10: LLM 9因素打分创建完成
- [ ] Task 11: AS得分计算创建完成
- [ ] Task 12: 人机协作分配创建完成
- [ ] Task 13: Mermaid生成创建完成
- [ ] Task 14: JSON构建创建完成
- [ ] Task 15: 混合图输出创建完成
- [ ] Task 16: API整合完成

---

## 下一步

**选择执行方式：**

1. **Subagent-Driven (推荐)** - 每个任务由独立子代理执行
2. **Inline Execution** - 在当前会话中执行任务

**你选择哪种方式？**