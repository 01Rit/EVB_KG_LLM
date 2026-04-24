# Alias Dictionary 增强实现计划

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development or superpowers:executing-plans

**Goal:** 扩展 alias dictionary 并改进匹配逻辑，提升 L2 coverage

**Architecture:**
- 修改 `src/cross_layer/batch_builder.py`
- 新增 normalization 函数
- 新增自动抽取函数
- 新增三层 alias 融合构建

---

## Task 1: 实现 Normalization 函数

**Files:**
- Modify: `src/cross_layer/batch_builder.py`

- [ ] **Step 1: 添加 normalize_term 函数**

```python
def normalize_term(name: str) -> str:
    """规范化术语：去连字符/复数/单位/括号内容"""
    if not name:
        return ''
    n = name.lower().strip()
    # 去括号内容
    n = re.sub(r'\s*\([^)]*\)', '', n)
    n = re.sub(r'\s*\[[^\]]*\]', '', n)
    # 去连字符
    n = re.sub(r'[-\s_]+', ' ', n)
    # 去复数（简单规则）
    if n.endswith('s') and len(n) > 2:
        n = n[:-1]
    # 去单位/编号（M6, #12等）
    n = re.sub(r'\b[M#]?\d+\b', '', n)
    n = n.strip()
    return n
```

- [ ] **Step 2: 验证 normalize_term**

```python
assert normalize_term('Battery-Pack') == 'battery pack'
assert normalize_term('cells') == 'cell'
assert normalize_term('M6 bolt') == 'bolt'
assert normalize_term('battery module (BM)') == 'battery module'
```

- [ ] **Step 3: Commit**

```bash
git add src/cross_layer/batch_builder.py
git commit -m "feat: add normalize_term function for alias normalization"
```

---

## Task 2: 实现 Stopword 过滤 + 清洗规则

**Files:**
- Modify: `src/cross_layer/batch_builder.py`

- [ ] **Step 1: 添加 STOPWORDS 和清洗函数**

```python
STOPWORDS = {"system", "device", "component", "unit", "part", "item", "element"}

def is_valid_term(term: str, is_english: bool) -> bool:
    """验证术语是否有效"""
    term = term.strip()
    if not term or len(term) < 2:
        return False
    if term in STOPWORDS:
        return False
    if is_english:
        tokens = term.split()
        if len(tokens) > 4:
            return False
    else:
        if len(term) > 10:
            return False
    return True

def filter_invalid_terms(terms: list[str], is_english: bool) -> list[str]:
    """过滤无效术语"""
    return [t for t in terms if is_valid_term(t, is_english)]
```

- [ ] **Step 2: Commit**

```bash
git add src/cross_layer/batch_builder.py
git commit -m "feat: add stopword filter and validation for alias terms"
```

---

## Task 3: 实现自动抽取函数

**Files:**
- Modify: `src/cross_layer/batch_builder.py`

- [ ] **Step 1: 添加抽取正则和函数**

```python
EXTRACTION_PATTERNS = [
    r'([\u4e00-\u9fa5]+)[（(]([A-Za-z0-9\s\-]+)[）)]',  # Pattern A: 中文→英文
    r'([A-Za-z0-9\s\-]+)[（(]([\u4e00-\u9fa5]+)[）)]',  # Pattern B: 英文→中文
    r'([\u4e00-\u9fa5]+)\s*\[([A-Za-z0-9\s\-]+)\]',      # Pattern C: 方括号
    r'([\u4e00-\u9fa5]+)\s*-\s*([A-Za-z0-9\s\-]+)',       # Pattern D: 破折号
]

def extract_alias_pairs(text: str) -> list[tuple[str, str]]:
    """从文本中抽取中英文术语对"""
    pairs = []
    for pattern in EXTRACTION_PATTERNS:
        matches = re.findall(pattern, text, re.UNICODE)
        for match in matches:
            if len(match) == 2:
                # 判断哪个是英文哪个是中文
                if re.search(r'[\u4e00-\u9fa5]', match[0]):
                    chinese, english = match[0], match[1]
                else:
                    english, chinese = match[0], match[1]
                english = english.strip().lower()
                chinese = chinese.strip()
                if is_valid_term(english, True) and is_valid_term(chinese, False):
                    pairs.append((english, chinese))
    return pairs
```

- [ ] **Step 2: Commit**

```bash
git add src/cross_layer/batch_builder.py
git commit -m "feat: add automatic alias extraction from documents"
```

---

## Task 4: 实现 Alias 方向统一 + 去冲突 + 三层融合

**Files:**
- Modify: `src/cross_layer/batch_builder.py`

- [ ] **Step 1: 重构 build_alias_sets 函数**

```python
def build_extended_alias_dict() -> dict[str, list[str]]:
    """构建扩展 alias dictionary (English -> [Chinese aliases])"""
    # Layer 1: 手工词典
    manual_dict = {
        "battery module": ["电池模块", "电池模组", "模块"],
        "busbar": ["汇流排", "母线"],
        "electrolyte": ["电解液"],
        "cell": ["电芯"],
        "tab": ["极耳"],
        "connector": ["连接器", "接插件"],
        "housing": ["外壳", "壳体"],
        "insulator": ["绝缘体", "绝缘板"],
        "cooling plate": ["冷却板"],
        "thermal pad": ["导热垫"],
        "bms": ["电池管理系统"],
        "fuse": ["熔断器", "保险丝"],
    }

    # Layer 2: 自动抽取 (需要从文档调用)
    # auto_dict = extract_from_documents()

    # Layer 3: 用户自定义 (从配置文件加载)
    # user_dict = load_user_aliases()

    # 融合 (手工优先)
    merged = dict(manual_dict)

    return merged

def build_alias_sets(alias_dict: dict[str, list[str]]) -> dict[str, set[str]]:
    """从 alias_dict 构建 alias_sets"""
    alias_map = {}
    for english, chinese_list in alias_dict.items():
        norm_en = normalize_term(english)
        if norm_en not in alias_map:
            alias_map[norm_en] = set()
        for chinese in chinese_list:
            norm_cn = normalize_term(chinese)
            alias_map[norm_en].add(norm_cn)
    return alias_map
```

- [ ] **Step 2: 去冲突函数**

```python
def deduplicate_aliases(aliases: list[str]) -> list[str]:
    """优先保留更长、更具体的中文"""
    aliases = list(set(aliases))
    aliases.sort(key=len, reverse=True)
    return aliases
```

- [ ] **Step 3: Commit**

```bash
git add src/cross_layer/batch_builder.py
git commit -m "feat: implement unified alias direction and deduplication"
```

---

## Task 5: 修改匹配逻辑（alias > contains > embedding）

**Files:**
- Modify: `src/cross_layer/batch_builder.py`

- [ ] **Step 1: 修改 are_aliases 优先级**

```python
def are_aliases(name1: str, name2: str, alias_sets: dict[str, set[str]]) -> tuple[bool, float]:
    """判断两个名称是否为 alias，返回 (is_alias, score)"""
    n1 = normalize_term(name1)
    n2 = normalize_term(name2)

    # 1. 精确匹配
    if n1 == n2:
        return True, 1.0

    # 2. alias set 匹配
    if n1 in alias_sets and n2 in alias_sets[n1]:
        return True, 1.0
    if n2 in alias_sets and n1 in alias_sets[n2]:
        return True, 1.0

    # 3. contains 匹配
    if n1 in n2 or n2 in n1:
        return True, 0.8

    return False, 0.0
```

- [ ] **Step 2: 修改 _build_definition_of 使用新逻辑**

- [ ] **Step 3: Commit**

```bash
git add src/cross_layer/batch_builder.py
git commit -m "feat: update matching logic with priority alias > contains > embedding"
```

---

## Task 6: 测试验证

**Files:**
- Create: `tests/cross_layer/test_alias_normalization.py`

- [ ] **Step 1: 编写测试**

```python
def test_normalize_term():
    assert normalize_term('Battery-Pack') == 'battery pack'
    assert normalize_term('cells') == 'cell'
    assert normalize_term('M6 bolt') == 'bolt'
    assert normalize_term('battery module (BM)') == 'battery module'

def test_stopword_filter():
    assert is_valid_term('system', True) is False
    assert is_valid_term('battery module', True) is True
    assert is_valid_term('电解液', False) is True
    assert is_valid_term('电池模块模块模块模块', False) is False

def test_alias_extraction():
    pairs = extract_alias_pairs('电池模块(battery module)')
    assert ('battery module', '电池模块') in pairs
```

- [ ] **Step 2: 运行测试**

```bash
python -m pytest tests/cross_layer/test_alias_normalization.py -v
```

- [ ] **Step 3: 测试 build-all API**

```bash
curl -X POST http://localhost:8000/api/v1/cross-layer/build-all
```

验证 L2 coverage 提升

- [ ] **Step 4: Commit**

```bash
git add tests/
git commit -m "test: add alias normalization tests"
```

---

## 验证命令

```bash
# 测试 normalization
python -c "from src.cross_layer.batch_builder import normalize_term; print(normalize_term('Battery-Pack'))"

# 测试完整 build
curl -X POST http://localhost:8000/api/v1/cross-layer/build-all

# 验证 L2 coverage
python -c "
from src.kg.client import Neo4jClient
from src.config import settings
neo4j = Neo4jClient(settings.neo4j_uri, settings.neo4j_user, settings.neo4j_password)
r = neo4j.execute_query('MATCH (e:L2_Entity)-[:DEFINITION_OF]->(:L3_Term) WITH count(DISTINCT e) as cnt RETURN cnt')
print('L2 covered:', r)
neo4j.close()
"
```

## Spec Coverage

| 设计要求 | 对应 Task |
|----------|-----------|
| Normalization（去连字符/复数/单位） | Task 1 |
| Stopword 过滤 | Task 2 |
| 自动抽取正则 | Task 3 |
| Alias 方向统一 | Task 4 |
| 去冲突 | Task 4 |
| 匹配优先级（alias > contains > embedding） | Task 5 |
| 测试验证 | Task 6 |
