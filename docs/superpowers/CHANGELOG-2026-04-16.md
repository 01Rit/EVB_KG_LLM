# 三层知识图谱架构重构 - 修改文档

**日期：** 2026.04.16
**版本：** v1.0
**作者：** Superpowers Agent
**分支：** feature/l2-import-refactoring

---

## 1. 概述

本次修改重构了动力电池拆卸知识图谱的 L2 导入流程，实现了**逻辑分层 + 物理互联**的三层架构（L1/L2/L3），使节点之间跨层互联，支持 LLM 推理时多跳检索。

### 三层架构定义

| 层级 | 节点类型 | 描述 | 查询场景 |
|------|----------|------|----------|
| **L1** | Component | 拆卸部件节点，从 L1 导入创建 | 拆卸序列生成（仅查 L1） |
| **L2** | Document + Entity | 参考文档节点 + 从文档提取的实体节点 | LLM 推理时的多跳检索 |
| **L3** | Term | 术语定义节点（国标定义、度量标准） | LLM 推理时的定义查询 |

---

## 2. 变更内容

### 2.1 新增文件

| 文件 | 说明 |
|------|------|
| `src/importer/l2_importer.py` | L2 导入编排类，负责提取实体、创建节点、建立跨层关系 |
| `tests/importer/test_l2_importer.py` | L2Importer 单元测试（6个测试用例） |

### 2.2 修改文件

| 文件 | 修改内容 |
|------|----------|
| `src/api/schemas.py` | 新增 L2/L3 相关 Pydantic schemas |
| `src/importer/entity_extractor.py` | 新增 `extract_entities_with_types()` 方法，支持 7 种实体类型分类 |
| `src/api/import_routes.py` | 重构 `/import/l2` 端点，使用 L2Importer |
| `tests/api/test_routes.py` | 新增 schema 验证测试 |

### 2.3 新增的节点类型

所有节点新增 `node_type` 属性用于标识层级：

```
L2_Document  - L2 文档节点
L2_Entity   - L2 实体节点
L3_Term     - L3 术语节点
```

### 2.4 新增的跨层关系类型

| 关系 | 起点 | 终点 | 说明 |
|------|------|------|------|
| `CONTAINS` | L2_Document → L2_Entity | 文档包含实体 | L2 导入时创建 |
| `CONTAINS` | L2_Document → L3_Term | 文档包含术语 | L2 导入时创建 |
| `DEFINED_AS` | L2_Entity → L3_Term | 实体定义为术语 | L2 导入时创建 |
| `ORIGINATED_FROM` | L3_Term → L2_Document | 术语来源于文档 | 自动追溯 |
| `REFERENCED_IN` | L2_Entity → L2_Document | 实体被文档引用 | 自动追溯 |

### 2.5 L2 导入流程变更

**Before（旧流程）：**
```
PDF → EntityExtractor.extract_triplets() → 创建 Entity 节点 + Document 节点
```

**After（新流程）：**
```
PDF → L2Importer.import_pdf()
     → L2Importer._create_l2_document()       创建 L2_Document 节点
     → L2Importer._create_l2_entities()        创建 L2_Entity 节点（带 entity_type）
     → L2Importer._create_l3_terms()            创建 L3_Term 节点
     → L2Importer._create_cross_layer_relations() 建立跨层关系
```

---

## 3. 技术细节

### 3.1 实体类型分类

L2 导入的实体支持 7 种类型：

| entity_type | 说明 | 示例 |
|-------------|------|------|
| `component` | 可拆卸部件 | 电池包、模组、电芯 |
| `tool` | 工具 | 扭矩扳手、绝缘工具 |
| `action` | 动作/步骤 | 拆卸、拧松、拔出 |
| `parameter` | 技术参数 | 扭矩值25Nm、电压阈值 |
| `safety` | 安全规范 | 高压安全距离、IP67 |
| `material` | 材料/属性 | 阻燃材料、铝合金 |
| `definition` | 定义 | 预紧力、力矩标准 |

### 3.2 节点属性

**L2_Document:**
```json
{
  "node_type": "L2_Document",
  "doc_id": "uuid",
  "name": "文件名.pdf",
  "source": "文件名.pdf",
  "content": "文档内容（前50000字符）"
}
```

**L2_Entity:**
```json
{
  "node_type": "L2_Entity",
  "id": "uuid",
  "name": "实体名称",
  "entity_type": "component|tool|action|parameter|safety|material|definition",
  "source_evidence": "原文摘录",
  "battery_model": "电池型号",
  "doc_id": "所属文档ID"
}
```

**L3_Term:**
```json
{
  "node_type": "L3_Term",
  "id": "uuid",
  "term_id": "术语ID",
  "name": "术语名称",
  "definition": "术语定义",
  "source_document_id": "来源文档ID"
}
```

### 3.3 性能优化

- 使用 Neo4j `UNWIND` 批量创建节点，避免 N+1 查询问题
- 单个 L2 导入仅需 4 次数据库查询（创建文档 + 创建实体 + 创建术语 + 创建关系）

---

## 4. API 变更

### 4.1 `/import/l2` 端点响应格式

**旧响应：**
```json
{
  "code": 0,
  "message": "...",
  "nodes": 10,
  "relations": 20
}
```

**新响应：**
```json
{
  "code": 0,
  "message": "L2 import completed: 5 entities, 3 terms, 8 relations",
  "doc_id": "uuid",
  "entities": 5,
  "terms": 3,
  "relations": 8,
  "errors": []
}
```

---

## 5. 数据验证查询

### 5.1 验证跨层关系
```cypher
MATCH (d:L2_Document)-[:CONTAINS]->(e:L2_Entity)-[:DEFINED_AS]->(t:L3_Term)
RETURN d.name, e.name, t.name LIMIT 20
```

### 5.2 验证节点数量
```cypher
MATCH (n) WHERE n.node_type IN ['L2_Document', 'L2_Entity', 'L3_Term']
RETURN count(n)
```

### 5.3 验证无 L1 节点被 L2 导入创建
```cypher
MATCH (n:L2_Entity) RETURN count(n)
MATCH (n:Component) RETURN count(n)  -- 应为 0（由 L1 导入独立创建）
```

---

## 6. 提交记录

| 提交 | 说明 |
|------|------|
| 0cacfc2 | feat(api): add L2/L3 Pydantic schemas |
| 6c7db67 | Add extract_entities_with_types method |
| 64a4bb5 | Add test for extract_entities_with_types |
| b15b761 | Fix code quality issues in entity_extractor |
| d98f66a | Add L2Importer orchestration class |
| 6c34604 | Fix parameter bugs in L2Importer |
| fec4ed3 | Fix N+1 query and code quality issues |
| 6993d41 | refactor(import_l2): replace with L2Importer |
| 39150c0 | Add unit tests for L2Importer |
| d074256 | Improve test_l2_importer tests |
| f834b5d | Fix L2Importer tests |
| 9edf078 | test: add schema validation tests |
| bb7ebae | Fix critical review issues |

---

## 7. 已知限制

1. **USES_TOOL 关系暂未实现** - 由于难以准确判断 component 与 tool 的对应关系，当前版本暂时注释了该逻辑。工具信息通过 `source_evidence` 字段记录。

2. **事务支持** - L2Importer 尚未实现完整的事务回滚，如果中间步骤失败可能遗留部分数据。

3. **数据迁移** - 本次修改不包含现有数据的迁移脚本。旧数据（使用 `Document`/`Entity` 标签）将保持不变，需要时可手动迁移。

---

## 8. 下一步计划

1. 实现完整的 USES_TOOL 关系建立逻辑
2. 添加 Neo4j 事务支持
3. 编写数据迁移脚本
4. 更新拆卸序列生成逻辑，优先查询 L1 节点

---

**文档结束**