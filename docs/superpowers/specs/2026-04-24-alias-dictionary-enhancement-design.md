# 中英文术语对齐 - Alias Dictionary 增强设计

## Status: APPROVED

## Context

当前 L2 coverage 仅 16.4%，主要原因是中英文术语未对齐。需要扩展 alias dictionary 并改进匹配逻辑。

## Design

### 1. Alias Dictionary 三层构建

```
手工词典(核心) → 自动抽取(扩展) → 用户自定义(补充)
融合优先级: 手工 > 自动抽取 > 用户自定义
```

### 2. Normalization（必须）

| 规则 | 示例 |
|------|------|
| 去连字符 | battery-pack → battery pack |
| 去复数 | cells → cell |
| 去单位/编号 | M6 bolt → bolt |
| 去括号内容 | battery module (BM) → battery module |

### 3. Stopword 过滤

```python
STOPWORDS = ["system", "device", "component", "unit", "part"]
# 抽取后过滤，防止 alias 污染
```

### 4. Alias 方向统一

```json
{
  "battery module": ["电池模块", "电池模组"],
  "busbar": ["汇流排"]
}
```

### 5. 匹配优先级（召回层）

| 优先级 | 方式 | Score |
|--------|------|-------|
| 1 | alias match | 1.0 |
| 2 | name contains | 0.8 |
| 3 | embedding similarity | 0.75~0.9 |

**注意**：embedding 仅用于 rank + 兜底，不参与召回判断。

### 6. Top-K 前排序

综合评分 = max(alias_score, contains_score, embedding_score)

确保正确 alias 不被 embedding 挤掉。

### 7. 多值 Alias 去冲突

优先保留"更长、更具体"的中文：
- 模块 ❌
- 电池模块 ✔

### 8. 自动抽取正则

| Pattern | 格式 | 示例 |
|---------|------|------|
| A | 中文→英文 | `电池模块(battery module)` |
| B | 英文→中文 | `battery module(电池模块)` |
| C | 方括号 | `电池模块 [battery module]` |
| D | 破折号 | `电池模块 - battery module` |

```python
PATTERNS = [
    r'([\u4e00-\u9fa5]+)[（(]([A-Za-z0-9\s\-]+)[）)]',  # Pattern A
    r'([A-Za-z0-9\s\-]+)[（(]([\u4e00-\u9fa5]+)[）)]',  # Pattern B
    r'([\u4e00-\u9fa5]+)\s*\[([A-Za-z0-9\s\-]+)\]',      # Pattern C
    r'([\u4e00-\u9fa5]+)\s*-\s*([A-Za-z0-9\s\-]+)',       # Pattern D
]
```

### 9. 清洗规则

- 去噪：过滤长句(>5词)、含标点过多、含"应/可/用于"
- 小写统一：Battery Module → battery module
- 去重复
- 长度限制：英文≤4 tokens，中文≤10字

## Implementation

修改 `src/cross_layer/batch_builder.py`:

### 新增函数

1. `normalize_term(name)` - 规范化处理
2. `extract_alias_from_text(text)` - 自动抽取正则
3. `filter_stopwords(alias_set)` - Stopword 过滤
4. `deduplicate_aliases(aliases)` - 多值去冲突
5. `build_extended_alias_dict()` - 三层融合构建

### 修改函数

1. `build_alias_sets()` - 使用统一方向 + 扩展词典
2. `are_aliases()` - 优先 alias > contains > embedding
3. `_build_definition_of()` - 使用新排序逻辑

## Consequences

- L2 coverage 应从 16.4% 提升至 60%+
- 不影响现有 REFERENCE_OF 逻辑
- 仅改 batch_builder.py
