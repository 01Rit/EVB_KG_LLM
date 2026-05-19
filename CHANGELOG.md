# 变更日志

> 项目：动力电池拆卸知识图谱与 GraphRAG 推理系统
> 格式基于 [Keep a Changelog](https://keepachangelog.com/zh-CN/1.0.0/)

---

## V1.5 — 联网搜索修复：DuckDuckGo → Serper API + 前端来源展示

**发布日期**: 2026-05-19 | **标签**: `v1.5-web-search-fix`

### 概述

修复联网搜索在 Docker 容器内不可用的问题（替换搜索源为 Serper API），补全前端来源展示功能（"参考来源"区域始终为空）。

### 搜索源替换

| 变更 | 说明 |
|------|------|
| `web_searcher.py` | DuckDuckGo → Serper API，`verify_ssl=False` 适配 Docker 网络 |
| `config.py` / `.env` | 新增 `SERPER_API_KEY` 配置 |
| `docker-compose.yml` | 传递 `SERPER_API_KEY` 环境变量 |

### 前端来源展示修复

| 变更 | 说明 |
|------|------|
| `natural_feedback.py` | SSE "done" 事件新增 `sources` 数组 |
| `QueryPage.tsx` | 解析 sources 并渲染可展开来源列表 |
| `CollapsibleSource.tsx` | 增加 `url` 字段，支持"查看原文"链接 |

### 验证

- WebSearcher 容器内搜索正常（3 条结果）
- API 返回 14 条来源（9 本地 KG + 5 联网搜索）
- 前端"参考来源"区域可展开显示摘要及原文链接

---

## V1.4 — 前端设计统一 + 图谱显示修复 + 序列规划Bug修复

**发布日期**: 2026-05-15 | **标签**: `v1.4-frontend-unify-graph-fix`

### 概述

本次迭代完成了三大目标：(1) 全栈前端界面统一为新能源汽车仪表盘设计风格；(2) 修复 Neo4j 图层节点显示不全、导入统计不准确的数据层问题；(3) 修复序列规划接口 500 错误及进度条显示延迟问题。

### 前端设计统一化

| 页面 | 变更内容 |
|------|----------|
| `Dashboard.tsx` | 全新设计：动态数字动画、分层分布图、系统状态卡片、最近查询列表、快速入口网格 |
| `QueryPage.tsx` | 统一进度条样式、搜索历史下拉、Debug模式开关、响应式布局 |
| `SequencePlanner.tsx` | 统一进度条布局、电池型号搜索下拉、拓扑+LLM双结果展示、甘特图集成 |
| `ImportManager.tsx` | 三Tab布局（L1/L2/L3）、统一进度卡片、批量导入按钮组 |
| `GraphExplorer.tsx` | 节点筛选+搜索、力导向图全屏模式、节点详情面板 |
| `Settings.tsx` | Tab式分类设置、配置编辑+保存、系统信息展示 |
| `Sidebar.tsx` | 统一导航样式、活跃页面高亮 |
| `index.css` | 910行全新CSS变量体系：统一颜色、阴影、间距、动画、组件样式 |

**设计规范**：
- CSS 变量驱动的主题系统（`--color-*`, `--space-*`, `--radius-*`, `--shadow-*`）
- 卡片式布局（`.card` + `.card-header` 模式）
- 统一进度条组件（`.progress-bar-container`, `.progress-steps`）
- 渐入动画（`slideUp`, `fadeIn`）+ 骨架屏加载态
- 三色层标识系统（L1=蓝色, L2=绿色, L3=橙色）

### 进度条即时显示优化

**问题**：所有进度条在加载时有延迟弹出。

**修复**：进度条容器始终在 `loading` 状态下渲染，添加 `indeterminate` 动画类，`QueryPage`、`SequencePlanner`、`ImportManager` 三端统一实现。

### 图谱节点显示修复

**问题**：图谱页面只能获取 L1 组件，L2/L3 节点在数据库中存在但未显示。根因为 Neo4j 查询使用了 `:Document` 和 `:Term` 标签，但实际数据库节点标签为 `:L2_Document`、`:L2_Entity`、`:L3_Term`。

**修复**：`graph_routes.py` 所有查询统一使用 `:Component|L2_Document|L2_Entity|L3_Term` 多标签匹配；新增 `L2_Entity` 映射；`models.py` 增加 `.get()` 容错读取。

### 导入统计修复

**问题**：Dashboard 显示 L2 文档数量仅为 10（仅 `:L2_Document`），实际 L2 层有 395 个 `:L2_Entity` 节点未统计。

**修复**：`import_routes.py` Cypher 查询增加 `OR d:L2_Entity`；Dashboard 标签改为 "L2 文档和实体数量"。

### 序列规划 500 错误修复

**问题**：`POST /api/v1/disassembly/plan` 返回 `500 Internal Server Error`，错误信息 `'start'` 键不存在。

**根因**：`cross_layer_retriever.py` 构建边时使用 `source/target/relation_type` 键名，但 `EvidenceGraph.to_text()` 使用 `edge["start"]/edge["end"]/edge["type"]` 访问。

**修复**：边字典键名统一为 `start/end/type/properties`；`to_text()` 增加 `.get()` 容错支持两种键名格式。

**涉及文件**：
- `src/graphrag/cross_layer_retriever.py`
- `src/kg/models.py`
- `src/api/routes.py`

---

## V1.3 — 跨层多跳查询修复 + 向量语义搜索

**发布日期**: 2026-05-15 | **标签**: `v1.3-cross-layer-query-fix`

### 概述

修复了知识图谱跨层多跳查询的核心问题，引入基于 DashScope `text-embedding-v4` 的向量语义搜索。修复后 L1 Component → L2_Entity → L2_Document/L3_Term 的完整推理链路正常工作，自然语言问答可正确引用 GB/T 国标文档。

### 跨层多跳遍历修复（核心）

**问题**：查询"Audi A3冷却板的国标标准"时回答"无法确定"。

**根因**：
1. 第二跳遍历关系类型限定为 `DEFINITION_OF`，遗漏 `REFERENCED_IN` 关系
2. `COALESCE(neighbor.id, ...)` 未处理 `doc_id` 主键
3. LLM 生成时仅取前 10 条证据，Documents 排在第 12 名后被截断

**修复**：
- `get_l2_neighbors()` 替代 `get_l3_by_l2_ids()`，不限关系类型
- `COALESCE(neighbor.id, neighbor.doc_id, neighbor.term_id)` 统一主键
- `evidence[:10]` → `evidence[:20]` 增加 LLM 证据量

### 向量语义搜索引入

**新增能力**：使用 DashScope `text-embedding-v4` 模型生成 1536 维嵌入向量，创建 Neo4j VECTOR INDEX（`doc_embedding_idx`，COSINE 相似度）。

**涉及文件**：
- `src/kg/client.py` — `compute_embedding()` DashScope API 适配
- `src/kg/client.py` — `search_documents_vector()` Neo4j 原生向量检索
- `src/kg/client.py` — `build_document_embeddings()` 批量 embedding 构建
- `src/graphrag/retriever.py` — 向量搜索优先策略
- `.env` — 新增 `DASHSCOPE_API_KEY`

### 历史遗留 Bug 修复

| 文件 | 问题 | 修复 |
|------|------|------|
| `client.py` | Neo4j Relationship 被误判为 tuple | `.start_node`/`.end_node`/`.type` 属性访问 |
| `client.py` | 节点标签不匹配 | 统一使用 `|` 多标签匹配 |
| `client.py` | 起始节点排除 Document/Term | 起始标签扩大覆盖 |

### 性能提升

| 指标 | V1.25 | V1.3 |
|------|-------|------|
| 跨层节点发现 | L3_Term 仅 3-5 个 | L3_Term + L2_Document 共 15+ 个 |
| 文档检索 | 关键词 CONTAINS | 语义向量搜索 (COSINE) |
| LLM 证据量 | 前 10 条 | 前 20 条 |
| 国标标准回答 | "无法确定" | 正确引用 GBT+34015.3 |

---

## V1.25 — 并行拆卸逻辑修复 + 拓扑排序甘特图

**发布日期**: 2026-05-14 | **标签**: `v1.25-parallel-disassembly-fix`

### 并行拆卸逻辑修复

- **生成器提示词优化**：`generator.py` 添加并行拆卸规则到 LLM Prompt
- **并行规则准确度提升**：改进拆卸规则判断逻辑，确保同一并行批次的操作物理上可同时执行
- **步骤 ID 字段修复**：拓扑排序结果中为每步添加 `id` 字段，确保前端渲染稳定

### 甘特图可视化

- **甘特图组件**：自定义甘特图组件，支持并行批次和时间轴展示
- **并行组标签**：为每步添加并行组标签，直观显示哪些步骤可并行执行
- **颜色方案优化**：去除批量背景色，采用更清晰的单色层级设计

### 依赖图修复

| 修复 | 描述 |
|------|------|
| `cycle_detector.py` | 修正图构建中的边方向错误 |
| `planner.py` | 修正 `dep_map` 方向与关系解析逻辑 |

---

## V1.24 — 并行拆卸修复 + 甘特图批次可视化

**发布日期**: 2026-05-14 | **标签**: `v1.24-parallel-batch-visualization`

- 甘特图批次可视化：支持按并行批次着色
- 拆卸序列并行批次分组算法优化
- 前端甘特图组件与后端数据对接

---

## V1.23 — 拓扑排序依赖标准化 + LLM时间合并

**发布日期**: 2026-05-14 | **标签**: `v1.23-topo-deps-standardize`

### 依赖标准化

- **组件 ID 归一化**：`SequencePlanner` 将依赖引用统一归一化为组件 ID 格式
- **时间估算差异化**：`TimeEstimator` 根据组件属性（重量、连接类型、操作类型）差异化估算时间
- **重复节点去重**：增加日志和去重逻辑，消除因数据重复导致的序列异常

### 新增文件

- `verify_safety.py` 安全验证脚本

### 问题修复

- `SequencePlanner` 组件计数追踪及其日志增强
- 前端 TypeScript 未使用属性错误修复

---

## V1.22 — 拓扑排序自环Bug修复 + 版本更新

**发布日期**: 2026-05-14 | **标签**: `v1.22-topo-self-loop-fix`

- 修复拓扑排序中自环（self-loop）导致的死循环问题
- 改进环路检测算法对自环的特殊处理
- 系统版本更新机制建立

---

## V1.21 — 前端展示优化 + 拓扑排序Bug修复

**发布日期**: 2026-05-14 | **标签**: `v1.21-frontend-optimization`

### 前端增强

- **双序列展示**：`SequencePlanner` 新增拓扑排序 + LLM 结果双列对比展示
- **StepCard 组件**：独立的步骤卡片组件，支持安全等级、工具需求、时间展示
- **SequenceSection 组件**：序列分区展示，按并行批次分组
- **MarkdownRenderer**：通用 Markdown 渲染组件，支持证据链接化
- **CollapsibleSource**：可折叠的来源证据面板
- **页面转场动画**：`page-transition` 动画效果

### 后端修复

- `cycle_detector.py` 环路检测算法优化
- `planner.py` 依赖图构建逻辑修正

---

## V1.2 — Bug修复 + OneAPI配置 + LLM推理反馈增强

**发布日期**: 2026-05-14 | **标签**: `v1.2-bugfix-oneapi-feedback`

### LLM推理反馈增强 (Phase 1-4)

实施了四阶段推理反馈增强：

- **Phase 1**: 置信度评分从加权求和改为层次化门控（hierarchical gates）
- **Phase 2**: 覆盖度分布日志记录，支持数据驱动的阈值调优
- **Phase 3**: 结构化推理链设计（`ReasoningLink` + `StepReasoningChain`）
- **Phase 4**: 动态深度混合策略（dynamic depth hybrid approach）

### OneAPI 配置

- 集成 OneAPI 作为 OpenAI 兼容接口的统一代理
- 支持多模型路由和负载均衡

### MAX_TOKENS 调优

- 根据各模块实际需求差异化配置 MAX_TOKENS
- 减少不必要的 token 消耗，降低 API 调用成本

### 前端增强

- **页面转场动画**：过渡动画效果
- **仪表盘 EV 主题**：更新 Dashboard 卡片、侧边栏、甘特图颜色适配深色 EV 主题
- **CSS 变量体系**：统一的深色主题 CSS 变量

### 测试

- 新增 `batch_scorer` Neo4j 上下文增强测试
- 新增三元组提取稳定性和关系类型测试

---

## V1.0 — 三层知识图谱跨层连接 + 基础系统

**发布日期**: 2026-05-08

### 核心架构

- **三层知识图谱**：`L1 Component` / `L2 Document+Entity` / `L3 Term` 分层存储
- **跨层连接系统**：
  - `CrossLayerBatchBuilder` — 批量处理 L2→L3 连接
  - `entity_extractor.py` — LLM 提取 L2/L3 实体和术语
  - 别名词典 — 归一化映射、优先级匹配、停用词过滤
- **跨层关系类型**：`REFERENCE_OF` (L1→L2)、`DEFINITION_OF` (L2→L3)、`CONSTRAINED_BY` (L1→L3)

### GraphRAG 增强检索

- **查询重写**：`QueryRewriter` 同义词/上下位词扩展
- **多路径检索**：`MultiPathRetriever` Component/Document/Term 三路并行
- **证据排序**：`Ranker` 文本相似度 + 图中心性 + 新鲜度多维排序
- **约束感知检索**：`ConstrainedRetriever` 结构有效性优先
- **跨层检索器**：`CrossLayerRetriever` 跨层推理链路
- **迭代补充**：`FeedbackLoop` 自动检测缺失证据并补充

### 拆卸序列规划

- **环路检测**：Tarjan 强连通分量算法 + 智能环拆分
- **拓扑排序**：Kahn 算法生成有效拆卸序列
- **孤立节点解析**：`IsolatedNodeResolver` Levenshtein 相似度匹配
- **时间估算**：MTM 方法 + LLM 辅助时间调整
- **并行分组**：并行批次划分

### 人机协作分配

- **LLM 九因素实时打分**：安全性、可达性、精度等 9 维综合评估
- **AS 自动化评分**：规则化自动化适宜性计算
- **批量评分优化**：`BatchScorer` 上下文增强评分

### 混合图输出

- **Mermaid 流程图**：自动生成拆卸序列图
- **JSON 结构化输出**：标准化机器可解析格式

### 数据导入

- **PyMuPDF 解析**：PDF 文档自动解析
- **路径分类**：文档章节自动分类
- **LLM 实体提取**：从文本提取结构化实体和术语

### API 端点

- 拆卸规划、图谱查询、自然语言问答、数据导入、管理维护
- SSE 流式推送、FastAPI 自动文档

### 前端界面

- 6 大页面：仪表盘、图谱浏览、推理查询、序列规划、导入管理、参数设置
- 交互式力导向图、甘特图可视化
- Docker 容器化部署

---

## 详细版本报告

各版本的详细变更报告存放在以下文件中：

| 版本 | 文件 |
|------|------|
| V1.5 | `v1.5版本迭代报告.md` |
| V1.4 | `V1.4版本迭代报告.md` |
| V1.3 | `v1.3版本迭代报告.md` |
| V1.21 | `V1.21版本迭代报告.md` |
| V1.2 | `V1.2版本迭代报告.md` |
| 设计文档 | `docs/superpowers/specs/*.md` |
| 实现计划 | `docs/superpowers/plans/*.md` |
