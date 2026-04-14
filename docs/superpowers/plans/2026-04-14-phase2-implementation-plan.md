# 阶段2实现计划

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 实现拆卸序列规划、人机协作分配、混合图输出、数据导入功能

**Architecture:** 在阶段1 GraphRAG 基础上，新增4个核心模块：数据导入、序列规划、人机分配、图输出

**Tech Stack:** Python 3.11+, PyMuPDF, Neo4j, LLM, FastAPI

---

## 文件结构

```
src/
├── importer/                    # 数据导入模块
│   ├── __init__.py
│   ├── pdf_parser.py           # PyMuPDF解析
│   ├── path_classifier.py      # 路径分类
│   ├── entity_extractor.py     # LLM提取L2/L3
│   └── importer.py             # 导入主逻辑
│
├── sequence/                    # 拆卸序列模块
│   ├── __init__.py
│   ├── planner.py              # 序列规划主逻辑
│   ├── cycle_detector.py       # Tarjan环路检测
│   ├── topological_sort.py      # 拓扑排序
│   └── time_estimator.py       # MTM时间估算
│
├── allocator/                   # 人机协作模块
│   ├── __init__.py
│   ├── scorer.py               # LLM 9因素打分
│   ├── as_calculator.py        # AS得分计算
│   └── allocator.py            # 分配主逻辑
│
├── graph_output/               # 混合图输出模块
│   ├── __init__.py
│   ├── mermaid_gen.py          # Mermaid生成
│   ├── json_builder.py         # JSON构建
│   └── generator.py             # 输出主逻辑

tests/
├── importer/
│   └── test_importer.py
├── sequence/
│   ├── test_cycle_detector.py
│   ├── test_topological_sort.py
│   └── test_time_estimator.py
├── allocator/
│   └── test_allocator.py
└── graph_output/
    └── test_generator.py
```

---

### Task 1: 数据导入模块 - 基础设置

**Files:**
- Create: `src/importer/__init__.py`
- Create: `src/sequence/__init__.py`
- Create: `src/allocator/__init__.py`
- Create: `src/graph_output/__init__.py`
- Modify: `requirements.txt`
- Create: `tests/importer/__init__.py`
- Create: `tests/sequence/__init__.py`
- Create: `tests/allocator/__init__.py`
- Create: `tests/graph_output/__init__.py`

- [ ] **Step 1: 创建目录和__init__.py文件**

```bash
mkdir -p src/importer src/sequence src/allocator src/graph_output
mkdir -p tests/importer tests/sequence tests/allocator tests/graph_output
touch src/importer/__init__.py src/sequence/__init__.py src/allocator/__init__.py src/graph_output/__init__.py
touch tests/importer/__init__.py tests/sequence/__init__.py tests/allocator/__init__.py tests/graph_output/__init__.py
```

- [ ] **Step 2: 更新 requirements.txt 添加 PyMuPDF**

```txt
pymupdf==1.24.0
```

- [ ] **Step 3: 运行测试验证**

```bash
python -c "import pymupdf; print('PyMuPDF OK')"
```

- [ ] **Step 4: Commit**

```bash
git add requirements.txt src/importer/ src/sequence/ src/allocator/ src/graph_output/ tests/importer/ tests/sequence/ tests/allocator/ tests/graph_output/
git commit -m "feat(phase2): add module directories"
```

---

### Task 2: 数据导入 - PDF解析器

**Files:**
- Create: `src/importer/pdf_parser.py`
- Create: `tests/importer/test_pdf_parser.py`

- [ ] **Step 1: 创建 src/importer/pdf_parser.py**

```python
from pymupdf import Document, Pixmap
from typing import Optional
import logging

logger = logging.getLogger(__name__)


class PDFParser:
    def __init__(self):
        self.supported_extensions = ['.pdf']
    
    def extract_text(self, file_path: str) -> str:
        text_parts = []
        try:
            doc = Document(file_path)
            for page_num in range(len(doc)):
                page = doc[page_num]
                text = page.get_text()
                if text.strip():
                    text_parts.append(text)
            logger.info(f'Extracted {len(text_parts)} pages from {file_path}')
            return '\n\n'.join(text_parts)
        except Exception as e:
            logger.error(f'Failed to extract text from {file_path}: {e}')
            raise
    
    def extract_metadata(self, file_path: str) -> dict:
        try:
            doc = Document(file_path)
            metadata = doc.metadata
            return {
                'title': metadata.get('title', ''),
                'author': metadata.get('author', ''),
                'subject': metadata.get('subject', ''),
                'creator': metadata.get('creator', ''),
                'page_count': len(doc)
            }
        except Exception as e:
            logger.error(f'Failed to extract metadata from {file_path}: {e}')
            return {'page_count': 0}
    
    def extract_pages(self, file_path: str, start: int = 0, end: Optional[int] = None) -> list[str]:
        pages = []
        try:
            doc = Document(file_path)
            end = end or len(doc)
            for page_num in range(start, min(end, len(doc))):
                page = doc[page_num]
                text = page.get_text()
                if text.strip():
                    pages.append(text)
            return pages
        except Exception as e:
            logger.error(f'Failed to extract pages from {file_path}: {e}')
            return []
```

- [ ] **Step 2: 创建 tests/importer/test_pdf_parser.py**

```python
import pytest
from src.importer.pdf_parser import PDFParser


def test_pdf_parser_import():
    assert PDFParser is not None


def test_parser_initialization():
    parser = PDFParser()
    assert parser.supported_extensions == ['.pdf']
```

- [ ] **Step 3: 运行测试**

```bash
python -m pytest tests/importer/test_pdf_parser.py -v
```

- [ ] **Step 4: Commit**

```bash
git add src/importer/pdf_parser.py tests/importer/test_pdf_parser.py
git commit -m "feat(importer): add PDF parser using PyMuPDF"
```

---

### Task 3: 数据导入 - 路径分类器

**Files:**
- Create: `src/importer/path_classifier.py`
- Create: `tests/importer/test_path_classifier.py`

- [ ] **Step 1: 创建 src/importer/path_classifier.py**

```python
from typing import Literal
from dataclasses import dataclass


@dataclass
class SourceClassification:
    source: Literal['patent', 'standard', 'paper']
    paper_category: str = ''
    target_layers: list[str] = None
    
    def __post_init__(self):
        if self.target_layers is None:
            self.target_layers = ['L2', 'L3']


class PathClassifier:
    PATTERN_PATENT = ['专利', 'CN', 'WO', 'US']
    PATTERN_STANDARD = ['国标', 'GBT', 'GB_T']
    PATTERN_PAPER_DISASSEMBLY = ['A_', '拆卸']
    PATTERN_PAPER_REUSE = ['B_', '梯次']
    PATTERN_PAPER_DFD = ['C_', '可拆卸']
    PATTERN_PAPER_HRC = ['D_', '人机']
    PATTERN_PAPER_GENERAL = ['E_', '综述']
    
    def classify(self, file_path: str) -> SourceClassification:
        if self._is_patent(file_path):
            return SourceClassification(source='patent')
        elif self._is_standard(file_path):
            return SourceClassification(source='standard')
        elif self._is_paper(file_path):
            return SourceClassification(source='paper', paper_category=self._get_paper_category(file_path))
        else:
            return SourceClassification(source='unknown')
    
    def _is_patent(self, path: str) -> bool:
        return any(p in path for p in self.PATTERN_PATENT)
    
    def _is_standard(self, path: str) -> bool:
        return any(p in path for p in self.PATTERN_STANDARD)
    
    def _is_paper(self, path: str) -> bool:
        return '学术论文' in path or 'paper' in path.lower()
    
    def _get_paper_category(self, path: str) -> str:
        if any(p in path for p in self.PATTERN_PAPER_DISASSEMBLY):
            return 'A_disassembly'
        elif any(p in path for p in self.PATTERN_PAPER_REUSE):
            return 'B_reuse'
        elif any(p in path for p in self.PATTERN_PAPER_DFD):
            return 'C_dfd'
        elif any(p in path for p in self.PATTERN_PAPER_HRC):
            return 'D_hrc'
        elif any(p in path for p in self.PATTERN_PAPER_GENERAL):
            return 'E_general'
        return 'unknown'
```

- [ ] **Step 2: 创建 tests/importer/test_path_classifier.py**

```python
import pytest
from src.importer.path_classifier import PathClassifier, SourceClassification


def test_path_classifier_import():
    assert PathClassifier is not None


def test_classify_patent():
    classifier = PathClassifier()
    result = classifier.classify('专利/CN202511156458.pdf')
    assert result.source == 'patent'


def test_classify_standard():
    classifier = PathClassifier()
    result = classifier.classify('国标/GBT+34015-2017.pdf')
    assert result.source == 'standard'


def test_classify_paper():
    classifier = PathClassifier()
    result = classifier.classify('学术论文/A_动力电池拆卸数据/xxx.pdf')
    assert result.source == 'paper'
    assert result.paper_category == 'A_disassembly'
```

- [ ] **Step 3: 运行测试**

```bash
python -m pytest tests/importer/test_path_classifier.py -v
```

- [ ] **Step 4: Commit**

```bash
git add src/importer/path_classifier.py tests/importer/test_path_classifier.py
git commit -m "feat(importer): add path classifier for source detection"
```

---

### Task 4: 数据导入 - LLM实体提取器

**Files:**
- Create: `src/importer/entity_extractor.py`
- Create: `tests/importer/test_entity_extractor.py`

- [ ] **Step 1: 创建 src/importer/entity_extractor.py**

```python
from src.utils.llm_client import LLMClient
from src.kg.models import Document, Term
from typing import Optional
import logging

logger = logging.getLogger(__name__)


class EntityExtractor:
    DOCUMENT_PROMPT = '''从以下文档内容中提取信息，生成结构化的文档对象。

返回JSON格式：
{
    "doc_id": "文档ID",
    "title": "文档标题",
    "content": "文档主要内容摘要（不超过500字）"
}

文档内容：
{content}
'''

    TERM_PROMPT = '''从以下文本中提取专业术语及其定义。

返回JSON数组格式：
[
    {"term_id": "术语ID", "definition": "术语定义", "units": "单位（如适用）"}
]

文本内容：
{content}
'''

    def __init__(self, llm_client: LLMClient):
        self.llm = llm_client
    
    def extract_document(self, content: str, doc_id: str, source: str) -> Document:
        prompt = self.DOCUMENT_PROMPT.format(content=content[:5000])
        try:
            result = self.llm.generate_json(prompt, ['doc_id', 'title', 'content'])
            return Document(
                doc_id=result.get('doc_id', doc_id),
                title=result.get('title', ''),
                source=source,
                source_type=source,
                content=result.get('content', ''),
                file_path=''
            )
        except Exception as e:
            logger.error(f'Failed to extract document: {e}')
            return Document(doc_id=doc_id, title='', source=source, source_type=source, content='')
    
    def extract_terms(self, content: str) -> list[Term]:
        prompt = self.TERM_PROMPT.format(content=content[:3000])
        try:
            result = self.llm.generate_json(prompt, [])
            terms_data = result if isinstance(result, list) else result.get('terms', [])
            return [
                Term(
                    term_id=t.get('term_id', f'term_{i}'),
                    definition=t.get('definition', ''),
                    units=t.get('units')
                )
                for i, t in enumerate(terms_data[:20])
            ]
        except Exception as e:
            logger.error(f'Failed to extract terms: {e}')
            return []
```

- [ ] **Step 2: 创建 tests/importer/test_entity_extractor.py**

```python
import pytest
from src.importer.entity_extractor import EntityExtractor


def test_entity_extractor_import():
    assert EntityExtractor is not None


def test_extractor_initialization():
    class MockLLM:
        def generate_json(self, prompt, schema):
            return {'doc_id': 'test', 'title': 'Test', 'content': 'Test content'}
    
    extractor = EntityExtractor(MockLLM())
    assert extractor.llm is not None
```

- [ ] **Step 3: 运行测试**

```bash
python -m pytest tests/importer/test_entity_extractor.py -v
```

- [ ] **Step 4: Commit**

```bash
git add src/importer/entity_extractor.py tests/importer/test_entity_extractor.py
git commit -m "feat(importer): add LLM entity extractor for L2/L3"
```

---

### Task 5: 数据导入 - 导入主逻辑

**Files:**
- Create: `src/importer/importer.py`
- Create: `tests/importer/test_importer.py`
- Modify: `src/kg/models.py` (添加新字段)

- [ ] **Step 1: 创建 src/importer/importer.py**

```python
from src.importer.pdf_parser import PDFParser
from src.importer.path_classifier import PathClassifier, SourceClassification
from src.importer.entity_extractor import EntityExtractor
from src.kg.client import Neo4jClient
from src.kg.models import Document, Term, Component
from typing import Optional
import logging

logger = logging.getLogger(__name__)


class DataImporter:
    def __init__(self, neo4j_client: Neo4jClient, llm_client):
        self.parser = PDFParser()
        self.classifier = PathClassifier()
        self.extractor = EntityExtractor(llm_client)
        self.neo4j = neo4j_client
    
    def import_pdf(self, file_path: str) -> dict:
        classification = self.classifier.classify(file_path)
        logger.info(f'Importing {file_path} as {classification.source}')
        
        text = self.parser.extract_text(file_path)
        metadata = self.parser.extract_metadata(file_path)
        
        doc = self.extractor.extract_document(text, file_path, classification.source)
        doc.file_path = file_path
        
        terms = self.extractor.extract_terms(text)
        
        self._save_to_kg(doc, terms)
        
        return {
            'status': 'success',
            'doc_id': doc.doc_id,
            'terms_count': len(terms),
            'source': classification.source
        }
    
    def promote_to_component(self, doc_id: str, component_data: dict) -> Component:
        component = Component(
            id=doc_id,
            name=component_data.get('name', ''),
            battery_model=component_data.get('battery_model', ''),
            tool_required=component_data.get('tool_required', []),
            safety_level=component_data.get('safety_level', 1),
            preconditions=component_data.get('preconditions', []),
            estimated_time=component_data.get('estimated_time', 0),
            source_type='manual',
            metadata=component_data.get('metadata', {})
        )
        
        cypher = '''
        MERGE (c:Component {id: $id})
        SET c.name = $name,
            c.battery_model = $battery_model,
            c.tool_required = $tool_required,
            c.safety_level = $safety_level,
            c.preconditions = $preconditions,
            c.estimated_time = $estimated_time,
            c.source_type = 'manual'
        '''
        self.neo4j.execute_query(cypher, {
            'id': component.id,
            'name': component.name,
            'battery_model': component.battery_model,
            'tool_required': component.tool_required,
            'safety_level': component.safety_level,
            'preconditions': component.preconditions,
            'estimated_time': component.estimated_time
        })
        
        return component
    
    def _save_to_kg(self, doc: Document, terms: list[Term]):
        doc_cypher = '''
        MERGE (d:Document {doc_id: $doc_id})
        SET d.title = $title,
            d.source = $source,
            d.source_type = $source_type,
            d.content = $content,
            d.file_path = $file_path
        '''
        self.neo4j.execute_query(doc_cypher, {
            'doc_id': doc.doc_id,
            'title': doc.title,
            'source': doc.source,
            'source_type': doc.source_type,
            'content': doc.content,
            'file_path': doc.file_path
        })
        
        for term in terms:
            term_cypher = '''
            MERGE (t:Term {term_id: $term_id})
            SET t.definition = $definition,
                t.units = $units
            '''
            self.neo4j.execute_query(term_cypher, {
                'term_id': term.term_id,
                'definition': term.definition,
                'units': term.units or ''
            })
```

- [ ] **Step 2: 创建 tests/importer/test_importer.py**

```python
import pytest
from src.importer.importer import DataImporter


def test_importer_import():
    assert DataImporter is not None
```

- [ ] **Step 3: 运行测试**

```bash
python -m pytest tests/importer/test_importer.py -v
```

- [ ] **Step 4: Commit**

```bash
git add src/importer/importer.py tests/importer/test_importer.py
git commit -m "feat(importer): add main importer logic"
```

---

### Task 6: 拆卸序列 - Tarjan环路检测

**Files:**
- Create: `src/sequence/cycle_detector.py`
- Create: `tests/sequence/test_cycle_detector.py`

- [ ] **Step 1: 创建 src/sequence/cycle_detector.py**

```python
from typing import Optional
from dataclasses import dataclass, field


@dataclass
class CycleNode:
    id: str
    neighbors: list[str] = field(default_factory=list)
    index: Optional[int] = None
    lowlink: Optional[int] = None
    on_stack: bool = False


class TarjanCycleDetector:
    def __init__(self):
        self.index = 0
        self.stack: list[CycleNode] = []
        self.sccs: list[list[str]] = []
        self.nodes: dict[str, CycleNode] = {}
    
    def detect_cycles(self, edges: list[tuple[str, str]]) -> list[list[str]]:
        self._reset()
        
        for source, target in edges:
            if source not in self.nodes:
                self.nodes[source] = CycleNode(id=source)
            if target not in self.nodes:
                self.nodes[target] = CycleNode(id=target)
            self.nodes[source].neighbors.append(target)
        
        for node in self.nodes.values():
            if node.index is None:
                self._strong_connect(node)
        
        cycles = [scc for scc in self.sccs if len(scc) > 1]
        return cycles
    
    def _reset(self):
        self.index = 0
        self.stack = []
        self.sccs = []
        self.nodes = {}
    
    def _strong_connect(self, v: CycleNode):
        v.index = self.index
        v.lowlink = self.index
        self.index += 1
        self.stack.append(v)
        v.on_stack = True
        
        for w_id in v.neighbors:
            w = self.nodes[w_id]
            if w.index is None:
                self._strong_connect(w)
                v.lowlink = min(v.lowlink, w.lowlink)
            elif w.on_stack:
                v.lowlink = min(v.lowlink, w.index)
        
        if v.lowlink == v.index:
            scc = []
            while True:
                w = self.stack.pop()
                w.on_stack = False
                scc.append(w.id)
                if w.id == v.id:
                    break
            self.sccs.append(scc)
    
    def has_cycles(self, edges: list[tuple[str, str]]) -> bool:
        cycles = self.detect_cycles(edges)
        return len(cycles) > 0
```

- [ ] **Step 2: 创建 tests/sequence/test_cycle_detector.py**

```python
import pytest
from src.sequence.cycle_detector import TarjanCycleDetector


def test_tarjan_import():
    assert TarjanCycleDetector is not None


def test_no_cycle():
    detector = TarjanCycleDetector()
    edges = [('A', 'B'), ('B', 'C'), ('C', 'D')]
    assert not detector.has_cycles(edges)
    assert detector.detect_cycles(edges) == []


def test_with_cycle():
    detector = TarjanCycleDetector()
    edges = [('A', 'B'), ('B', 'C'), ('C', 'A')]
    assert detector.has_cycles(edges)
    cycles = detector.detect_cycles(edges)
    assert len(cycles) == 1
    assert set(cycles[0]) == {'A', 'B', 'C'}


def test_self_loop():
    detector = TarjanCycleDetector()
    edges = [('A', 'A'), ('B', 'C')]
    cycles = detector.detect_cycles(edges)
    assert len(cycles) == 1
    assert 'A' in cycles[0]
```

- [ ] **Step 3: 运行测试**

```bash
python -m pytest tests/sequence/test_cycle_detector.py -v
```

- [ ] **Step 4: Commit**

```bash
git add src/sequence/cycle_detector.py tests/sequence/test_cycle_detector.py
git commit -m "feat(sequence): add Tarjan cycle detector"
```

---

### Task 7: 拆卸序列 - 拓扑排序

**Files:**
- Create: `src/sequence/topological_sort.py`
- Create: `tests/sequence/test_topological_sort.py`

- [ ] **Step 1: 创建 src/sequence/topological_sort.py**

```python
from typing import Optional
from collections import deque


class TopologicalSorter:
    def __init__(self):
        self.graph: dict[str, list[str]] = {}
        self.in_degree: dict[str, int] = {}
    
    def sort(self, edges: list[tuple[str, str]], nodes: list[str]) -> Optional[list[str]]:
        self._build_graph(edges, nodes)
        
        queue = deque([n for n in nodes if self.in_degree.get(n, 0) == 0])
        result = []
        
        while queue:
            node = queue.popleft()
            result.append(node)
            
            for neighbor in self.graph.get(node, []):
                self.in_degree[neighbor] -= 1
                if self.in_degree[neighbor] == 0:
                    queue.append(neighbor)
        
        if len(result) != len(nodes):
            return None
        
        return result
    
    def find_parallel_groups(self, edges: list[tuple[str, str]], nodes: list[str], sorted_order: list[str]) -> list[list[str]]:
        self._build_graph(edges, nodes)
        
        level = {}
        for node in nodes:
            level[node] = 0
        
        for node in sorted_order:
            for neighbor in self.graph.get(node, []):
                level[neighbor] = max(level[neighbor], level[node] + 1)
        
        groups = {}
        for node, lvl in level.items():
            if lvl not in groups:
                groups[lvl] = []
            groups[lvl].append(node)
        
        return [groups[l] for l in sorted(groups.keys())]
    
    def _build_graph(self, edges: list[tuple[str, str]], nodes: list[str]):
        self.graph = {n: [] for n in nodes}
        self.in_degree = {n: 0 for n in nodes}
        
        for source, target in edges:
            if source in self.graph and target in self.graph:
                self.graph[source].append(target)
                self.in_degree[target] += 1
```

- [ ] **Step 2: 创建 tests/sequence/test_topological_sort.py**

```python
import pytest
from src.sequence.topological_sort import TopologicalSorter


def test_topological_sorter_import():
    assert TopologicalSorter is not None


def test_simple_sort():
    sorter = TopologicalSorter()
    nodes = ['A', 'B', 'C']
    edges = [('A', 'B'), ('B', 'C')]
    result = sorter.sort(edges, nodes)
    assert result is not None
    assert result.index('A') < result.index('B')
    assert result.index('B') < result.index('C')


def test_parallel_groups():
    sorter = TopologicalSorter()
    nodes = ['A', 'B', 'C', 'D']
    edges = [('A', 'C'), ('B', 'C'), ('C', 'D')]
    sorted_order = sorter.sort(edges, nodes)
    groups = sorter.find_parallel_groups(edges, nodes, sorted_order)
    assert len(groups) == 3
    assert set(groups[0]) == {'A', 'B'}
    assert 'C' in groups[1]
    assert 'D' in groups[2]


def test_cycle_handling():
    sorter = TopologicalSorter()
    nodes = ['A', 'B', 'C']
    edges = [('A', 'B'), ('B', 'C'), ('C', 'A')]
    result = sorter.sort(edges, nodes)
    assert result is None
```

- [ ] **Step 3: 运行测试**

```bash
python -m pytest tests/sequence/test_topological_sort.py -v
```

- [ ] **Step 4: Commit**

```bash
git add src/sequence/topological_sort.py tests/sequence/test_topological_sort.py
git commit -m "feat(sequence): add topological sorter"
```

---

### Task 8: 拆卸序列 - MTM时间估算

**Files:**
- Create: `src/sequence/time_estimator.py`
- Create: `tests/sequence/test_time_estimator.py`

- [ ] **Step 1: 创建 src/sequence/time_estimator.py**

```python
from src.kg.models import Component
from typing import Optional


class MTMT imeEstimator:
    """
    MTM (Methods-Time Measurement) based time estimator
    Based on technical document formulas:
    - Ts: operation time score (0-3)
    - Tt: tool switch time score (0-3)
    - Tp: position move time score (0-3)
    
    T = Ts + Tt + Tp (total score)
    T_seconds = (T / 5) * 85 (score to seconds conversion)
    """
    
    def __init__(self):
        self.score_to_seconds_factor = 85 / 5
    
    def calculate_time(self, component: Component) -> int:
        ts = getattr(component, 'avg_operation_time', 1)
        tt = getattr(component, 'tool_switch_time', 0)
        tp = getattr(component, 'position_move_time', 0)
        
        ts = max(0, min(3, ts))
        tt = max(0, min(3, tt))
        tp = max(0, min(3, tp))
        
        total_score = ts + tt + tp
        seconds = int((total_score / 5) * self.score_to_seconds_factor)
        
        return max(5, seconds)
    
    def calculate_sequence_time(self, components: list[Component], 
                                 parallel_groups: list[list[str]]) -> int:
        total_time = 0
        for group in parallel_groups:
            group_time = max(
                self.calculate_time(c) 
                for c in components 
                if c.id in group
            )
            total_time += group_time
        return total_time
    
    def estimate_from_dict(self, data: dict) -> int:
        ts = max(0, min(3, data.get('avg_operation_time', 1)))
        tt = max(0, min(3, data.get('tool_switch_time', 0)))
        tp = max(0, min(3, data.get('position_move_time', 0)))
        
        total_score = ts + tt + tp
        return int((total_score / 5) * self.score_to_seconds_factor)
```

- [ ] **Step 2: 创建 tests/sequence/test_time_estimator.py**

```python
import pytest
from src.sequence.time_estimator import MTMT imeEstimator


def test_time_estimator_import():
    assert MTMT imeEstimator is not None


def test_minimal_time():
    estimator = MTMT imeEstimator()
    assert estimator.estimate_from_dict({'avg_operation_time': 0, 'tool_switch_time': 0, 'position_move_time': 0}) == 5


def test_maximal_time():
    estimator = MTMT imeEstimator()
    result = estimator.estimate_from_dict({'avg_operation_time': 3, 'tool_switch_time': 3, 'position_move_time': 3})
    assert result >= 51


def test_score_clamping():
    estimator = MTMT imeEstimator()
    result = estimator.estimate_from_dict({'avg_operation_time': 10, 'tool_switch_time': -5, 'position_move_time': 2})
    expected_ts = 3
    expected_tt = 0
    expected_tp = 2
    assert result == int(((expected_ts + expected_tt + expected_tp) / 5) * 17)
```

- [ ] **Step 3: 运行测试**

```bash
python -m pytest tests/sequence/test_time_estimator.py -v
```

- [ ] **Step 4: Commit**

```bash
git add src/sequence/time_estimator.py tests/sequence/test_time_estimator.py
git commit -m "feat(sequence): add MTM time estimator"
```

---

### Task 9: 拆卸序列 - 规划主逻辑

**Files:**
- Create: `src/sequence/planner.py`
- Create: `tests/sequence/test_planner.py`

- [ ] **Step 1: 创建 src/sequence/planner.py**

```python
from src.sequence.cycle_detector import TarjanCycleDetector
from src.sequence.topological_sort import TopologicalSorter
from src.sequence.time_estimator import MTMT imeEstimator
from src.kg.models import Component
from dataclasses import dataclass
from typing import Optional
import logging

logger = logging.getLogger(__name__)


@dataclass
class DisassemblyStep:
    id: str
    name: str
    time_estimate: int
    assignee: Optional[str] = None
    parallel_with: list[str] = None
    
    def __post_init__(self):
        if self.parallel_with is None:
            self.parallel_with = []


@dataclass
class DisassemblySequence:
    steps: list[DisassemblyStep]
    total_time: int
    parallel_groups: list[list[str]]
    has_cycles: bool = False
    cycle_nodes: list[list[str]] = None
    
    def __post_init__(self):
        if self.cycle_nodes is None:
            self.cycle_nodes = []


class SequencePlanner:
    def __init__(self):
        self.cycle_detector = TarjanCycleDetector()
        self.topological_sorter = TopologicalSorter()
        self.time_estimator = MTMT imeEstimator()
    
    def plan(self, components: list[Component]) -> DisassemblySequence:
        nodes = [c.id for c in components]
        edges = []
        for c in components:
            for precedence in getattr(c, 'precedence', []):
                edges.append((precedence, c.id))
        
        cycles = self.cycle_detector.detect_cycles(edges)
        has_cycles = len(cycles) > 0
        
        sorted_order = self.topological_sorter.sort(edges, nodes)
        if sorted_order is None:
            logger.warning('Cycle detected, partial sort returned')
            sorted_order = nodes
        
        parallel_groups = self.topological_sorter.find_parallel_groups(edges, nodes, sorted_order)
        
        steps = []
        component_map = {c.id: c for c in components}
        for c in components:
            if c.id in sorted_order:
                time_est = self.time_estimator.calculate_time(c)
                step = DisassemblyStep(
                    id=c.id,
                    name=c.name,
                    time_estimate=time_est
                )
                steps.append(step)
        
        total_time = self.time_estimator.calculate_sequence_time(components, parallel_groups)
        
        return DisassemblySequence(
            steps=steps,
            total_time=total_time,
            parallel_groups=parallel_groups,
            has_cycles=has_cycles,
            cycle_nodes=cycles
        )
```

- [ ] **Step 2: 创建 tests/sequence/test_planner.py**

```python
import pytest
from src.sequence.planner import SequencePlanner, DisassemblySequence
from src.kg.models import Component


def test_planner_import():
    assert SequencePlanner is not None


def test_simple_sequence():
    planner = SequencePlanner()
    components = [
        Component(id='A', name='Cover', battery_model='X1', preconditions=[]),
        Component(id='B', name='Screws', battery_model='X1', preconditions=['A']),
        Component(id='C', name='Pack', battery_model='X1', preconditions=['B'])
    ]
    result = planner.plan(components)
    assert isinstance(result, DisassemblySequence)
    assert len(result.steps) == 3
    assert not result.has_cycles


def test_parallel_sequence():
    planner = SequencePlanner()
    components = [
        Component(id='A', name='Cover', battery_model='X1', preconditions=[]),
        Component(id='B', name='Screws', battery_model='X1', preconditions=[]),
        Component(id='C', name='Pack', battery_model='X1', preconditions=['A', 'B'])
    ]
    result = planner.plan(components)
    assert len(result.parallel_groups) >= 2
```

- [ ] **Step 3: 运行测试**

```bash
python -m pytest tests/sequence/test_planner.py -v
```

- [ ] **Step 4: Commit**

```bash
git add src/sequence/planner.py tests/sequence/test_planner.py
git commit -m "feat(sequence): add sequence planner orchestrator"
```

---

### Task 10: 人机协作 - LLM打分器

**Files:**
- Create: `src/allocator/scorer.py`
- Create: `tests/allocator/test_scorer.py`

- [ ] **Step 1: 创建 src/allocator/scorer.py**

```python
from src.utils.llm_client import LLMClient
from dataclasses import dataclass
import logging

logger = logging.getLogger(__name__)


@dataclass
class FactorScores:
    h_visibility: float = 0.5
    h_space_limit: float = 0.5
    h_object_move: float = 0.5
    h_ergonomics: float = 0.5
    h_repeatability: float = 0.5
    s_high_voltage: float = 0.5
    s_chemical: float = 0.5
    s_fire_explosion: float = 0.5
    s_injury: float = 0.5


SCORING_PROMPT = '''为以下拆卸步骤评估9个因素的自动化可行性评分（0-1，越高越适合自动化）。

拆卸步骤：{step_name}
上下文：{context}

评分因素：
1. 可视性 (H1)
2. 空间限制 (H2)
3. 物体移动要求 (H3)
4. 人因工程影响 (H4)
5. 重复性 (H5)
6. 高压风险 (S1)
7. 化学试剂风险 (S2)
8. 火灾爆炸风险 (S3)
9. 人身伤害风险 (S4)

返回JSON格式：
{{"H1": 0.5, "H2": 0.5, "H3": 0.5, "H4": 0.5, "H5": 0.5, "S1": 0.5, "S2": 0.5, "S3": 0.5, "S4": 0.5}}
'''


class AllocatorScorer:
    HUMAN_WEIGHTS = [0.2, 0.2, 0.2, 0.2, 0.2]
    SAFETY_WEIGHTS = [0.25, 0.25, 0.25, 0.25]
    
    def __init__(self, llm_client: LLMClient):
        self.llm = llm_client
    
    def score_step(self, step_name: str, context: str = '') -> FactorScores:
        prompt = SCORING_PROMPT.format(step_name=step_name, context=context)
        try:
            result = self.llm.generate_json(prompt, ['H1', 'H2', 'H3', 'H4', 'H5', 'S1', 'S2', 'S3', 'S4'])
            return FactorScores(
                h_visibility=result.get('H1', 0.5),
                h_space_limit=result.get('H2', 0.5),
                h_object_move=result.get('H3', 0.5),
                h_ergonomics=result.get('H4', 0.5),
                h_repeatability=result.get('H5', 0.5),
                s_high_voltage=result.get('S1', 0.5),
                s_chemical=result.get('S2', 0.5),
                s_fire_explosion=result.get('S3', 0.5),
                s_injury=result.get('S4', 0.5)
            )
        except Exception as e:
            logger.error(f'Failed to score step {step_name}: {e}')
            return FactorScores()
```

- [ ] **Step 2: 创建 tests/allocator/test_scorer.py**

```python
import pytest
from src.allocator.scorer import AllocatorScorer, FactorScores


def test_scorer_import():
    assert AllocatorScorer is not None


def test_factor_scores_default():
    scores = FactorScores()
    assert scores.h_visibility == 0.5
    assert scores.s_high_voltage == 0.5
```

- [ ] **Step 3: 运行测试**

```bash
python -m pytest tests/allocator/test_scorer.py -v
```

- [ ] **Step 4: Commit**

```bash
git add src/allocator/scorer.py tests/allocator/test_scorer.py
git commit -m "feat(allocator): add LLM scorer for 9 factors"
```

---

### Task 11: 人机协作 - AS计算器

**Files:**
- Create: `src/allocator/as_calculator.py`
- Create: `tests/allocator/test_as_calculator.py`

- [ ] **Step 1: 创建 src/allocator/as_calculator.py**

```python
from src.allocator.scorer import FactorScores


class ASCalculator:
    """
    Calculate Automation Score (AS) based on 9 factors.
    
    AS = 0.5 * [Σ(Hi × Wi) + Σ(Si × wi)]
    
    Rules:
    - AS > 0.6 → robot
    - AS < 0.4 → human
    - 0.4 ≤ AS ≤ 0.6 → cost comparison
    """
    
    HUMAN_WEIGHTS = [0.2, 0.2, 0.2, 0.2, 0.2]
    SAFETY_WEIGHTS = [0.25, 0.25, 0.25, 0.25]
    
    ROBOT_THRESHOLD = 0.6
    HUMAN_THRESHOLD = 0.4
    
    def calculate(self, scores: FactorScores) -> float:
        h_values = [
            scores.h_visibility,
            scores.h_space_limit,
            scores.h_object_move,
            scores.h_ergonomics,
            scores.h_repeatability
        ]
        
        s_values = [
            scores.s_high_voltage,
            scores.s_chemical,
            scores.s_fire_explosion,
            scores.s_injury
        ]
        
        h_sum = sum(h * w for h, w in zip(h_values, self.HUMAN_WEIGHTS))
        s_sum = sum(s * w for s, w in zip(s_values, self.SAFETY_WEIGHTS))
        
        return 0.5 * (h_sum + s_sum)
    
    def recommend(self, as_score: float) -> str:
        if as_score > self.ROBOT_THRESHOLD:
            return 'robot'
        elif as_score < self.HUMAN_THRESHOLD:
            return 'human'
        else:
            return 'cost_comparison'
```

- [ ] **Step 2: 创建 tests/allocator/test_as_calculator.py**

```python
import pytest
from src.allocator.as_calculator import ASCalculator
from src.allocator.scorer import FactorScores


def test_as_calculator_import():
    assert ASCalculator is not None


def test_calculate_robot():
    calc = ASCalculator()
    scores = FactorScores(
        h_visibility=0.8, h_space_limit=0.8, h_object_move=0.8,
        h_ergonomics=0.8, h_repeatability=0.8,
        s_high_voltage=0.8, s_chemical=0.8, s_fire_explosion=0.8, s_injury=0.8
    )
    as_score = calc.calculate(scores)
    assert as_score > 0.6


def test_calculate_human():
    calc = ASCalculator()
    scores = FactorScores(
        h_visibility=0.1, h_space_limit=0.1, h_object_move=0.1,
        h_ergonomics=0.1, h_repeatability=0.1,
        s_high_voltage=0.1, s_chemical=0.1, s_fire_explosion=0.1, s_injury=0.1
    )
    as_score = calc.calculate(scores)
    assert as_score < 0.4


def test_recommend_robot():
    calc = ASCalculator()
    assert calc.recommend(0.7) == 'robot'


def test_recommend_human():
    calc = ASCalculator()
    assert calc.recommend(0.3) == 'human'


def test_recommend_cost():
    calc = ASCalculator()
    assert calc.recommend(0.5) == 'cost_comparison'
```

- [ ] **Step 3: 运行测试**

```bash
python -m pytest tests/allocator/test_as_calculator.py -v
```

- [ ] **Step 4: Commit**

```bash
git add src/allocator/as_calculator.py tests/allocator/test_as_calculator.py
git commit -m "feat(allocator): add AS calculator"
```

---

### Task 12: 人机协作 - 分配主逻辑

**Files:**
- Create: `src/allocator/allocator.py`
- Create: `tests/allocator/test_allocator.py`

- [ ] **Step 1: 创建 src/allocator/allocator.py**

```python
from src.allocator.scorer import AllocatorScorer, FactorScores
from src.allocator.as_calculator import ASCalculator
from src.sequence.planner import DisassemblySequence, DisassemblyStep
from dataclasses import dataclass
import logging

logger = logging.getLogger(__name__)


@dataclass
class CostFactors:
    human_cost: float = 1.0
    robot_cost: float = 1.0
    human_loss: float = 0.0
    robot_loss: float = 0.0


class HumanRobotAllocator:
    ROBOT_THRESHOLD = 0.6
    HUMAN_THRESHOLD = 0.4
    
    def __init__(self, llm_client):
        self.scorer = AllocatorScorer(llm_client)
        self.calculator = ASCalculator()
    
    def allocate(self, sequence: DisassemblySequence, context: str = '') -> DisassemblySequence:
        for step in sequence.steps:
            scores = self.scorer.score_step(step.name, context)
            as_score = self.calculator.calculate(scores)
            
            if as_score > self.ROBOT_THRESHOLD:
                step.assignee = 'robot'
            elif as_score < self.HUMAN_THRESHOLD:
                step.assignee = 'human'
            else:
                step.assignee = self._cost_comparison(step, scores)
        
        return sequence
    
    def _cost_comparison(self, step: DisassemblyStep, scores: FactorScores) -> str:
        human_cost = 1.0 + (1 - scores.h_ergonomics) * 0.5
        robot_cost = 1.0 + (1 - scores.s_high_voltage) * 0.3
        
        return 'robot' if robot_cost < human_cost else 'human'
```

- [ ] **Step 2: 创建 tests/allocator/test_allocator.py**

```python
import pytest
from src.allocator.allocator import HumanRobotAllocator, CostFactors


def test_allocator_import():
    assert HumanRobotAllocator is not None


def test_cost_factors_default():
    costs = CostFactors()
    assert costs.human_cost == 1.0
    assert costs.robot_cost == 1.0
```

- [ ] **Step 3: 运行测试**

```bash
python -m pytest tests/allocator/test_allocator.py -v
```

- [ ] **Step 4: Commit**

```bash
git add src/allocator/allocator.py tests/allocator/test_allocator.py
git commit -m "feat(allocator): add human-robot allocator"
```

---

### Task 13: 混合图输出 - Mermaid生成器

**Files:**
- Create: `src/graph_output/mermaid_gen.py`
- Create: `tests/graph_output/test_mermaid_gen.py`

- [ ] **Step 1: 创建 src/graph_output/mermaid_gen.py**

```python
from src.sequence.planner import DisassemblySequence, DisassemblyStep
import logging

logger = logging.getLogger(__name__)


class MermaidGenerator:
    def __init__(self):
        self.node_styles = {
            'robot': 'fill:#90EE90,stroke:#228B22',
            'human': 'fill:#87CEEB,stroke:#4169E1',
            'default': 'fill:#f9f,stroke:#333'
        }
    
    def generate(self, sequence: DisassemblySequence, edges: list[tuple[str, str]] = None) -> str:
        lines = ['graph TD']
        
        for step in sequence.steps:
            label = f'{step.name}\\n({step.time_estimate}s)'
            style = self._get_node_style(step)
            lines.append(f'    {step.id}[\'{label}\"]:::{style}')
        
        if edges:
            for source, target in edges:
                lines.append(f'    {source} --> {target}')
        else:
            for i in range(len(sequence.steps) - 1):
                curr = sequence.steps[i]
                next_step = sequence.steps[i + 1]
                lines.append(f'    {curr.id} --> {next_step.id}')
        
        lines.append('')
        lines.append('    classDef robot fill:#90EE90,stroke:#228B22')
        lines.append('    classDef human fill:#87CEEB,stroke:#4169E1')
        
        return '\n'.join(lines)
    
    def _get_node_style(self, step: DisassemblyStep) -> str:
        if step.assignee == 'robot':
            return 'robot'
        elif step.assignee == 'human':
            return 'human'
        return 'default'
```

- [ ] **Step 2: 创建 tests/graph_output/test_mermaid_gen.py**

```python
import pytest
from src.graph_output.mermaid_gen import MermaidGenerator
from src.sequence.planner import DisassemblyStep


def test_mermaid_generator_import():
    assert MermaidGenerator is not None


def test_generate_basic():
    gen = MermaidGenerator()
    steps = [
        DisassemblyStep(id='A', name='Cover', time_estimate=10),
        DisassemblyStep(id='B', name='Screws', time_estimate=20)
    ]
    from src.sequence.planner import DisassemblySequence
    seq = DisassemblySequence(steps=steps, total_time=30, parallel_groups=[['A'], ['B']])
    mermaid = gen.generate(seq)
    assert 'graph TD' in mermaid
    assert 'A' in mermaid
    assert 'B' in mermaid
```

- [ ] **Step 3: 运行测试**

```bash
python -m pytest tests/graph_output/test_mermaid_gen.py -v
```

- [ ] **Step 4: Commit**

```bash
git add src/graph_output/mermaid_gen.py tests/graph_output/test_mermaid_gen.py
git commit -m "feat(graph_output): add Mermaid generator"
```

---

### Task 14: 混合图输出 - JSON构建器

**Files:**
- Create: `src/graph_output/json_builder.py`
- Create: `tests/graph_output/test_json_builder.py`

- [ ] **Step 1: 创建 src/graph_output/json_builder.py**

```python
from src.sequence.planner import DisassemblySequence, DisassemblyStep
from typing import Any


class JSONGraphBuilder:
    def build(self, sequence: DisassemblySequence, edges: list[tuple[str, str]] = None) -> dict[str, Any]:
        nodes = [
            {
                'id': step.id,
                'label': step.name,
                'time': step.time_estimate,
                'assignee': step.assignee,
                'parallel_with': step.parallel_with
            }
            for step in sequence.steps
        ]
        
        graph_edges = []
        if edges:
            for source, target in edges:
                graph_edges.append({'from': source, 'to': target, 'type': 'PRECEDES'})
        else:
            for i in range(len(sequence.steps) - 1):
                curr = sequence.steps[i]
                next_step = sequence.steps[i + 1]
                graph_edges.append({'from': curr.id, 'to': next_step.id, 'type': 'PRECEDES'})
        
        return {
            'nodes': nodes,
            'edges': graph_edges,
            'parallel_groups': sequence.parallel_groups,
            'total_time': sequence.total_time,
            'metadata': {
                'has_cycles': sequence.has_cycles,
                'cycle_nodes': sequence.cycle_nodes
            }
        }
```

- [ ] **Step 2: 创建 tests/graph_output/test_json_builder.py**

```python
import pytest
from src.graph_output.json_builder import JSONGraphBuilder
from src.sequence.planner import DisassemblyStep, DisassemblySequence


def test_json_builder_import():
    assert JSONGraphBuilder is not None


def test_build_basic():
    builder = JSONGraphBuilder()
    steps = [
        DisassemblyStep(id='A', name='Cover', time_estimate=10),
        DisassemblyStep(id='B', name='Screws', time_estimate=20)
    ]
    seq = DisassemblySequence(steps=steps, total_time=30, parallel_groups=[['A'], ['B']])
    result = builder.build(seq)
    assert 'nodes' in result
    assert 'edges' in result
    assert 'parallel_groups' in result
    assert len(result['nodes']) == 2
```

- [ ] **Step 3: 运行测试**

```bash
python -m pytest tests/graph_output/test_json_builder.py -v
```

- [ ] **Step 4: Commit**

```bash
git add src/graph_output/json_builder.py tests/graph_output/test_json_builder.py
git commit -m "feat(graph_output): add JSON graph builder"
```

---

### Task 15: 混合图输出 - 输出主逻辑

**Files:**
- Create: `src/graph_output/generator.py`
- Create: `tests/graph_output/test_generator.py`

- [ ] **Step 1: 创建 src/graph_output/generator.py**

```python
from src.graph_output.mermaid_gen import MermaidGenerator
from src.graph_output.json_builder import JSONGraphBuilder
from src.sequence.planner import DisassemblySequence
from dataclasses import dataclass
from typing import Any


@dataclass
class GraphOutput:
    mermaid: str
    json: dict[str, Any]
    total_time: int
    parallel_groups: list[list[str]]


class GraphOutputGenerator:
    def __init__(self):
        self.mermaid_gen = MermaidGenerator()
        self.json_builder = JSONGraphBuilder()
    
    def generate(self, sequence: DisassemblySequence, edges: list[tuple[str, str]] = None) -> GraphOutput:
        mermaid = self.mermaid_gen.generate(sequence, edges)
        json_graph = self.json_builder.build(sequence, edges)
        
        return GraphOutput(
            mermaid=mermaid,
            json=json_graph,
            total_time=sequence.total_time,
            parallel_groups=sequence.parallel_groups
        )
```

- [ ] **Step 2: 创建 tests/graph_output/test_generator.py**

```python
import pytest
from src.graph_output.generator import GraphOutputGenerator, GraphOutput


def test_generator_import():
    assert GraphOutputGenerator is not None


def test_graph_output_dataclass():
    assert GraphOutput is not None
```

- [ ] **Step 3: 运行测试**

```bash
python -m pytest tests/graph_output/test_generator.py -v
```

- [ ] **Step 4: Commit**

```bash
git add src/graph_output/generator.py tests/graph_output/test_generator.py
git commit -m "feat(graph_output): add graph output generator"
```

---

### Task 16: API层 - 新增端点

**Files:**
- Modify: `src/api/routes.py`
- Create: `src/api/schemas_phase2.py`

- [ ] **Step 1: 创建 src/api/schemas_phase2.py**

```python
from pydantic import BaseModel
from typing import Optional


class SequenceRequest(BaseModel):
    battery_model: str
    components: list[dict] = []


class SequenceResponse(BaseModel):
    code: int = 0
    message: str = 'Success'
    data: Optional[dict] = None


class AllocateRequest(BaseModel):
    sequence: dict
    context: str = ''


class GraphRequest(BaseModel):
    sequence: dict
    edges: list[tuple[str, str]] = []


class GraphResponse(BaseModel):
    code: int = 0
    message: str = 'Success'
    data: Optional[dict] = None


class ImportRequest(BaseModel):
    file_path: str


class ImportResponse(BaseModel):
    code: int = 0
    message: str = 'Success'
    data: Optional[dict] = None


class PromoteRequest(BaseModel):
    doc_id: str
    component_data: dict


class PromoteResponse(BaseModel):
    code: int = 0
    message: str = 'Success'
    data: Optional[dict] = None
```

- [ ] **Step 2: 更新 src/api/routes.py 添加新端点**

```python
from fastapi import APIRouter, HTTPException
from src.api.schemas import PlanRequest, PlanResponse, HealthResponse
from src.api.schemas_phase2 import (
    SequenceRequest, SequenceResponse,
    AllocateRequest, AllocateResponse,
    GraphRequest, GraphResponse,
    ImportRequest, ImportResponse,
    PromoteRequest, PromoteResponse
)
from src.sequence.planner import SequencePlanner
from src.allocator.allocator import HumanRobotAllocator
from src.graph_output.generator import GraphOutputGenerator
from src.importer.importer import DataImporter
from src.kg.client import Neo4jClient, MilvusClient
from src.utils.llm_client import LLMClient
from src.config import settings
import logging

logger = logging.getLogger(__name__)

router = APIRouter()

neo4j_client = Neo4jClient(settings.neo4j_uri, settings.neo4j_user, settings.neo4j_password)
milvus_client = MilvusClient(settings.milvus_host, settings.milvus_port) if hasattr(settings, 'milvus_host') else None
llm_client = LLMClient(settings.openai_api_key, settings.openai_base_url, settings.model, settings.temperature, settings.max_tokens)

importer = DataImporter(neo4j_client, llm_client)
sequence_planner = SequencePlanner()
allocator = HumanRobotAllocator(llm_client)
graph_generator = GraphOutputGenerator()


@router.post('/api/v1/disassembly/sequence', response_model=SequenceResponse)
async def create_sequence(request: SequenceRequest):
    try:
        from src.kg.models import Component
        components = [Component(**c) for c in request.components]
        sequence = sequence_planner.plan(components)
        return SequenceResponse(
            data={
                'steps': [{'id': s.id, 'name': s.name, 'time_estimate': s.time_estimate} for s in sequence.steps],
                'total_time': sequence.total_time,
                'parallel_groups': sequence.parallel_groups
            }
        )
    except Exception as e:
        logger.error(f'Sequence creation failed: {e}')
        raise HTTPException(status_code=500, detail=str(e))


@router.post('/api/v1/disassembly/allocate', response_model=AllocateResponse)
async def allocate_tasks(request: AllocateRequest):
    try:
        from src.sequence.planner import DisassemblySequence, DisassemblyStep
        steps = [DisassemblyStep(**s) for s in request.sequence.get('steps', [])]
        sequence = DisassemblySequence(
            steps=steps,
            total_time=request.sequence.get('total_time', 0),
            parallel_groups=request.sequence.get('parallel_groups', [])
        )
        allocated = allocator.allocate(sequence, request.context)
        return AllocateResponse(
            data={
                'steps': [{'id': s.id, 'name': s.name, 'assignee': s.assignee} for s in allocated.steps]
            }
        )
    except Exception as e:
        logger.error(f'Allocation failed: {e}')
        raise HTTPException(status_code=500, detail=str(e))


@router.post('/api/v1/disassembly/graph', response_model=GraphResponse)
async def generate_graph(request: GraphRequest):
    try:
        from src.sequence.planner import DisassemblySequence, DisassemblyStep
        steps = [DisassemblyStep(**s) for s in request.sequence.get('steps', [])]
        sequence = DisassemblySequence(
            steps=steps,
            total_time=request.sequence.get('total_time', 0),
            parallel_groups=request.sequence.get('parallel_groups', [])
        )
        graph = graph_generator.generate(sequence, request.edges)
        return GraphResponse(
            data={
                'mermaid': graph.mermaid,
                'json': graph.json,
                'total_time': graph.total_time
            }
        )
    except Exception as e:
        logger.error(f'Graph generation failed: {e}')
        raise HTTPException(status_code=500, detail=str(e))


@router.post('/api/v1/admin/import/pdf', response_model=ImportResponse)
async def import_pdf(request: ImportRequest):
    try:
        result = importer.import_pdf(request.file_path)
        return ImportResponse(data=result)
    except Exception as e:
        logger.error(f'Import failed: {e}')
        raise HTTPException(status_code=500, detail=str(e))


@router.post('/api/v1/admin/components/promote', response_model=PromoteResponse)
async def promote_to_component(request: PromoteRequest):
    try:
        component = importer.promote_to_component(request.doc_id, request.component_data)
        return PromoteResponse(
            data={'id': component.id, 'name': component.name}
        )
    except Exception as e:
        logger.error(f'Promote failed: {e}')
        raise HTTPException(status_code=500, detail=str(e))
```

- [ ] **Step 3: Commit**

```bash
git add src/api/schemas_phase2.py src/api/routes.py
git commit -m "feat(api): add Phase 2 endpoints"
```

---

## 验收标准

- [ ] Task 1-5: 数据导入模块完成
- [ ] Task 6-9: 拆卸序列规划模块完成
- [ ] Task 10-12: 人机协作分配模块完成
- [ ] Task 13-15: 混合图输出模块完成
- [ ] Task 16: API层整合完成

---

## 总结

**计划文件:** `docs/superpowers/plans/2026-04-14-phase2-implementation-plan.md`

**下一步执行选项：**

**1. Subagent-Driven (推荐)** - 每个任务由独立子代理执行，任务间进行审查和快速迭代

**2. Inline Execution** - 使用executing-plans技能在此会话中执行任务，设置检查点进行审查

**你选择哪种方式？**