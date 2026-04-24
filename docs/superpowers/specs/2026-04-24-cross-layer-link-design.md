# 三层知识图谱跨层连接技术设计

## Status: APPROVED

## Context

当前系统L1/L2/L3节点共存于同一Neo4j数据库，但**层间无关联关系**，导致：
- LLM多跳推理时无法跨层检索
- 拆卸序列生成仅能查L1，无法利用L2/L3的丰富上下文
- 拆卸操作无法追溯到对应的标准依据和术语定义

## Design

### 四步跨层连接管道

```
Embedding recall (Milvus)
    ↓
Hard rule filter (structure validation)
    ↓
LLM judge (relation-aware gating)
    ↓
Graph write (threshold + per-relation Top-K)
```

### 三层控制逻辑

| 层级 | 作用 | 说明 |
|------|------|------|
| Embedding | 候选生成 | 统一Embedding空间，Milvus向量检索 |
| Rule Filter | 结构合法性 | **Hard constraint**，不满足则直接丢弃，不参与后续评分 |
| LLM | 语义审计 | relation-aware gating，判断语义是否成立 |
| Write Policy | 图结构控制 | per source_node + relation_type Top-K，防止某类关系垄断 |

### 跨层关系类型

| 关系 | 起点→终点 | 含义 | Phase |
|------|-----------|------|-------|
| `REFERENCE_OF` | L1→L2 | 拆卸操作对应的知识来源或标准依据 | Phase 1 |
| `DEFINITION_OF` | L2→L3 | 知识实体对应的术语定义 | Phase 1 |
| `CONSTRAINED_BY` | L1→L3 | 拆卸过程受某术语或规范约束 | Phase 2（需满足触发条件） |

### 置信度分关系类型阈值

| 关系类型 | 高置信（自动通过） | 中置信（LLM精判） | 低置信（直接丢弃） |
|----------|-------------------|------------------|-------------------|
| REFERENCE_OF | ≥ 0.92 | 0.80 ~ 0.92 | < 0.80 |
| DEFINITION_OF | ≥ 0.90 | 0.75 ~ 0.90 | < 0.75 |
| CONSTRAINED_BY | ≥ 0.88 | 0.70 ~ 0.88 | < 0.70 |

> **重要**：不同关系类型的语义分布不同，因此阈值不同。统一阈值会导致某类关系过度召回或过度丢弃。

### 规则过滤设计

#### 规则过滤 = Hard Constraint

**规则过滤是硬条件，不是评分权重**：
- 不满足规则的候选对**直接丢弃**，不进入LLM精判
- 规则过滤的目的：防止结构上不合法的关系污染LLM判断
- 规则过滤先于LLM执行，形成级联过滤

#### 层间类型映射表

| 源实体类型 | 目标实体类型 | 允许的关系 |
|------------|--------------|------------|
| Component | Component, Document, Term | REFERENCE_OF |
| Document | Entity, Term | REFERENCE_OF |
| Entity | Term | DEFINITION_OF |
| Term | Entity | DEFINITION_OF（反向） |
| Component | Term | CONSTRAINED_BY（Phase 2） |

#### 跨层关系方向约束

```
L1 → L2 → L3（严格两跳）
```

不允许：
- L3 → L2 → L1（反向）
- L1 → L3 直连（Phase 2除外）

### Top-K 写入策略

Top-K 按 `source_node + relation_type` 细分：

```
每对 (source_node, relation_type) 最多保留 Top-K 条
```

例如：
- `(BatteryPack, REFERENCE_OF)` → Top 3
- `(BatteryPack, DEFINITION_OF)` → Top 3
- `(Module, REFERENCE_OF)` → Top 3

**为什么不能按 source_node 粗粒度**：
- 否则 REFERENCE_OF 会吞掉 DEFINITION_OF
- 图结构会偏向某类关系，失去平衡

### LLM 精判 Prompt 设计

#### 输入信息
- 源实体：name, type, context
- 目标实体：name, type, context
- 关系类型：REFERENCE_OF / DEFINITION_OF
- 业务约束条件：层间类型映射表规则

#### Prompt 结构
```
你是一个跨层关系判断专家。判断以下两个实体之间是否应该建立 {relation_type} 关系。

源实体：
- 名称：{source_name}
- 类型：{source_type}
- 上下文：{source_context}

目标实体：
- 名称：{target_name}
- 类型：{target_type}
- 上下文：{target_context}

业务约束：
- {constraint_rules}

请判断：是否应该建立 {relation_type} 关系？
输出：YES / NO 及置信度（0.0~1.0）
```

### GraphRAG 集成策略

#### 透明插入
跨层检索作为独立模块，在现有检索流程之后执行，结果合并到证据子图。

#### 触发条件（按需触发）
当以下三重条件**同时满足**时触发跨层检索：
1. **Coverage**：关键概念（如查询中的术语、组件）在检索结果中覆盖率 < 阈值
2. **Structure completeness**：现有证据子图结构不完整（如缺少标准依据）
3. **Minimum evidence**：返回的证据数量 < 最小数量N

#### 结果合并策略
1. 跨层结果与原证据合并
2. 按实体ID去重
3. 按置信度重新排序
4. 裁剪到上限N条

### CONSTRAINED_BY Phase 2 触发条件

Phase 2 启用 CONSTRAINED_BY 需满足：
1. **图稳定性**：三层跨层关系图结构趋于稳定，无剧烈波动
2. **LLM precision > 0.85**：LLM精判准确率达到85%以上
3. **false positive rate low**：误报率低于5%

否则贸然启用 CONSTRAINED_BY 会引入推理型噪声边，污染图谱质量。

## Module Structure

```
src/cross_layer/
├── __init__.py
├── linker.py          # 跨层连接主逻辑：四步管道
├── embedder.py        # Embedding生成与Milvus检索
├── rules.py           # 硬规则过滤：层间类型映射表
├── llm_judge.py       # LLM精判模块
├── write_policy.py    # 写入策略：阈值 + Top-K
└── merger.py          # 跨层结果与现有证据合并
```

## Verification

### 数据验证查询

```cypher
-- 验证跨层关系数量分布
MATCH (s)-[r]->(t)
WHERE type(r) IN ['REFERENCE_OF', 'DEFINITION_OF', 'CONSTRAINED_BY']
RETURN type(r) as relation_type, count(*) as count

-- 验证per-relation Top-K约束
MATCH (s)-[r:REFERENCE_OF]->(t)
WITH s, count(r) as rel_count
WHERE rel_count > 3
RETURN s.name, rel_count

-- 验证三层两跳路径
MATCH (l1:L1)-[:REFERENCE_OF]->(l2:L2)-[:DEFINITION_OF]->(l3:L3)
RETURN l1.name, l2.name, l3.name LIMIT 20
```

## Consequences

- 拆卸序列规划模块（`sequence/`）**完全不受影响**
- GraphRAG检索能力增强，支持多跳跨层推理
- 图谱质量由三层控制逻辑保证：候选→过滤→审计→写入
- CONSTRAINED_BY 暂缓，避免推理噪声边引入
