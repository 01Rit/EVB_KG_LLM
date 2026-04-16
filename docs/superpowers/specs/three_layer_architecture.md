# 动力电池拆卸知识图谱三层架构设计

## Status: PROPOSED

## Context

当前系统L1/L2/L3节点共存于同一Neo4j数据库，但**层间无关联关系**，导致：
- LLM多跳推理时无法跨层检索
- 拆卸序列生成仅能查L1，无法利用L2/L3的丰富上下文

## Design

### 三层定义

| 层级 | 节点类型 | 描述 | 查询场景 |
|------|----------|------|----------|
| **L1** | Component (部件) | 拆卸树叶子节点，实际操作对象 | 拆卸序列生成（仅查L1） |
| **L2** | Document (文档) + Entity (实体) | 参考文档 + 从文档提取的部件/工具/动作/参数等 | LLM推理时的多跳检索 |
| **L3** | Term (术语) | 术语定义节点（国标定义、度量标准） | LLM推理时的定义查询 |

### 节点Schema

**L1_Component**:
```json
{
  "node_type": "L1_Component",
  "id": "string",        // 如 "battery_pack_001"
  "name": "string",      // 如 "电池包"
  "component_type": "string", // 如 "battery_pack", "module", "cell"
  "properties": {}
}
```

**L2_Document**:
```json
{
  "node_type": "L2_Document",
  "id": "string",
  "name": "string",
  "source": "string",    // PDF文件名
  "chapter": "string",   // 所属章节
  "properties": {}
}
```

**L2_Entity**:
```json
{
  "node_type": "L2_Entity",
  "id": "string",
  "name": "string",
  "entity_type": "component|tool|action|parameter|safety|material|definition",
  "source_document_id": "string",
  "source_evidence": "string",  // 原文摘录
  "properties": {}
}
```

**L3_Term**:
```json
{
  "node_type": "L3_Term",
  "id": "string",
  "name": "string",      // 如 "预紧力", "力矩标准"
  "definition": "string", // 国标/定义来源
  "source_document_id": "string",
  "properties": {}
}
```

### 跨层关系类型

| 关系 | 起点 | 终点 | 描述 | 创建时机 |
|------|------|------|------|----------|
| `CONTAINS` | L2_Document | L2_Entity | 文档包含某实体 | L2导入时 |
| `DEFINED_AS` | L2_Entity | L3_Term | 实体定义为某术语 | L2导入时 |
| `USES_TOOL` | L2_Entity | L2_Entity (tool) | 实体操作使用工具 | L2导入时 |
| `REFERENCED_IN` | L2_Entity | L2_Document | 实体被某文档引用 | 自动追溯 |
| `ORIGINATED_FROM` | L3_Term | L2_Document | 术语来源于文档 | 自动追溯 |

### L2导入流程（不创建L1节点）

```
PDF上传
  → 创建 L2_Document 节点
  → LLM按章节提取三元组
  → 同章节实体分群
  → 创建 L2_Entity 节点（不创建L1）
  → 对于实体中的术语类型 → 创建 L3_Term 节点
  → 建立 CONTAINS / DEFINED_AS / USES_TOOL 关系
  → 自动建立 REFERENCED_IN / ORIGINATED_FROM 关系
```

### L1节点来源

L1节点通过**现有L1导入流程**创建（`/api/v1/import/l1`），从拆卸序列文件中提取。

**L1与L2的关联**通过**共用的name属性**实现应用层关联（非数据库关联）：
- 查询时：L1组件name → 匹配L2_Entity中相同name的节点 → 跨层推理

## Verification

### 数据验证查询

```cypher
-- 验证L2实体有跨层关系
MATCH (e:L2_Entity)-[r]->(t:L3_Term)
WHERE r.type = 'DEFINED_AS'
RETURN e.name, t.name, r.type LIMIT 20

-- 验证无L1节点被L2导入创建
MATCH (n) WHERE n.node_type IN ['L2_Document', 'L2_Entity', 'L3_Term']
RETURN count(n)
```

## Consequences

- L2导入不再创建L1节点，避免数据混淆
- LLM推理可通过关系路径实现多跳检索
- 拆卸序列生成逻辑无需修改，仅改查询条件
- 现有L1导入流程保持不变