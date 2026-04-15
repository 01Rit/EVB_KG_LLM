# 阶段3：可视化界面与参数管理 实现计划

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 构建React前端可视化界面，支持知识图谱查看、拆卸序列可视化、参数动态调整、文件导入管理

**Architecture:** React + Vite前端 + FastAPI后端扩展 + Neo4j图数据库 + Docker容器化部署

**Tech Stack:** React 18, Vite, TypeScript, react-force-graph-2d, reactflow, FastAPI, Neo4j, Docker

---

## 文件结构

```
frontend/
├── public/
│   └── favicon.ico
├── src/
│   ├── main.tsx
│   ├── App.tsx
│   ├── index.css
│   ├── api/
│   │   └── client.ts
│   ├── components/
│   │   ├── Layout/
│   │   │   ├── Layout.tsx
│   │   │   └── Sidebar.tsx
│   │   ├── GraphView/
│   │   │   ├── GraphView.tsx
│   │   │   └── NodeDetail.tsx
│   │   ├── SequenceView/
│   │   │   ├── FlowView.tsx
│   │   │   └── TimelineView.tsx
│   │   ├── FileImporter/
│   │   │   ├── L1Importer.tsx
│   │   │   ├── L2Importer.tsx
│   │   │   └── L3Importer.tsx
│   │   ├── ParamEditor/
│   │   │   └── ParamEditor.tsx
│   │   └── QueryPanel/
│   │       ├── QueryPanel.tsx
│   │       ├── TraceViewer.tsx
│   │       └── EvidenceList.tsx
│   ├── pages/
│   │   ├── Dashboard.tsx
│   │   ├── GraphExplorer.tsx
│   │   ├── QueryPage.tsx
│   │   ├── SequencePlanner.tsx
│   │   ├── ImportManager.tsx
│   │   └── Settings.tsx
│   ├── hooks/
│   │   ├── useGraph.ts
│   │   ├── useSequence.ts
│   │   ├── useConfig.ts
│   │   └── useQuery.ts
│   ├── types/
│   │   └── index.ts
│   └── utils/
│       └── formatters.ts
├── index.html
├── package.json
├── tsconfig.json
├── vite.config.ts
└── Dockerfile

backend/
├── src/
│   └── api/
│       ├── graph_routes.py
│       ├── query_routes.py
│       ├── import_routes.py
│       └── config_routes.py
├── config.yaml
└── Dockerfile
```

---

### Task 1: 前端项目初始化

**Files:**
- Create: `frontend/package.json`
- Create: `frontend/tsconfig.json`
- Create: `frontend/vite.config.ts`
- Create: `frontend/index.html`
- Create: `frontend/src/main.tsx`
- Create: `frontend/Dockerfile`

- [ ] **Step 1: 创建 frontend/package.json**

```json
{
  "name": "battery-kg-frontend",
  "private": true,
  "version": "1.0.0",
  "type": "module",
  "scripts": {
    "dev": "vite",
    "build": "tsc && vite build",
    "preview": "vite preview"
  },
  "dependencies": {
    "react": "^18.2.0",
    "react-dom": "^18.2.0",
    "react-router-dom": "^6.22.0",
    "react-force-graph-2d": "^1.25.0",
    "@xyflow/react": "^10.3.0",
    "axios": "^1.6.7",
    "@tanstack/react-query": "^5.24.0"
  },
  "devDependencies": {
    "@types/react": "^18.2.55",
    "@types/react-dom": "^18.2.19",
    "@vitejs/plugin-react": "^4.2.1",
    "typescript": "^5.3.3",
    "vite": "^5.1.0"
  }
}
```

- [ ] **Step 2: 创建 frontend/tsconfig.json**

```json
{
  "compilerOptions": {
    "target": "ES2020",
    "useDefineForClassFields": true,
    "lib": ["ES2020", "DOM", "DOM.Iterable"],
    "module": "ESNext",
    "skipLibCheck": true,
    "moduleResolution": "bundler",
    "allowImportingTsExtensions": true,
    "resolveJsonModule": true,
    "isolatedModules": true,
    "noEmit": true,
    "jsx": "react-jsx",
    "strict": true,
    "noUnusedLocals": true,
    "noUnusedParameters": true,
    "noFallthroughCasesInSwitch": true
  },
  "include": ["src"],
  "references": [{ "path": "./tsconfig.node.json" }]
}
```

- [ ] **Step 3: 创建 frontend/vite.config.ts**

```typescript
import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

export default defineConfig({
  plugins: [react()],
  server: {
    port: 3000,
    proxy: {
      '/api': {
        target: 'http://backend:8000',
        changeOrigin: true,
      },
    },
  },
})
```

- [ ] **Step 4: 创建 frontend/index.html**

```html
<!DOCTYPE html>
<html lang="zh-CN">
  <head>
    <meta charset="UTF-8" />
    <link rel="icon" type="image/svg+xml" href="/vite.svg" />
    <meta name="viewport" content="width=device-width, initial-scale=1.0" />
    <title>动力电池拆卸知识图谱系统</title>
  </head>
  <body>
    <div id="root"></div>
    <script type="module" src="/src/main.tsx"></script>
  </body>
</html>
```

- [ ] **Step 5: 创建 frontend/src/main.tsx**

```tsx
import React from 'react'
import ReactDOM from 'react-dom/client'
import App from './App'
import './index.css'

ReactDOM.createRoot(document.getElementById('root')!).render(
  <React.StrictMode>
    <App />
  </React.StrictMode>,
)
```

- [ ] **Step 6: 创建 frontend/Dockerfile**

```dockerfile
FROM node:20-alpine AS builder
WORKDIR /app
COPY package*.json ./
RUN npm install
COPY . .
RUN npm run build

FROM nginx:alpine
COPY --from=builder /app/dist /usr/share/nginx/html
EXPOSE 3000
CMD ["nginx", "-g", "daemon off;"]
```

- [ ] **Step 7: 安装依赖并验证**

```bash
cd frontend
npm install
npm run build
```

- [ ] **Step 8: Commit**

```bash
git add frontend/package.json frontend/tsconfig.json frontend/vite.config.ts frontend/index.html frontend/src/main.tsx frontend/Dockerfile
git commit -m "feat(phase3): add frontend project scaffolding"
```

---

### Task 2: 基础组件 - 布局与导航

**Files:**
- Create: `frontend/src/App.tsx`
- Create: `frontend/src/index.css`
- Create: `frontend/src/components/Layout/Layout.tsx`
- Create: `frontend/src/components/Layout/Sidebar.tsx`

- [ ] **Step 1: 创建 frontend/src/index.css**

```css
* {
  margin: 0;
  padding: 0;
  box-sizing: border-box;
}

body {
  font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Oxygen, Ubuntu, Cantarell, sans-serif;
  background-color: #f5f5f5;
}

.app-container {
  display: flex;
  min-height: 100vh;
}

.sidebar {
  width: 240px;
  background-color: #1a1a2e;
  color: white;
  padding: 20px;
}

.sidebar-logo {
  font-size: 18px;
  font-weight: bold;
  margin-bottom: 30px;
  padding: 10px;
}

.sidebar-nav {
  list-style: none;
}

.sidebar-nav-item {
  padding: 12px 15px;
  margin-bottom: 5px;
  border-radius: 8px;
  cursor: pointer;
  transition: background-color 0.2s;
}

.sidebar-nav-item:hover {
  background-color: #16213e;
}

.sidebar-nav-item.active {
  background-color: #0f3460;
}

.main-content {
  flex: 1;
  padding: 20px;
}

.page-header {
  font-size: 24px;
  font-weight: bold;
  margin-bottom: 20px;
}

.card {
  background: white;
  border-radius: 8px;
  padding: 20px;
  margin-bottom: 20px;
  box-shadow: 0 2px 4px rgba(0,0,0,0.1);
}
```

- [ ] **Step 2: 创建 frontend/src/components/Layout/Sidebar.tsx**

```tsx
import { Link, useLocation } from 'react-router-dom'

const navItems = [
  { path: '/', label: '仪表盘' },
  { path: '/graph', label: '图谱浏览' },
  { path: '/query', label: '推理查询' },
  { path: '/sequence', label: '序列规划' },
  { path: '/import', label: '导入管理' },
  { path: '/settings', label: '参数设置' },
]

export function Sidebar() {
  const location = useLocation()

  return (
    <aside className="sidebar">
      <div className="sidebar-logo">电池拆卸系统</div>
      <ul className="sidebar-nav">
        {navItems.map((item) => (
          <li
            key={item.path}
            className={`sidebar-nav-item ${location.pathname === item.path ? 'active' : ''}`}
          >
            <Link to={item.path} style={{ color: 'inherit', textDecoration: 'none' }}>
              {item.label}
            </Link>
          </li>
        ))}
      </ul>
    </aside>
  )
}
```

- [ ] **Step 3: 创建 frontend/src/components/Layout/Layout.tsx**

```tsx
import { Outlet } from 'react-router-dom'
import { Sidebar } from './Sidebar'

export function Layout() {
  return (
    <div className="app-container">
      <Sidebar />
      <main className="main-content">
        <Outlet />
      </main>
    </div>
  )
}
```

- [ ] **Step 4: 创建 frontend/src/App.tsx**

```tsx
import { BrowserRouter, Routes, Route } from 'react-router-dom'
import { Layout } from './components/Layout/Layout'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'

const queryClient = new QueryClient()

export default function App() {
  return (
    <QueryClientProvider client={queryClient}>
      <BrowserRouter>
        <Routes>
          <Route path="/" element={<Layout />}>
            <Route index element={<div>仪表盘</div>} />
            <Route path="graph" element={<div>图谱浏览</div>} />
            <Route path="query" element={<div>推理查询</div>} />
            <Route path="sequence" element={<div>序列规划</div>} />
            <Route path="import" element={<div>导入管理</div>} />
            <Route path="settings" element={<div>参数设置</div>} />
          </Route>
        </Routes>
      </BrowserRouter>
    </QueryClientProvider>
  )
}
```

- [ ] **Step 5: Commit**

```bash
git add frontend/src/App.tsx frontend/src/index.css frontend/src/components/Layout/
git commit -m "feat(phase3): add layout and navigation components"
```

---

### Task 3: API客户端

**Files:**
- Create: `frontend/src/api/client.ts`
- Create: `frontend/src/types/index.ts`

- [ ] **Step 1: 创建 frontend/src/types/index.ts**

```typescript
export interface GraphNode {
  id: string
  name: string
  type: 'L1' | 'L2' | 'L3'
  properties: Record<string, any>
}

export interface GraphEdge {
  from: string
  to: string
  type: string
}

export interface QueryRequest {
  battery_model: string
  context: string[]
  debug: boolean
}

export interface QueryResponse {
  code: number
  message: string
  data: {
    steps: DisassemblyStep[]
    trace?: QueryTrace
  }
}

export interface DisassemblyStep {
  id: number
  component: string
  action: string
  tool: string[]
  evidence: string[]
  confidence: number
  safety_level: number
}

export interface QueryTrace {
  rewritten_queries: string[]
  retrieval_paths: string[]
  evidence_count: number
  iteration_count: number
  timing: Record<string, number>
}

export interface SequenceResponse {
  battery_model: string
  steps: SequenceStep[]
  parallel_groups: string[][]
  total_time_seconds: number
  cycle_count: number
}

export interface SequenceStep {
  step: number
  component: string
  component_name: string
  time_seconds: number
  tool_required: string[]
  safety_level: number
  assignee?: 'human' | 'robot'
}

export interface Config {
  mtm: {
    tool_switch_default: number
    position_default: number
    mtm_base_seconds: number
  }
  as: {
    h_weights: number[]
    s_weights: number[]
  }
  threshold: {
    robot_threshold: number
    human_threshold: number
  }
  cost: {
    cost_decision_enabled: boolean
    robot_cost_default: number
    human_cost_default: number
    loss_cost_enabled: boolean
  }
  parallel: {
    parallel_level: number
  }
  time_coefficient: number
  llm: {
    temperature: number
    max_tokens: number
  }
  rag: {
    top_k: number
    similarity_threshold: number
    retrieval_depth: number
  }
}
```

- [ ] **Step 2: 创建 frontend/src/api/client.ts**

```typescript
import axios from 'axios'
import type {
  QueryRequest,
  QueryResponse,
  SequenceResponse,
  Config,
  GraphNode,
  GraphEdge,
} from '../types'

const api = axios.create({
  baseURL: '/api/v1',
  timeout: 30000,
})

export const graphApi = {
  getNodes: () => api.get<GraphNode[]>('/graph/nodes'),
  getNode: (id: string) => api.get(`/graph/node/${id}`),
  getRelationships: () => api.get<GraphEdge[]>('/graph/relationships'),
  search: (q: string) => api.get('/graph/search', { params: { q } }),
}

export const queryApi = {
  ask: (data: QueryRequest) => api.post<QueryResponse>('/disassembly/plan', data),
  getHistory: (limit = 10) => api.get('/query/history', { params: { limit } }),
}

export const sequenceApi = {
  getSequence: (batteryModel: string) =>
    api.get<SequenceResponse>(`/disassembly/sequence/${batteryModel}`),
}

export const configApi = {
  getAll: () => api.get<Config>('/config'),
  update: (category: string, data: any) =>
    api.put(`/config/${category}`, data),
  validate: () => api.get('/config/validate'),
  reload: () => api.post('/config/reload'),
}

export const importApi = {
  importL1Manual: (data: any) => api.post('/import/l1/manual', data),
  importL1Csv: (formData: FormData) =>
    api.post('/import/l1/csv', formData, {
      headers: { 'Content-Type': 'multipart/form-data' },
    }),
  importL1Txt: (formData: FormData) =>
    api.post('/import/l1/txt', formData, {
      headers: { 'Content-Type': 'multipart/form-data' },
    }),
  importL1Pdf: (formData: FormData) =>
    api.post('/import/l1/pdf', formData, {
      headers: { 'Content-Type': 'multipart/form-data' },
    }),
  importL2: (formData: FormData) =>
    api.post('/import/l2', formData, {
      headers: { 'Content-Type': 'multipart/form-data' },
    }),
  importL3: (data: any) => api.post('/import/l3', data),
  getStatus: () => api.get('/import/status'),
}

export default api
```

- [ ] **Step 3: Commit**

```bash
git add frontend/src/api/client.ts frontend/src/types/index.ts
git commit -m "feat(phase3): add API client and types"
```

---

### Task 4: 后端API扩展 - 图谱路由

**Files:**
- Create: `src/api/graph_routes.py`
- Modify: `src/main.py`

- [ ] **Step 1: 创建 src/api/graph_routes.py**

```python
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import List, Dict, Any, Optional

router = APIRouter()


class GraphNodeResponse(BaseModel):
    id: str
    name: str
    type: str
    properties: Dict[str, Any]


class GraphEdgeResponse(BaseModel):
    from_: str
    to: str
    type: str

    class Config:
        populate_by_name = True


@router.get('/graph/nodes', response_model=List[GraphNodeResponse])
async def get_nodes():
    from src.kg.client import Neo4jClient
    from src.config import settings

    neo4j = Neo4jClient(settings.neo4j_uri, settings.neo4j_user, settings.neo4j_password)

    cypher = '''
    MATCH (n)
    WHERE n:Component OR n:Document OR n:Term
    RETURN n.id as id,
           COALESCE(n.name, n.title, n.term_id) as name,
           labels(n)[0] as type,
           properties(n) as properties
    LIMIT 500
    '''

    results = neo4j.execute_query(cypher)

    nodes = []
    for r in results:
        node_type = r.get('type', 'Unknown')
        if node_type == 'Component':
            display_type = 'L1'
        elif node_type == 'Document':
            display_type = 'L2'
        else:
            display_type = 'L3'

        nodes.append(GraphNodeResponse(
            id=r.get('id', ''),
            name=r.get('name', ''),
            type=display_type,
            properties=r.get('properties', {})
        ))

    neo4j.close()
    return nodes


@router.get('/graph/node/{node_id}', response_model=GraphNodeResponse)
async def get_node(node_id: str):
    from src.kg.client import Neo4jClient
    from src.config import settings

    neo4j = Neo4jClient(settings.neo4j_uri, settings.neo4j_user, settings.neo4j_password)

    cypher = '''
    MATCH (n)
    WHERE n.id = $node_id OR n.name = $node_id
    RETURN n.id as id,
           COALESCE(n.name, n.title, n.term_id) as name,
           labels(n)[0] as type,
           properties(n) as properties
    LIMIT 1
    '''

    results = neo4j.execute_query(cypher, {'node_id': node_id})

    if not results:
        neo4j.close()
        raise HTTPException(status_code=404, detail='Node not found')

    r = results[0]
    node_type = r.get('type', 'Unknown')

    neo4j.close()

    return GraphNodeResponse(
        id=r.get('id', ''),
        name=r.get('name', ''),
        type=node_type,
        properties=r.get('properties', {})
    )


@router.get('/graph/relationships', response_model=List[GraphEdgeResponse])
async def get_relationships():
    from src.kg.client import Neo4jClient
    from src.config import settings

    neo4j = Neo4jClient(settings.neo4j_uri, settings.neo4j_user, settings.neo4j_password)

    cypher = '''
    MATCH (a)-[r]->(b)
    WHERE a:Component OR a:Document OR a:Term
    RETURN a.id as from_id, b.id as to_id, type(r) as type
    LIMIT 1000
    '''

    results = neo4j.execute_query(cypher)

    edges = []
    for r in results:
        edges.append(GraphEdgeResponse(
            from_=r.get('from_id', ''),
            to=r.get('to_id', ''),
            type=r.get('type', '')
        ))

    neo4j.close()
    return edges


@router.get('/graph/search')
async def search_nodes(q: str, node_type: Optional[str] = None):
    from src.kg.client import Neo4jClient
    from src.config import settings

    neo4j = Neo4jClient(settings.neo4j_uri, settings.neo4j_user, settings.neo4j_password)

    if node_type:
        label = node_type
    else:
        label = 'Component'

    cypher = f'''
    MATCH (n:{label})
    WHERE n.name CONTAINS $q OR n.id CONTAINS $q
    RETURN n.id as id, n.name as name, '{label}' as type, properties(n) as properties
    LIMIT 50
    '''

    results = neo4j.execute_query(cypher, {'q': q})

    nodes = []
    for r in results:
        nodes.append(GraphNodeResponse(
            id=r.get('id', ''),
            name=r.get('name', ''),
            type=label,
            properties=r.get('properties', {})
        ))

    neo4j.close()
    return nodes
```

- [ ] **Step 2: 更新 src/main.py**

```python
from fastapi import FastAPI
from src.api.routes import router
from src.api.middleware import logging_middleware
from src.api.admin_routes import router as admin_router
from src.api.graph_routes import router as graph_router
from src.logs import logger

app = FastAPI(title='动力电池拆卸知识图谱推理系统', version='1.0.0')

app.middleware('http')(logging_middleware)

app.include_router(router)
app.include_router(admin_router, prefix='/admin')
app.include_router(graph_router, prefix='/api/v1')


@app.on_event('shutdown')
async def shutdown_event():
    logger.info('Shutting down application')


if __name__ == '__main__':
    import uvicorn
    uvicorn.run(app, host='0.0.0.0', port=8000)
```

- [ ] **Step 3: Commit**

```bash
git add src/api/graph_routes.py src/main.py
git commit -m "feat(phase3): add graph API routes"
```

---

### Task 5: 后端API扩展 - 查询与配置路由

**Files:**
- Create: `src/api/query_routes.py`
- Create: `src/api/config_routes.py`
- Create: `config.yaml`

- [ ] **Step 1: 创建 src/api/query_routes.py**

```python
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import List, Dict, Any, Optional

router = APIRouter()


class QueryHistoryItem(BaseModel):
    id: str
    battery_model: str
    context: List[str]
    result_summary: str
    created_at: str


@router.post('/disassembly/plan')
async def create_plan(
    battery_model: str,
    context: List[str] = [],
    debug: bool = False
):
    from src.graphrag.planner import Planner
    from src.kg.client import Neo4jClient
    from src.utils.llm_client import LLMClient
    from src.config import settings

    neo4j = Neo4jClient(settings.neo4j_uri, settings.neo4j_user, settings.neo4j_password)
    llm = LLMClient(settings.openai_api_key, settings.openai_base_url)

    from src.graphrag.retriever import MultiPathRetriever

    retriever = MultiPathRetriever(neo4j, None)
    planner = Planner(llm, retriever)

    result = await planner.plan(
        query=f"拆卸{battery_model}型号电池",
        battery_model=battery_model,
        context=context,
        debug=debug
    )

    neo4j.close()
    return result


@router.get('/query/history')
async def get_history(limit: int = 10):
    return []


@router.get('/query/history/{limit}')
async def get_history_by_limit(limit: int):
    return []
```

- [ ] **Step 2: 创建 src/api/config_routes.py**

```python
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Dict, Any, List
import yaml
import os

router = APIRouter()

CONFIG_PATH = os.environ.get('CONFIG_PATH', 'config.yaml')


def load_config() -> Dict[str, Any]:
    if os.path.exists(CONFIG_PATH):
        with open(CONFIG_PATH, 'r', encoding='utf-8') as f:
            return yaml.safe_load(f) or {}
    return get_default_config()


def save_config(config: Dict[str, Any]):
    with open(CONFIG_PATH, 'w', encoding='utf-8') as f:
        yaml.dump(config, f, allow_unicode=True)


def get_default_config() -> Dict[str, Any]:
    return {
        'mtm': {
            'tool_switch_default': 5,
            'position_default': 15,
            'mtm_base_seconds': 85
        },
        'as': {
            'h_weights': [0.2, 0.2, 0.2, 0.2, 0.2],
            's_weights': [0.25, 0.25, 0.25, 0.25]
        },
        'threshold': {
            'robot_threshold': 0.6,
            'human_threshold': 0.4
        },
        'cost': {
            'cost_decision_enabled': True,
            'robot_cost_default': 100.0,
            'human_cost_default': 80.0,
            'loss_cost_enabled': True
        },
        'parallel': {
            'parallel_level': 0
        },
        'time_coefficient': 1.0,
        'llm': {
            'temperature': 0.1,
            'max_tokens': 2000
        },
        'rag': {
            'top_k': 30,
            'similarity_threshold': 0.72,
            'retrieval_depth': 2
        }
    }


@router.get('/config')
async def get_config():
    config = load_config()
    return config


@router.put('/config/{category}')
async def update_config_category(category: str, data: Dict[str, Any]):
    config = load_config()

    if category not in config:
        raise HTTPException(status_code=400, detail=f'Invalid category: {category}')

    config[category] = data
    save_config(config)

    return {'code': 0, 'message': 'Config updated successfully'}


@router.get('/config/validate')
async def validate_config():
    config = load_config()
    errors = []

    if config.get('threshold', {}).get('robot_threshold', 0) <= \
       config.get('threshold', {}).get('human_threshold', 0):
        errors.append('robot_threshold must be greater than human_threshold')

    if errors:
        raise HTTPException(status_code=400, detail={'errors': errors})

    return {'code': 0, 'message': 'Config is valid'}


@router.post('/config/reload')
async def reload_config():
    config = load_config()
    return {'code': 0, 'message': 'Config reloaded', 'config': config}
```

- [ ] **Step 3: 创建 config.yaml**

```yaml
mtm:
  tool_switch_default: 5
  position_default: 15
  mtm_base_seconds: 85

as:
  h_weights:
    - 0.2
    - 0.2
    - 0.2
    - 0.2
    - 0.2
  s_weights:
    - 0.25
    - 0.25
    - 0.25
    - 0.25

threshold:
  robot_threshold: 0.6
  human_threshold: 0.4

cost:
  cost_decision_enabled: true
  robot_cost_default: 100.0
  human_cost_default: 80.0
  loss_cost_enabled: true

parallel:
  parallel_level: 0

time_coefficient: 1.0

llm:
  temperature: 0.1
  max_tokens: 2000

rag:
  top_k: 30
  similarity_threshold: 0.72
  retrieval_depth: 2
```

- [ ] **Step 4: 更新 src/main.py**

```python
from fastapi import FastAPI
from src.api.routes import router
from src.api.middleware import logging_middleware
from src.api.admin_routes import router as admin_router
from src.api.graph_routes import router as graph_router
from src.api.query_routes import router as query_router
from src.api.config_routes import router as config_router
from src.logs import logger

app = FastAPI(title='动力电池拆卸知识图谱推理系统', version='1.0.0')

app.middleware('http')(logging_middleware)

app.include_router(router)
app.include_router(admin_router, prefix='/admin')
app.include_router(graph_router, prefix='/api/v1')
app.include_router(query_router, prefix='/api/v1')
app.include_router(config_router, prefix='/api/v1')


@app.on_event('shutdown')
async def shutdown_event():
    logger.info('Shutting down application')


if __name__ == '__main__':
    import uvicorn
    uvicorn.run(app, host='0.0.0.0', port=8000)
```

- [ ] **Step 5: Commit**

```bash
git add src/api/query_routes.py src/api/config_routes.py config.yaml src/main.py
git commit -m "feat(phase3): add query and config API routes"
```

---

### Task 6: 后端API扩展 - 导入路由

**Files:**
- Create: `src/api/import_routes.py`
- Modify: `src/main.py`

- [ ] **Step 1: 创建 src/api/import_routes.py**

```python
from fastapi import APIRouter, HTTPException, UploadFile, File
from pydantic import BaseModel
from typing import List, Dict, Any, Optional
import csv
import io
import uuid

router = APIRouter()


class L1ComponentData(BaseModel):
    name: str
    battery_model: str
    tool_required: List[str] = []
    safety_level: int = 1
    precedence: List[str] = []


class ImportStatus(BaseModel):
    total: int
    success: int
    failed: int
    errors: List[str] = []


@router.post('/import/l1/manual')
async def import_l1_manual(data: L1ComponentData):
    from src.kg.client import Neo4jClient
    from src.config import settings

    neo4j = Neo4jClient(settings.neo4j_uri, settings.neo4j_user, settings.neo4j_password)

    cypher = '''
    CREATE (c:Component {
        id: $id,
        name: $name,
        battery_model: $battery_model,
        tool_required: $tool_required,
        safety_level: $safety_level,
        precedence: $precedence,
        source_type: 'manual'
    })
    RETURN c
    '''

    result = neo4j.execute_query(cypher, {
        'id': str(uuid.uuid4()),
        'name': data.name,
        'battery_model': data.battery_model,
        'tool_required': str(data.tool_required),
        'safety_level': data.safety_level,
        'precedence': str(data.precedence)
    })

    neo4j.close()

    return {'code': 0, 'message': 'Component imported successfully'}


@router.post('/import/l1/csv')
async def import_l1_csv(file: UploadFile = File(...)):
    from src.kg.client import Neo4jClient
    from src.config import settings

    content = await file.read()
    decoded_content = content.decode('utf-8')

    reader = csv.DictReader(io.StringIO(decoded_content))
    rows = list(reader)

    neo4j = Neo4jClient(settings.neo4j_uri, settings.neo4j_user, settings.neo4j_password)

    success = 0
    failed = 0
    errors = []

    for i, row in enumerate(rows):
        try:
            name = row.get('name', '').strip()
            battery_model = row.get('battery_model', '').strip()
            tool_str = row.get('tool_required', '')
            safety_level = int(row.get('safety_level', 1))
            precedence_str = row.get('precedence', '')

            tools = [t.strip() for t in tool_str.split(',') if t.strip()]
            precedence = [p.strip() for p in precedence_str.split(',') if p.strip()]

            cypher = '''
            CREATE (c:Component {
                id: $id,
                name: $name,
                battery_model: $battery_model,
                tool_required: $tool_required,
                safety_level: $safety_level,
                precedence: $precedence,
                source_type: 'manual'
            })
            '''

            neo4j.execute_query(cypher, {
                'id': str(uuid.uuid4()),
                'name': name,
                'battery_model': battery_model,
                'tool_required': str(tools),
                'safety_level': safety_level,
                'precedence': str(precedence)
            })

            success += 1

        except Exception as e:
            failed += 1
            errors.append(f'Row {i+1}: {str(e)}')

    neo4j.close()

    return {
        'code': 0,
        'message': f'Import completed',
        'total': len(rows),
        'success': success,
        'failed': failed,
        'errors': errors
    }


@router.post('/import/l1/txt')
async def import_l1_txt(file: UploadFile = File(...)):
    content = await file.read()
    text = content.decode('utf-8')

    components = []
    current = {}

    for line in text.split('\n'):
        line = line.strip()
        if line.startswith('[组件'):
            if current:
                components.append(current)
            current = {}
        elif ':' in line:
            key, value = line.split(':', 1)
            key = key.strip()
            value = value.strip()
            current[key] = value

    if current:
        components.append(current)

    from src.kg.client import Neo4jClient
    from src.config import settings

    neo4j = Neo4jClient(settings.neo4j_uri, settings.neo4j_user, settings.neo4j_password)

    success = 0
    for comp in components:
        try:
            name = comp.get('名称', comp.get('name', ''))
            battery_model = comp.get('型号', comp.get('battery_model', ''))
            tools_str = comp.get('工具', comp.get('tool_required', ''))
            safety_level = int(comp.get('安全等级', comp.get('safety_level', 1)))
            precedence_str = comp.get('依赖', comp.get('precedence', ''))

            tools = [t.strip() for t in tools_str.split(',') if t.strip()]
            precedence = [p.strip() for p in precedence_str.split(';') if p.strip()]

            cypher = '''
            CREATE (c:Component {
                id: $id,
                name: $name,
                battery_model: $battery_model,
                tool_required: $tool_required,
                safety_level: $safety_level,
                precedence: $precedence,
                source_type: 'manual'
            })
            '''

            neo4j.execute_query(cypher, {
                'id': str(uuid.uuid4()),
                'name': name,
                'battery_model': battery_model,
                'tool_required': str(tools),
                'safety_level': safety_level,
                'precedence': str(precedence)
            })

            success += 1

        except Exception as e:
            pass

    neo4j.close()

    return {'code': 0, 'message': f'Imported {success} components'}


@router.post('/import/l1/pdf')
async def import_l1_pdf(file: UploadFile = File(...)):
    content = await file.read()

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
        os.unlink(tmp_path)

    from src.importer.entity_extractor import EntityExtractor
    from src.utils.llm_client import LLMClient
    from src.config import settings

    llm = LLMClient(settings.openai_api_key, settings.openai_base_url)
    extractor = EntityExtractor(llm)

    components = extractor.extract_components(full_text)

    from src.kg.client import Neo4jClient

    neo4j = Neo4jClient(settings.neo4j_uri, settings.neo4j_user, settings.neo4j_password)

    for comp in components:
        cypher = '''
        CREATE (c:Component {
            id: $id,
            name: $name,
            battery_model: $battery_model,
            tool_required: $tool_required,
            safety_level: $safety_level,
            precedence: $precedence,
            source_type: 'pdf_import'
        })
        '''

        neo4j.execute_query(cypher, {
            'id': str(uuid.uuid4()),
            'name': comp.get('name', ''),
            'battery_model': comp.get('category', ''),
            'tool_required': str(comp.get('tools', [])),
            'safety_level': comp.get('safety_level', 1),
            'precedence': str(comp.get('dependencies', []))
        })

    neo4j.close()

    return {'code': 0, 'message': f'Extracted {len(components)} components from PDF'}


@router.post('/import/l2')
async def import_l2(file: UploadFile = File(...)):
    content = await file.read()

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
        os.unlink(tmp_path)

    from src.importer.importer import DataImporter
    from src.kg.client import Neo4jClient
    from src.utils.llm_client import LLMClient
    from src.config import settings

    neo4j = Neo4jClient(settings.neo4j_uri, settings.neo4j_user, settings.neo4j_password)
    llm = LLMClient(settings.openai_api_key, settings.openai_base_url)

    importer = DataImporter(neo4j, llm)

    result = importer.import_pdf(tmp_path)

    neo4j.close()

    return {
        'code': 0,
        'message': f'Document imported',
        'doc_id': result.doc_id,
        'components': result.components,
        'terms': result.terms
    }


@router.post('/import/l3')
async def import_l3(data: Dict[str, Any]):
    from src.kg.client import Neo4jClient
    from src.config import settings

    neo4j = Neo4jClient(settings.neo4j_uri, settings.neo4j_user, settings.neo4j_password)

    terms = data.get('terms', [])

    for term in terms:
        cypher = '''
        CREATE (t:Term {
            term_id: $term_id,
            definition: $definition,
            units: $units,
            source_type: 'manual'
        })
        '''

        neo4j.execute_query(cypher, {
            'term_id': term.get('term_id', ''),
            'definition': term.get('definition', ''),
            'units': term.get('units', '')
        })

    neo4j.close()

    return {'code': 0, 'message': f'Imported {len(terms)} terms'}


@router.get('/import/status')
async def get_import_status():
    from src.kg.client import Neo4jClient
    from src.config import settings

    neo4j = Neo4jClient(settings.neo4j_uri, settings.neo4j_user, settings.neo4j_password)

    cypher_components = 'MATCH (c:Component) RETURN count(c) as count'
    cypher_documents = 'MATCH (d:Document) RETURN count(d) as count'
    cypher_terms = 'MATCH (t:Term) RETURN count(t) as count'

    comp_count = neo4j.execute_query(cypher_components)[0].get('count', 0)
    doc_count = neo4j.execute_query(cypher_documents)[0].get('count', 0)
    term_count = neo4j.execute_query(cypher_terms)[0].get('count', 0)

    neo4j.close()

    return {
        'components': comp_count,
        'documents': doc_count,
        'terms': term_count
    }
```

- [ ] **Step 2: 更新 src/main.py**

```python
from fastapi import FastAPI
from src.api.routes import router
from src.api.middleware import logging_middleware
from src.api.admin_routes import router as admin_router
from src.api.graph_routes import router as graph_router
from src.api.query_routes import router as query_router
from src.api.config_routes import router as config_router
from src.api.import_routes import router as import_router
from src.logs import logger

app = FastAPI(title='动力电池拆卸知识图谱推理系统', version='1.0.0')

app.middleware('http')(logging_middleware)

app.include_router(router)
app.include_router(admin_router, prefix='/admin')
app.include_router(graph_router, prefix='/api/v1')
app.include_router(query_router, prefix='/api/v1')
app.include_router(config_router, prefix='/api/v1')
app.include_router(import_router, prefix='/api/v1')


@app.on_event('shutdown')
async def shutdown_event():
    logger.info('Shutting down application')


if __name__ == '__main__':
    import uvicorn
    uvicorn.run(app, host='0.0.0.0', port=8000)
```

- [ ] **Step 3: Commit**

```bash
git add src/api/import_routes.py src/main.py
git commit -m "feat(phase3): add import API routes"
```

---

### Task 7: 图谱可视化页面

**Files:**
- Create: `frontend/src/pages/GraphExplorer.tsx`
- Create: `frontend/src/components/GraphView/GraphView.tsx`

- [ ] **Step 1: 创建 frontend/src/components/GraphView/GraphView.tsx**

```tsx
import { useEffect, useRef, useState } from 'react'
import ForceGraph2D from 'react-force-graph-2d'
import { graphApi } from '../../api/client'
import type { GraphNode, GraphEdge } from '../../types'

interface GraphViewProps {
  nodes: GraphNode[]
  edges: GraphEdge[]
  onNodeClick?: (node: GraphNode) => void
}

const NODE_COLORS = {
  L1: '#22c55e',
  L2: '#3b82f6',
  L3: '#f97316',
}

export function GraphView({ nodes, edges, onNodeClick }: GraphViewProps) {
  const graphRef = useRef<any>(null)

  const graphData = {
    nodes: nodes.map(n => ({
      ...n,
      color: NODE_COLORS[n.type as keyof typeof NODE_COLORS] || '#999',
    })),
    links: edges.map(e => ({
      source: e.from,
      target: e.to,
    })),
  }

  useEffect(() => {
    if (graphRef.current) {
      graphRef.current.d3Force('charge').strength(-100)
    }
  }, [])

  return (
    <ForceGraph2D
      ref={graphRef}
      graphData={graphData}
      nodeLabel="name"
      nodeColor="color"
      linkColor={() => '#999'}
      linkWidth={1}
      onNodeClick={(node: any) => onNodeClick?.(node as GraphNode)}
    />
  )
}
```

- [ ] **Step 2: 创建 frontend/src/pages/GraphExplorer.tsx**

```tsx
import { useState, useEffect, useCallback } from 'react'
import { graphApi } from '../api/client'
import { GraphView } from '../components/GraphView/GraphView'
import type { GraphNode } from '../types'

export function GraphExplorer() {
  const [nodes, setNodes] = useState<GraphNode[]>([])
  const [edges, setEdges] = useState<any[]>([])
  const [loading, setLoading] = useState(true)
  const [searchQuery, setSearchQuery] = useState('')
  const [filterType, setFilterType] = useState<string>('all')
  const [selectedNode, setSelectedNode] = useState<GraphNode | null>(null)

  const loadGraph = useCallback(async () => {
    setLoading(true)
    try {
      const [nodesRes, edgesRes] = await Promise.all([
        graphApi.getNodes(),
        graphApi.getRelationships(),
      ])
      setNodes(nodesRes.data)
      setEdges(edgesRes.data)
    } catch (error) {
      console.error('Failed to load graph:', error)
    } finally {
      setLoading(false)
    }
  }, [])

  useEffect(() => {
    loadGraph()
  }, [loadGraph])

  const handleSearch = async () => {
    if (!searchQuery.trim()) {
      loadGraph()
      return
    }

    setLoading(true)
    try {
      const res = await graphApi.search(searchQuery)
      setNodes(res.data)
      setEdges([])
    } catch (error) {
      console.error('Search failed:', error)
    } finally {
      setLoading(false)
    }
  }

  const filteredNodes = filterType === 'all'
    ? nodes
    : nodes.filter(n => n.type === filterType)

  return (
    <div>
      <h1 className="page-header">图谱浏览</h1>

      <div className="card">
        <div style={{ display: 'flex', gap: '10px', marginBottom: '20px' }}>
          <input
            type="text"
            placeholder="搜索节点..."
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            onKeyDown={(e) => e.key === 'Enter' && handleSearch()}
            style={{
              flex: 1,
              padding: '10px',
              borderRadius: '8px',
              border: '1px solid #ddd',
            }}
          />
          <button onClick={handleSearch} style={{
            padding: '10px 20px',
            backgroundColor: '#3b82f6',
            color: 'white',
            border: 'none',
            borderRadius: '8px',
            cursor: 'pointer',
          }}>
            搜索
          </button>
          <select
            value={filterType}
            onChange={(e) => setFilterType(e.target.value)}
            style={{
              padding: '10px',
              borderRadius: '8px',
              border: '1px solid #ddd',
            }}
          >
            <option value="all">全部</option>
            <option value="L1">L1 组件</option>
            <option value="L2">L2 文档</option>
            <option value="L3">L3 术语</option>
          </select>
          <button onClick={loadGraph} style={{
            padding: '10px 20px',
            backgroundColor: '#666',
            color: 'white',
            border: 'none',
            borderRadius: '8px',
            cursor: 'pointer',
          }}>
            刷新
          </button>
        </div>

        <div style={{ display: 'flex', gap: '20px' }}>
          <div style={{ flex: 1, height: '500px', backgroundColor: '#f0f0f0', borderRadius: '8px' }}>
            {loading ? (
              <div style={{ padding: '20px', textAlign: 'center' }}>加载中...</div>
            ) : (
              <GraphView
                nodes={filteredNodes}
                edges={edges}
                onNodeClick={setSelectedNode}
              />
            )}
          </div>

          {selectedNode && (
            <div style={{ width: '300px', padding: '20px', backgroundColor: '#f9f9f9', borderRadius: '8px' }}>
              <h3>节点详情</h3>
              <p><strong>ID:</strong> {selectedNode.id}</p>
              <p><strong>名称:</strong> {selectedNode.name}</p>
              <p><strong>类型:</strong> {selectedNode.type}</p>
              <button
                onClick={() => setSelectedNode(null)}
                style={{
                  marginTop: '10px',
                  padding: '5px 10px',
                  backgroundColor: '#666',
                  color: 'white',
                  border: 'none',
                  borderRadius: '4px',
                  cursor: 'pointer',
                }}
              >
                关闭
              </button>
            </div>
          )}
        </div>

        <div style={{ marginTop: '20px', display: 'flex', gap: '20px' }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: '5px' }}>
            <div style={{ width: '12px', height: '12px', backgroundColor: '#22c55e', borderRadius: '2px' }} />
            <span>L1 组件</span>
          </div>
          <div style={{ display: 'flex', alignItems: 'center', gap: '5px' }}>
            <div style={{ width: '12px', height: '12px', backgroundColor: '#3b82f6', borderRadius: '2px' }} />
            <span>L2 文档</span>
          </div>
          <div style={{ display: 'flex', alignItems: 'center', gap: '5px' }}>
            <div style={{ width: '12px', height: '12px', backgroundColor: '#f97316', borderRadius: '2px' }} />
            <span>L3 术语</span>
          </div>
        </div>
      </div>
    </div>
  )
}
```

- [ ] **Step 3: 更新 frontend/src/App.tsx**

```tsx
import { BrowserRouter, Routes, Route } from 'react-router-dom'
import { Layout } from './components/Layout/Layout'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { Dashboard } from './pages/Dashboard'
import { GraphExplorer } from './pages/GraphExplorer'
import { QueryPage } from './pages/QueryPage'
import { SequencePlanner } from './pages/SequencePlanner'
import { ImportManager } from './pages/ImportManager'
import { Settings } from './pages/Settings'

const queryClient = new QueryClient()

export default function App() {
  return (
    <QueryClientProvider client={queryClient}>
      <BrowserRouter>
        <Routes>
          <Route path="/" element={<Layout />}>
            <Route index element={<Dashboard />} />
            <Route path="graph" element={<GraphExplorer />} />
            <Route path="query" element={<QueryPage />} />
            <Route path="sequence" element={<SequencePlanner />} />
            <Route path="import" element={<ImportManager />} />
            <Route path="settings" element={<Settings />} />
          </Route>
        </Routes>
      </BrowserRouter>
    </QueryClientProvider>
  )
}
```

- [ ] **Step 4: 创建占位页面**

```tsx
// frontend/src/pages/Dashboard.tsx
export function Dashboard() {
  return <div className="page-header">仪表盘</div>
}

// frontend/src/pages/QueryPage.tsx
export function QueryPage() {
  return <div className="page-header">推理查询</div>
}

// frontend/src/pages/SequencePlanner.tsx
export function SequencePlanner() {
  return <div className="page-header">序列规划</div>
}

// frontend/src/pages/ImportManager.tsx
export function ImportManager() {
  return <div className="page-header">导入管理</div>
}

// frontend/src/pages/Settings.tsx
export function Settings() {
  return <div className="page-header">参数设置</div>
}
```

- [ ] **Step 5: Commit**

```bash
git add frontend/src/pages/GraphExplorer.tsx frontend/src/components/GraphView/
git commit -m "feat(phase3): add graph explorer page"
```

---

### Task 8: 仪表盘页面

**Files:**
- Create: `frontend/src/pages/Dashboard.tsx`

- [ ] **Step 1: 创建 frontend/src/pages/Dashboard.tsx`

```tsx
import { useState, useEffect } from 'react'
import { useNavigate } from 'react-router-dom'
import { importApi } from '../api/client'

interface Stats {
  components: number
  documents: number
  terms: number
}

export function Dashboard() {
  const [stats, setStats] = useState<Stats>({ components: 0, documents: 0, terms: 0 })
  const [history, setHistory] = useState<any[]>([])
  const navigate = useNavigate()

  useEffect(() => {
    const loadData = async () => {
      try {
        const status = await importApi.getStatus()
        setStats(status.data)
      } catch (error) {
        console.error('Failed to load stats:', error)
      }
    }
    loadData()
  }, [])

  return (
    <div>
      <h1 className="page-header">仪表盘</h1>

      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(3, 1fr)', gap: '20px', marginBottom: '20px' }}>
        <div className="card">
          <h3 style={{ color: '#666', fontSize: '14px' }}>组件数量</h3>
          <p style={{ fontSize: '36px', fontWeight: 'bold', color: '#22c55e' }}>{stats.components}</p>
        </div>
        <div className="card">
          <h3 style={{ color: '#666', fontSize: '14px' }}>文档数量</h3>
          <p style={{ fontSize: '36px', fontWeight: 'bold', color: '#3b82f6' }}>{stats.documents}</p>
        </div>
        <div className="card">
          <h3 style={{ color: '#666', fontSize: '14px' }}>术语数量</h3>
          <p style={{ fontSize: '36px', fontWeight: 'bold', color: '#f97316' }}>{stats.terms}</p>
        </div>
      </div>

      <div className="card">
        <h2 style={{ marginBottom: '20px' }}>最近查询记录</h2>
        {history.length === 0 ? (
          <p style={{ color: '#999' }}>暂无查询记录</p>
        ) : (
          <ul style={{ listStyle: 'none' }}>
            {history.map((item) => (
              <li
                key={item.id}
                onClick={() => navigate('/query', { state: { query: item.query } })}
                style={{
                  padding: '10px',
                  marginBottom: '10px',
                  backgroundColor: '#f5f5f5',
                  borderRadius: '8px',
                  cursor: 'pointer',
                }}
              >
                <strong>{item.battery_model}</strong> - {item.query}
              </li>
            ))}
          </ul>
        )}
      </div>

      <div className="card">
        <h2 style={{ marginBottom: '20px' }}>快速入口</h2>
        <div style={{ display: 'flex', gap: '10px' }}>
          <button
            onClick={() => navigate('/query')}
            style={{
              padding: '15px 30px',
              backgroundColor: '#3b82f6',
              color: 'white',
              border: 'none',
              borderRadius: '8px',
              cursor: 'pointer',
              fontSize: '16px',
            }}
          >
            新建推理查询
          </button>
          <button
            onClick={() => navigate('/import')}
            style={{
              padding: '15px 30px',
              backgroundColor: '#22c55e',
              color: 'white',
              border: 'none',
              borderRadius: '8px',
              cursor: 'pointer',
              fontSize: '16px',
            }}
          >
            导入数据
          </button>
          <button
            onClick={() => navigate('/graph')}
            style={{
              padding: '15px 30px',
              backgroundColor: '#f97316',
              color: 'white',
              border: 'none',
              borderRadius: '8px',
              cursor: 'pointer',
              fontSize: '16px',
            }}
          >
            查看图谱
          </button>
        </div>
      </div>
    </div>
  )
}
```

- [ ] **Step 2: Commit**

```bash
git add frontend/src/pages/Dashboard.tsx
git commit -m "feat(phase3): add dashboard page"
```

---

### Task 9: 推理查询页面

**Files:**
- Create: `frontend/src/pages/QueryPage.tsx`

- [ ] **Step 1: 创建 frontend/src/pages/QueryPage.tsx**

```tsx
import { useState } from 'react'
import { useLocation, useNavigate } from 'react-router-dom'
import { queryApi } from '../api/client'
import type { QueryResponse, DisassemblyStep } from '../types'

const CONTEXT_OPTIONS = [
  '室温环境',
  '低湿度',
  '开阔空间',
  '专业工具齐全',
]

const TEMPLATES = [
  '拆卸 {型号} 型号电池',
  '{型号} 电池的标准拆卸流程',
]

export function QueryPage() {
  const location = useLocation()
  const navigate = useNavigate()

  const [batteryModel, setBatteryModel] = useState('')
  const [context, setContext] = useState<string[]>([])
  const [debug, setDebug] = useState(false)
  const [loading, setLoading] = useState(false)
  const [result, setResult] = useState<QueryResponse | null>(null)

  const handleContextToggle = (option: string) => {
    setContext(prev =>
      prev.includes(option)
        ? prev.filter(c => c !== option)
        : [...prev, option]
    )
  }

  const handleQuery = async () => {
    if (!batteryModel.trim()) return

    setLoading(true)
    try {
      const res = await queryApi.ask({
        battery_model: batteryModel,
        context,
        debug,
      })
      setResult(res.data)
    } catch (error) {
      console.error('Query failed:', error)
    } finally {
      setLoading(false)
    }
  }

  const steps: DisassemblyStep[] = result?.data?.steps || []

  return (
    <div>
      <h1 className="page-header">推理查询</h1>

      <div className="card">
        <div style={{ marginBottom: '20px' }}>
          <label style={{ display: 'block', marginBottom: '10px', fontWeight: 'bold' }}>
            电池型号
          </label>
          <input
            type="text"
            value={batteryModel}
            onChange={(e) => setBatteryModel(e.target.value)}
            placeholder="例如: X123"
            style={{
              width: '100%',
              padding: '10px',
              borderRadius: '8px',
              border: '1px solid #ddd',
              fontSize: '16px',
            }}
          />
        </div>

        <div style={{ marginBottom: '20px' }}>
          <label style={{ display: 'block', marginBottom: '10px', fontWeight: 'bold' }}>
            工作环境（可多选）
          </label>
          <div style={{ display: 'flex', gap: '10px', flexWrap: 'wrap' }}>
            {CONTEXT_OPTIONS.map(option => (
              <label key={option} style={{ display: 'flex', alignItems: 'center', gap: '5px' }}>
                <input
                  type="checkbox"
                  checked={context.includes(option)}
                  onChange={() => handleContextToggle(option)}
                />
                {option}
              </label>
            ))}
          </div>
        </div>

        <div style={{ marginBottom: '20px' }}>
          <label style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
            <input
              type="checkbox"
              checked={debug}
              onChange={(e) => setDebug(e.target.checked)}
            />
            <span>Debug模式（显示推理过程）</span>
          </label>
        </div>

        <button
          onClick={handleQuery}
          disabled={loading || !batteryModel.trim()}
          style={{
            padding: '15px 30px',
            backgroundColor: loading ? '#ccc' : '#3b82f6',
            color: 'white',
            border: 'none',
            borderRadius: '8px',
            cursor: loading ? 'not-allowed' : 'pointer',
            fontSize: '16px',
          }}
        >
          {loading ? '查询中...' : '开始查询'}
        </button>
      </div>

      {result && (
        <div className="card">
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '20px' }}>
            <h2>拆卸方案</h2>
            <button
              onClick={() => {
                const dataStr = JSON.stringify(result, null, 2)
                const blob = new Blob([dataStr], { type: 'application/json' })
                const url = URL.createObjectURL(blob)
                const a = document.createElement('a')
                a.href = url
                a.download = `disassembly_${batteryModel}.json`
                a.click()
              }}
              style={{
                padding: '10px 20px',
                backgroundColor: '#22c55e',
                color: 'white',
                border: 'none',
                borderRadius: '8px',
                cursor: 'pointer',
              }}
            >
              导出结果
            </button>
          </div>

          <div style={{ marginBottom: '20px' }}>
            <h3>拆卸步骤</h3>
            <table style={{ width: '100%', borderCollapse: 'collapse', marginTop: '10px' }}>
              <thead>
                <tr style={{ backgroundColor: '#f5f5f5' }}>
                  <th style={{ padding: '10px', textAlign: 'left' }}>序号</th>
                  <th style={{ padding: '10px', textAlign: 'left' }}>组件</th>
                  <th style={{ padding: '10px', textAlign: 'left' }}>操作</th>
                  <th style={{ padding: '10px', textAlign: 'left' }}>工具</th>
                  <th style={{ padding: '10px', textAlign: 'left' }}>置信度</th>
                </tr>
              </thead>
              <tbody>
                {steps.map((step) => (
                  <tr key={step.id} style={{ borderBottom: '1px solid #eee' }}>
                    <td style={{ padding: '10px' }}>{step.id}</td>
                    <td style={{ padding: '10px' }}>{step.component}</td>
                    <td style={{ padding: '10px' }}>{step.action}</td>
                    <td style={{ padding: '10px' }}>{step.tool?.join(', ') || '-'}</td>
                    <td style={{ padding: '10px' }}>{((step.confidence || 0) * 100).toFixed(0)}%</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>

          {debug && result.data?.trace && (
            <div>
              <h3>推理过程（Debug）</h3>
              <div style={{ backgroundColor: '#f5f5f5', padding: '15px', borderRadius: '8px', marginTop: '10px' }}>
                <p><strong>重写查询:</strong> {result.data.trace.rewritten_queries?.join(', ')}</p>
                <p><strong>检索路径:</strong> {result.data.trace.retrieval_paths?.join(', ')}</p>
                <p><strong>证据数量:</strong> {result.data.trace.evidence_count}</p>
                <p><strong>迭代次数:</strong> {result.data.trace.iteration_count}</p>
              </div>
            </div>
          )}
        </div>
      )}
    </div>
  )
}
```

- [ ] **Step 2: Commit**

```bash
git add frontend/src/pages/QueryPage.tsx
git commit -m "feat(phase3): add query page"
```

---

### Task 10: 参数设置页面

**Files:**
- Create: `frontend/src/pages/Settings.tsx`

- [ ] **Step 1: 创建 frontend/src/pages/Settings.tsx**

```tsx
import { useState, useEffect } from 'react'
import { configApi } from '../api/client'
import type { Config } from '../types'

export function Settings() {
  const [config, setConfig] = useState<Config | null>(null)
  const [loading, setLoading] = useState(true)
  const [saving, setSaving] = useState(false)
  const [message, setMessage] = useState('')

  useEffect(() => {
    const loadConfig = async () => {
      try {
        const res = await configApi.getAll()
        setConfig(res.data)
      } catch (error) {
        console.error('Failed to load config:', error)
      } finally {
        setLoading(false)
      }
    }
    loadConfig()
  }, [])

  const handleSave = async (category: string) => {
    if (!config) return

    setSaving(true)
    try {
      await configApi.update(category, config[category as keyof Config])
      setMessage('保存成功')
      setTimeout(() => setMessage(''), 3000)
    } catch (error) {
      setMessage('保存失败')
    } finally {
      setSaving(false)
    }
  }

  if (loading) return <div>加载中...</div>

  return (
    <div>
      <h1 className="page-header">参数设置</h1>

      {message && (
        <div className="card" style={{ backgroundColor: message.includes('成功') ? '#d4edda' : '#f8d7da' }}>
          {message}
        </div>
      )}

      {config && (
        <>
          <div className="card">
            <h2 style={{ marginBottom: '15px' }}>MTM时间参数</h2>
            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(3, 1fr)', gap: '15px' }}>
              <div>
                <label style={{ display: 'block', marginBottom: '5px' }}>工具切换时间(秒)</label>
                <input
                  type="number"
                  value={config.mtm.tool_switch_default}
                  onChange={(e) => setConfig({
                    ...config,
                    mtm: { ...config.mtm, tool_switch_default: Number(e.target.value) }
                  })}
                  style={{ width: '100%', padding: '8px', borderRadius: '4px', border: '1px solid #ddd' }}
                />
              </div>
              <div>
                <label style={{ display: 'block', marginBottom: '5px' }}>位置转移时间(秒)</label>
                <input
                  type="number"
                  value={config.mtm.position_default}
                  onChange={(e) => setConfig({
                    ...config,
                    mtm: { ...config.mtm, position_default: Number(e.target.value) }
                  })}
                  style={{ width: '100%', padding: '8px', borderRadius: '4px', border: '1px solid #ddd' }}
                />
              </div>
              <div>
                <label style={{ display: 'block', marginBottom: '5px' }}>MTM基准时间(秒)</label>
                <input
                  type="number"
                  value={config.mtm.mtm_base_seconds}
                  onChange={(e) => setConfig({
                    ...config,
                    mtm: { ...config.mtm, mtm_base_seconds: Number(e.target.value) }
                  })}
                  style={{ width: '100%', padding: '8px', borderRadius: '4px', border: '1px solid #ddd' }}
                />
              </div>
            </div>
            <button
              onClick={() => handleSave('mtm')}
              disabled={saving}
              style={{ marginTop: '15px', padding: '8px 20px', backgroundColor: '#3b82f6', color: 'white', border: 'none', borderRadius: '4px', cursor: saving ? 'not-allowed' : 'pointer' }}
            >
              保存MTM参数
            </button>
          </div>

          <div className="card">
            <h2 style={{ marginBottom: '15px' }}>分配阈值</h2>
            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(2, 1fr)', gap: '15px' }}>
              <div>
                <label style={{ display: 'block', marginBottom: '5px' }}>Robot阈值 (AS {">"} ?)</label>
                <input
                  type="number"
                  step="0.1"
                  min="0"
                  max="1"
                  value={config.threshold.robot_threshold}
                  onChange={(e) => setConfig({
                    ...config,
                    threshold: { ...config.threshold, robot_threshold: Number(e.target.value) }
                  })}
                  style={{ width: '100%', padding: '8px', borderRadius: '4px', border: '1px solid #ddd' }}
                />
              </div>
              <div>
                <label style={{ display: 'block', marginBottom: '5px' }}>Human阈值 (AS {"<"} ?)</label>
                <input
                  type="number"
                  step="0.1"
                  min="0"
                  max="1"
                  value={config.threshold.human_threshold}
                  onChange={(e) => setConfig({
                    ...config,
                    threshold: { ...config.threshold, human_threshold: Number(e.target.value) }
                  })}
                  style={{ width: '100%', padding: '8px', borderRadius: '4px', border: '1px solid #ddd' }}
                />
              </div>
            </div>
            <button
              onClick={() => handleSave('threshold')}
              disabled={saving}
              style={{ marginTop: '15px', padding: '8px 20px', backgroundColor: '#3b82f6', color: 'white', border: 'none', borderRadius: '4px', cursor: saving ? 'not-allowed' : 'pointer' }}
            >
              保存阈值参数
            </button>
          </div>

          <div className="card">
            <h2 style={{ marginBottom: '15px' }}>成本决策</h2>
            <div style={{ display: 'flex', flexDirection: 'column', gap: '10px' }}>
              <label style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
                <input
                  type="checkbox"
                  checked={config.cost.cost_decision_enabled}
                  onChange={(e) => setConfig({
                    ...config,
                    cost: { ...config.cost, cost_decision_enabled: e.target.checked }
                  })}
                />
                启用成本差决策
              </label>
              <label style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
                <input
                  type="checkbox"
                  checked={config.cost.loss_cost_enabled}
                  onChange={(e) => setConfig({
                    ...config,
                    cost: { ...config.cost, loss_cost_enabled: e.target.checked }
                  })}
                />
                考虑拆卸损失成本
              </label>
              <div style={{ display: 'grid', gridTemplateColumns: 'repeat(2, 1fr)', gap: '15px', marginTop: '10px' }}>
                <div>
                  <label style={{ display: 'block', marginBottom: '5px' }}>Robot默认成本</label>
                  <input
                    type="number"
                    value={config.cost.robot_cost_default}
                    onChange={(e) => setConfig({
                      ...config,
                      cost: { ...config.cost, robot_cost_default: Number(e.target.value) }
                    })}
                    style={{ width: '100%', padding: '8px', borderRadius: '4px', border: '1px solid #ddd' }}
                  />
                </div>
                <div>
                  <label style={{ display: 'block', marginBottom: '5px' }}>Human默认成本</label>
                  <input
                    type="number"
                    value={config.cost.human_cost_default}
                    onChange={(e) => setConfig({
                      ...config,
                      cost: { ...config.cost, human_cost_default: Number(e.target.value) }
                    })}
                    style={{ width: '100%', padding: '8px', borderRadius: '4px', border: '1px solid #ddd' }}
                  />
                </div>
              </div>
            </div>
            <button
              onClick={() => handleSave('cost')}
              disabled={saving}
              style={{ marginTop: '15px', padding: '8px 20px', backgroundColor: '#3b82f6', color: 'white', border: 'none', borderRadius: '4px', cursor: saving ? 'not-allowed' : 'pointer' }}
            >
              保存成本参数
            </button>
          </div>

          <div className="card">
            <h2 style={{ marginBottom: '15px' }}>并行控制</h2>
            <div>
              <label style={{ display: 'block', marginBottom: '5px' }}>并行拆卸允许程度</label>
              <select
                value={config.parallel.parallel_level}
                onChange={(e) => setConfig({
                  ...config,
                  parallel: { parallel_level: Number(e.target.value) }
                })}
                style={{ width: '100%', padding: '8px', borderRadius: '4px', border: '1px solid #ddd' }}
              >
                <option value={0}>不允许并行拆卸</option>
                <option value={1}>同层无依赖可并行</option>
              </select>
            </div>
            <button
              onClick={() => handleSave('parallel')}
              disabled={saving}
              style={{ marginTop: '15px', padding: '8px 20px', backgroundColor: '#3b82f6', color: 'white', border: 'none', borderRadius: '4px', cursor: saving ? 'not-allowed' : 'pointer' }}
            >
              保存并行参数
            </button>
          </div>

          <div className="card">
            <h2 style={{ marginBottom: '15px' }}>LLM参数</h2>
            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(2, 1fr)', gap: '15px' }}>
              <div>
                <label style={{ display: 'block', marginBottom: '5px' }}>Temperature</label>
                <input
                  type="number"
                  step="0.1"
                  min="0"
                  max="1"
                  value={config.llm.temperature}
                  onChange={(e) => setConfig({
                    ...config,
                    llm: { ...config.llm, temperature: Number(e.target.value) }
                  })}
                  style={{ width: '100%', padding: '8px', borderRadius: '4px', border: '1px solid #ddd' }}
                />
              </div>
              <div>
                <label style={{ display: 'block', marginBottom: '5px' }}>Max Tokens</label>
                <input
                  type="number"
                  value={config.llm.max_tokens}
                  onChange={(e) => setConfig({
                    ...config,
                    llm: { ...config.llm, max_tokens: Number(e.target.value) }
                  })}
                  style={{ width: '100%', padding: '8px', borderRadius: '4px', border: '1px solid #ddd' }}
                />
              </div>
            </div>
            <button
              onClick={() => handleSave('llm')}
              disabled={saving}
              style={{ marginTop: '15px', padding: '8px 20px', backgroundColor: '#3b82f6', color: 'white', border: 'none', borderRadius: '4px', cursor: saving ? 'not-allowed' : 'pointer' }}
            >
              保存LLM参数
            </button>
          </div>

          <div className="card">
            <h2 style={{ marginBottom: '15px' }}>RAG参数</h2>
            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(3, 1fr)', gap: '15px' }}>
              <div>
                <label style={{ display: 'block', marginBottom: '5px' }}>Top K</label>
                <input
                  type="number"
                  value={config.rag.top_k}
                  onChange={(e) => setConfig({
                    ...config,
                    rag: { ...config.rag, top_k: Number(e.target.value) }
                  })}
                  style={{ width: '100%', padding: '8px', borderRadius: '4px', border: '1px solid #ddd' }}
                />
              </div>
              <div>
                <label style={{ display: 'block', marginBottom: '5px' }}>相似度阈值</label>
                <input
                  type="number"
                  step="0.01"
                  min="0"
                  max="1"
                  value={config.rag.similarity_threshold}
                  onChange={(e) => setConfig({
                    ...config,
                    rag: { ...config.rag, similarity_threshold: Number(e.target.value) }
                  })}
                  style={{ width: '100%', padding: '8px', borderRadius: '4px', border: '1px solid #ddd' }}
                />
              </div>
              <div>
                <label style={{ display: 'block', marginBottom: '5px' }}>检索深度</label>
                <input
                  type="number"
                  value={config.rag.retrieval_depth}
                  onChange={(e) => setConfig({
                    ...config,
                    rag: { ...config.rag, retrieval_depth: Number(e.target.value) }
                  })}
                  style={{ width: '100%', padding: '8px', borderRadius: '4px', border: '1px solid #ddd' }}
                />
              </div>
            </div>
            <button
              onClick={() => handleSave('rag')}
              disabled={saving}
              style={{ marginTop: '15px', padding: '8px 20px', backgroundColor: '#3b82f6', color: 'white', border: 'none', borderRadius: '4px', cursor: saving ? 'not-allowed' : 'pointer' }}
            >
              保存RAG参数
            </button>
          </div>
        </>
      )}
    </div>
  )
}
```

- [ ] **Step 2: Commit**

```bash
git add frontend/src/pages/Settings.tsx
git commit -m "feat(phase3): add settings page"
```

---

### Task 11: 导入管理页面

**Files:**
- Create: `frontend/src/pages/ImportManager.tsx`

- [ ] **Step 1: 创建 frontend/src/pages/ImportManager.tsx**

```tsx
import { useState, useRef } from 'react'
import { importApi } from '../api/client'

type Tab = 'l1' | 'l2' | 'l3'

export function ImportManager() {
  const [activeTab, setActiveTab] = useState<Tab>('l1')
  const [uploading, setUploading] = useState(false)
  const [message, setMessage] = useState('')

  const [l1Form, setL1Form] = useState({
    name: '',
    battery_model: '',
    tool_required: '',
    safety_level: 1,
    precedence: '',
  })

  const csvRef = useRef<HTMLInputElement>(null)
  const txtRef = useRef<HTMLInputElement>(null)
  const pdfRef = useRef<HTMLInputElement>(null)

  const handleL1Manual = async () => {
    if (!l1Form.name || !l1Form.battery_model) {
      setMessage('请填写必填字段')
      return
    }

    setUploading(true)
    try {
      await importApi.importL1Manual({
        name: l1Form.name,
        battery_model: l1Form.battery_model,
        tool_required: l1Form.tool_required.split(',').map(t => t.trim()).filter(Boolean),
        safety_level: l1Form.safety_level,
        precedence: l1Form.precedence.split(',').map(p => p.trim()).filter(Boolean),
      })
      setMessage('导入成功')
      setL1Form({ name: '', battery_model: '', tool_required: '', safety_level: 1, precedence: '' })
    } catch (error) {
      setMessage('导入失败')
    } finally {
      setUploading(false)
    }
  }

  const handleCsvUpload = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0]
    if (!file) return

    setUploading(true)
    try {
      const formData = new FormData()
      formData.append('file', file)
      const res = await importApi.importL1Csv(formData)
      setMessage(`成功: ${res.data.success}, 失败: ${res.data.failed}`)
    } catch (error) {
      setMessage('CSV导入失败')
    } finally {
      setUploading(false)
    }
  }

  const handleTxtUpload = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0]
    if (!file) return

    setUploading(true)
    try {
      const formData = new FormData()
      formData.append('file', file)
      const res = await importApi.importL1Txt(formData)
      setMessage(res.data.message)
    } catch (error) {
      setMessage('TXT导入失败')
    } finally {
      setUploading(false)
    }
  }

  const handlePdfUpload = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0]
    if (!file) return

    setUploading(true)
    try {
      const formData = new FormData()
      formData.append('file', file)
      const res = await importApi.importL1Pdf(formData)
      setMessage(res.data.message)
    } catch (error) {
      setMessage('PDF导入失败')
    } finally {
      setUploading(false)
    }
  }

  const handleL2Upload = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0]
    if (!file) return

    setUploading(true)
    try {
      const formData = new FormData()
      formData.append('file', file)
      const res = await importApi.importL2(formData)
      setMessage(`文档已导入，DocID: ${res.data.doc_id}`)
    } catch (error) {
      setMessage('L2导入失败')
    } finally {
      setUploading(false)
    }
  }

  return (
    <div>
      <h1 className="page-header">导入管理</h1>

      {message && (
        <div className="card" style={{ marginBottom: '20px', backgroundColor: message.includes('成功') ? '#d4edda' : '#f8d7da' }}>
          {message}
        </div>
      )}

      <div style={{ display: 'flex', gap: '10px', marginBottom: '20px' }}>
        {(['l1', 'l2', 'l3'] as Tab[]).map(tab => (
          <button
            key={tab}
            onClick={() => setActiveTab(tab)}
            style={{
              padding: '10px 20px',
              backgroundColor: activeTab === tab ? '#3b82f6' : '#666',
              color: 'white',
              border: 'none',
              borderRadius: '8px',
              cursor: 'pointer',
            }}
          >
            {tab === 'l1' ? 'L1组件' : tab === 'l2' ? 'L2文档' : 'L3术语'}
          </button>
        ))}
      </div>

      {activeTab === 'l1' && (
        <div className="card">
          <h2 style={{ marginBottom: '20px' }}>L1组件导入</h2>

          <div style={{ marginBottom: '20px' }}>
            <h3 style={{ marginBottom: '10px' }}>手动输入</h3>
            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(2, 1fr)', gap: '15px' }}>
              <div>
                <label style={{ display: 'block', marginBottom: '5px' }}>组件名称 *</label>
                <input
                  type="text"
                  value={l1Form.name}
                  onChange={(e) => setL1Form({ ...l1Form, name: e.target.value })}
                  style={{ width: '100%', padding: '8px', borderRadius: '4px', border: '1px solid #ddd' }}
                />
              </div>
              <div>
                <label style={{ display: 'block', marginBottom: '5px' }}>电池型号 *</label>
                <input
                  type="text"
                  value={l1Form.battery_model}
                  onChange={(e) => setL1Form({ ...l1Form, battery_model: e.target.value })}
                  style={{ width: '100%', padding: '8px', borderRadius: '4px', border: '1px solid #ddd' }}
                />
              </div>
              <div>
                <label style={{ display: 'block', marginBottom: '5px' }}>所需工具（逗号分隔）</label>
                <input
                  type="text"
                  value={l1Form.tool_required}
                  onChange={(e) => setL1Form({ ...l1Form, tool_required: e.target.value })}
                  placeholder="螺丝刀, 扳手"
                  style={{ width: '100%', padding: '8px', borderRadius: '4px', border: '1px solid #ddd' }}
                />
              </div>
              <div>
                <label style={{ display: 'block', marginBottom: '5px' }}>安全等级</label>
                <input
                  type="number"
                  min="1"
                  max="5"
                  value={l1Form.safety_level}
                  onChange={(e) => setL1Form({ ...l1Form, safety_level: Number(e.target.value) })}
                  style={{ width: '100%', padding: '8px', borderRadius: '4px', border: '1px solid #ddd' }}
                />
              </div>
              <div style={{ gridColumn: '1 / -1' }}>
                <label style={{ display: 'block', marginBottom: '5px' }}>依赖部件（逗号分隔）</label>
                <input
                  type="text"
                  value={l1Form.precedence}
                  onChange={(e) => setL1Form({ ...l1Form, precedence: e.target.value })}
                  placeholder="电池外壳, 支架"
                  style={{ width: '100%', padding: '8px', borderRadius: '4px', border: '1px solid #ddd' }}
                />
              </div>
            </div>
            <button
              onClick={handleL1Manual}
              disabled={uploading}
              style={{ marginTop: '15px', padding: '10px 20px', backgroundColor: '#22c55e', color: 'white', border: 'none', borderRadius: '8px', cursor: uploading ? 'not-allowed' : 'pointer' }}
            >
              导入
            </button>
          </div>

          <div style={{ borderTop: '1px solid #eee', paddingTop: '20px' }}>
            <h3 style={{ marginBottom: '10px' }}>批量导入</h3>
            <div style={{ display: 'flex', gap: '10px' }}>
              <input type="file" ref={csvRef} accept=".csv" onChange={handleCsvUpload} style={{ display: 'none' }} />
              <button
                onClick={() => csvRef.current?.click()}
                disabled={uploading}
                style={{ padding: '10px 20px', backgroundColor: '#3b82f6', color: 'white', border: 'none', borderRadius: '8px', cursor: uploading ? 'not-allowed' : 'pointer' }}
              >
                CSV导入
              </button>

              <input type="file" ref={txtRef} accept=".txt" onChange={handleTxtUpload} style={{ display: 'none' }} />
              <button
                onClick={() => txtRef.current?.click()}
                disabled={uploading}
                style={{ padding: '10px 20px', backgroundColor: '#3b82f6', color: 'white', border: 'none', borderRadius: '8px', cursor: uploading ? 'not-allowed' : 'pointer' }}
              >
                TXT导入
              </button>

              <input type="file" ref={pdfRef} accept=".pdf" onChange={handlePdfUpload} style={{ display: 'none' }} />
              <button
                onClick={() => pdfRef.current?.click()}
                disabled={uploading}
                style={{ padding: '10px 20px', backgroundColor: '#f97316', color: 'white', border: 'none', borderRadius: '8px', cursor: uploading ? 'not-allowed' : 'pointer' }}
              >
                PDF提取导入
              </button>
            </div>
          </div>
        </div>
      )}

      {activeTab === 'l2' && (
        <div className="card">
          <h2 style={{ marginBottom: '20px' }}>L2文档导入</h2>
          <p style={{ marginBottom: '15px', color: '#666' }}>
            上传PDF文档，系统将自动解析并提取其中的组件和术语信息存入L2层。
          </p>
          <input
            type="file"
            accept=".pdf"
            onChange={handleL2Upload}
            style={{ display: 'none' }}
            id="l2-upload"
          />
          <button
            onClick={() => document.getElementById('l2-upload')?.click()}
            disabled={uploading}
            style={{ padding: '15px 30px', backgroundColor: '#f97316', color: 'white', border: 'none', borderRadius: '8px', cursor: uploading ? 'not-allowed' : 'pointer' }}
          >
            选择PDF文件
          </button>
        </div>
      )}

      {activeTab === 'l3' && (
        <div className="card">
          <h2 style={{ marginBottom: '20px' }}>L3术语导入</h2>
          <p style={{ color: '#666' }}>
            L3术语可以从L2文档自动提取，也支持手动添加。
          </p>
        </div>
      )}
    </div>
  )
}
```

- [ ] **Step 2: Commit**

```bash
git add frontend/src/pages/ImportManager.tsx
git commit -m "feat(phase3): add import manager page"
```

---

### Task 12: Docker配置

**Files:**
- Create: `docker-compose.yml`
- Create: `backend/Dockerfile`
- Modify: `requirements.txt`

- [ ] **Step 1: 创建 docker-compose.yml**

```yaml
version: '3.8'

services:
  frontend:
    build: ./frontend
    ports:
      - "3000:3000"
    depends_on:
      - backend
    networks:
      - app-network

  backend:
    build: ./backend
    ports:
      - "8000:8000"
    volumes:
      - ./config.yaml:/app/config.yaml:ro
    depends_on:
      - neo4j
    environment:
      - NEO4J_URI=bolt://neo4j:7687
      - NEO4J_USER=neo4j
      - NEO4J_PASSWORD=password
    networks:
      - app-network

  neo4j:
    image: neo4j:5.20
    ports:
      - "7474:7474"
      - "7687:7687"
    volumes:
      - neo4j_data:/data
    environment:
      - NEO4J_AUTH=neo4j/password
    networks:
      - app-network

volumes:
  neo4j_data:

networks:
  app-network:
    driver: bridge
```

- [ ] **Step 2: 创建 backend/Dockerfile**

```dockerfile
FROM python:3.11-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

EXPOSE 8000

CMD ["uvicorn", "src.main:app", "--host", "0.0.0.0", "--port", "8000"]
```

- [ ] **Step 3: 更新 requirements.txt**

```txt
fastapi==0.109.0
uvicorn==0.27.0
neo4j==5.18.0
pymilvus==2.4.0
openai==1.12.0
pydantic==2.5.3
pydantic-settings==2.1.0
python-dotenv==1.0.0
pytest==8.0.0
pytest-asyncio==0.23.0
httpx==0.26.0
pyyaml==6.0.1
python-multipart==0.0.9
```

- [ ] **Step 4: Commit**

```bash
git add docker-compose.yml backend/Dockerfile requirements.txt
git commit -m "feat(phase3): add Docker configuration"
```

---

## 验收标准

- [ ] Task 1: 前端项目初始化完成
- [ ] Task 2: 基础布局组件完成
- [ ] Task 3: API客户端和类型定义完成
- [ ] Task 4: 图谱API路由完成
- [ ] Task 5: 查询和配置API路由完成
- [ ] Task 6: 导入API路由完成
- [ ] Task 7: 图谱可视化页面完成
- [ ] Task 8: 仪表盘页面完成
- [ ] Task 9: 推理查询页面完成
- [ ] Task 10: 参数设置页面完成
- [ ] Task 11: 导入管理页面完成
- [ ] Task 12: Docker配置完成

---

## 下一步

**选择执行方式：**

1. **Subagent-Driven (推荐)** - 每个任务由独立子代理执行
2. **Inline Execution** - 在当前会话中执行任务

**你选择哪种方式？**