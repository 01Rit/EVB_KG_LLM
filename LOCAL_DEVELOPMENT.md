# 本地开发指南

本文档详细介绍如何在本地机器上运行动力电池拆卸知识图谱系统。

## 目录

- [环境要求](#环境要求)
- [架构概览](#架构概览)
- [快速开始 (Docker)](#快速开始-docker)
- [手动部署 (详细步骤)](#手动部署-详细步骤)
- [验证运行](#验证运行)
- [常见问题](#常见问题)

---

## 环境要求

### 必须安装的软件

| 软件 | 版本要求 | 说明 | 下载地址 |
|------|----------|------|----------|
| **Python** | 3.11+ | 后端运行环境 | https://www.python.org/downloads/ |
| **Node.js** | 18+ | 前端运行环境 | https://nodejs.org/ |
| **Git** | 任意版本 | 版本控制 | https://git-scm.com/ |
| **Neo4j** | 5.20+ | 图数据库 | https://neo4j.com/download/ |

### 可选软件

| 软件 | 用途 | 下载地址 |
|------|------|----------|
| **Docker Desktop** | 容器化部署 | https://www.docker.com/products/docker-desktop/ |
| **PyCharm/VSCode** | Python IDE | https://www.jetbrains.com/pycharm/ 或 https://code.visualstudio.com/ |
| **WebStorm/VSCode** | 前端IDE | https://www.jetbrains.com/webstorm/ 或 VSCode |

### 硬件要求

- **内存**: 最少 8GB (推荐 16GB+)
- **磁盘**: 最少 10GB 可用空间
- **操作系统**: Windows 10/11, macOS 10.14+, Ubuntu 18.04+

---

## 架构概览

```
┌─────────────────────────────────────────────────────────────────┐
│                        用户浏览器                                 │
│                     http://localhost:3000                        │
└─────────────────────────────────────────────────────────────────┘
                                │
                                ▼
┌─────────────────────────────────────────────────────────────────┐
│                      React 前端 (端口 3000)                       │
│                   处理用户界面和API请求转发                        │
└─────────────────────────────────────────────────────────────────┘
                                │ HTTP请求 (/api/*)
                                ▼
┌─────────────────────────────────────────────────────────────────┐
│                   FastAPI 后端 (端口 8000)                       │
│                                                                 │
│   ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────┐      │
│   │ GraphRAG │  │ Sequence │  │ Allocator│  │ Importer │      │
│   │  推理模块 │  │ 序列规划 │  │ 人机分配 │  │ 数据导入 │      │
│   └──────────┘  └──────────┘  └──────────┘  └──────────┘      │
└─────────────────────────────────────────────────────────────────┘
                                │
                    ┌───────────┴───────────┐
                    ▼                       ▼
        ┌──────────────────┐      ┌──────────────────┐
        │      Neo4j       │      │   OpenAI API     │
        │   (端口 7687)    │      │   (外部服务)      │
        │     图数据库      │      │    GPT-4o        │
        └──────────────────┘      └──────────────────┘
```

### 各组件说明

| 组件 | 端口 | 技术栈 | 作用 |
|------|------|--------|------|
| **前端** | 3000 | React + TypeScript | 用户界面，交互体验 |
| **后端** | 8000 | FastAPI + Python | API服务，业务逻辑 |
| **Neo4j** | 7687 | Cypher查询 | 知识图谱存储和查询 |
| **OpenAI** | 外部 | GPT-4o API | LLM推理生成 |

---

## 快速开始 (Docker)

**推荐方式**：使用Docker一键启动所有服务

### 步骤 1: 检查Docker环境

```bash
# 打开终端 (Windows: PowerShell, Mac: Terminal)

# 检查Docker是否安装
docker --version
docker-compose --version

# 如果没有安装，参考 https://docs.docker.com/get-docker/
```

### 步骤 2: 克隆项目

```bash
git clone https://github.com/01Rit/EVB_KG_LLM.git
cd EVB_KG_LLM
```

### 步骤 3: 配置环境变量

```bash
# 复制环境变量模板
cp .env.example .env

# 编辑 .env 文件 (Windows用 notepad 或任意文本编辑器)
notepad .env
```

**必须修改的配置**：
```env
NEO4J_PASSWORD=your_secure_password_here  # 设置你的Neo4j密码
OPENAI_API_KEY=sk-your-openai-api-key      # 你的OpenAI API Key
```

### 步骤 4: 启动服务

```bash
# 构建并启动所有服务 (首次运行需要下载镜像，约5-10分钟)
docker-compose up -d

# 查看服务状态
docker-compose ps
```

**预期输出**：
```
NAME                COMMAND               SERVICE
evb-kg-frontend    nginx -g daemon ...   frontend
evb-kg-backend     uvicorn src.main...   backend
evb-kg-neo4j       tini -g -s -- ...     neo4j
```

### 步骤 5: 验证运行

```bash
# 等待30秒让服务完全启动

# 检查后端API
curl http://localhost:8000/api/v1/health

# 预期响应:
# {"status":"healthy","neo4j":"connected","milvus":"not_configured","llm":"available"}
```

### 步骤 6: 访问界面

打开浏览器访问：

| 服务 | 地址 | 说明 |
|------|------|------|
| **前端界面** | http://localhost:3000 | 主界面 |
| **API文档** | http://localhost:8000/docs | Swagger API文档 |
| **Neo4j Browser** | http://localhost:7474 | 图数据库浏览器 (密码: 你设置的NEO4J_PASSWORD) |

### 停止服务

```bash
# 停止服务 (保留数据)
docker-compose stop

# 完全停止并删除容器 (保留数据卷)
docker-compose down

# 完全清理 (删除所有数据)
docker-compose down -v
```

---

## 手动部署 (详细步骤)

如果不使用Docker，需要手动安装和配置每个组件。

### 第一部分：后端设置

#### 步骤 1.1: 安装 Python

```bash
# 检查Python版本 (必须是3.11+)
python --version
# 输出应该是: Python 3.11.x 或更高

# 如果没有安装，下载: https://www.python.org/downloads/
# 安装时勾选 "Add Python to PATH"
```

#### 步骤 1.2: 创建虚拟环境

```bash
# 进入项目目录
cd D:\KG_project\Final4.14

# 创建虚拟环境 (推荐使用venv)
python -m venv venv

# 激活虚拟环境
# Windows:
venv\Scripts\activate
# Mac/Linux:
source venv/bin/activate

# 激活成功后，命令行前面会显示 (venv)
```

#### 步骤 1.3: 安装后端依赖

```bash
# 确保在虚拟环境中
pip install -r requirements.txt

# 安装成功后会显示类似:
# Successfully installed fastapi-0.109.0 uvicorn-0.27.0 ...
```

#### 步骤 1.4: 安装并启动 Neo4j

**方式A: 使用Neo4j Desktop (推荐新手)**

1. 下载并安装 [Neo4j Desktop](https://neo4j.com/download/)
2. 启动Neo4j Desktop
3. 点击 "New Project" → "Add Database"
4. 选择 Neo4j 5.20+ 版本
5. 设置密码 (记住这个密码!)
6. 点击 "Start" 启动数据库

**方式B: 使用Docker运行Neo4j**

```bash
# 如果你只想单独运行Neo4j (不启动整个项目)
docker run \
    --name neo4j \
    -p 7474:7474 \
    -p 7687:7687 \
    -e NEO4J_AUTH=neo4j/your_password \
    neo4j:5.20

# 浏览器访问 http://localhost:7474
```

#### 步骤 1.5: 配置环境变量

```bash
# 创建 .env 文件
notepad .env
```

**添加以下内容** (修改密码和API Key):
```env
NEO4J_URI=bolt://localhost:7687
NEO4J_USER=neo4j
NEO4J_PASSWORD=your_neo4j_password_here
MILVUS_HOST=localhost
MILVUS_PORT=19530
OPENAI_API_KEY=sk-your-openai-api-key-here
OPENAI_BASE_URL=https://api.openai.com/v1
MODEL=gpt-4o
TEMPERATURE=0.1
MAX_TOKENS=2000
LOG_LEVEL=INFO
```

#### 步骤 1.6: 启动后端服务

```bash
# 确保Neo4j正在运行

# 启动后端 (开发模式，支持热重载)
uvicorn src.main:app --reload --port 8000

# 或使用Python直接运行
python -m uvicorn src.main:app --reload --port 8000
```

**预期输出**:
```
INFO:     Uvicorn running on http://127.0.0.1:8000
INFO:     Application startup complete.
```

### 第二部分：前端设置

#### 步骤 2.1: 安装 Node.js

```bash
# 检查Node版本 (必须是18+)
node --version
# 输出: v18.x.x 或更高

# 如果没有安装，下载: https://nodejs.org/
# 推荐安装LTS版本
```

#### 步骤 2.2: 安装前端依赖

```bash
# 新开一个终端窗口

# 进入前端目录
cd D:\KG_project\Final4.14\frontend

# 安装依赖 (首次运行约3-5分钟)
npm install

# 成功后会显示:
# added 245 packages in 30s
```

#### 步骤 2.3: 配置API代理

前端开发服务器会自动代理API请求到后端。

检查 `vite.config.ts`:
```typescript
// frontend/vite.config.ts
export default defineConfig({
  plugins: [react()],
  server: {
    port: 3000,
    proxy: {
      '/api': {
        target: 'http://localhost:8000',  // 后端地址
        changeOrigin: true,
      },
    },
  },
})
```

#### 步骤 2.4: 启动前端开发服务器

```bash
# 在frontend目录下
npm run dev
```

**预期输出**:
```
  VITE v5.x.x  ready in 500 ms

  ➜  Local:   http://localhost:3000/
  ➜  Network: http://192.168.x.x:3000/
```

---

## 验证运行

### 1. 检查后端API

```bash
# 健康检查
curl http://localhost:8000/api/v1/health

# 预期响应:
# {"status":"healthy","neo4j":"connected","milvus":"not_configured","llm":"available"}
```

### 2. 检查API文档

浏览器打开: http://localhost:8000/docs

你应该能看到Swagger UI，可以在这里测试所有API接口。

### 3. 访问前端界面

浏览器打开: http://localhost:3000

你应该能看到项目的前端界面。

### 4. 测试拆卸规划接口

使用Swagger UI或curl测试:

```bash
curl -X POST http://localhost:8000/api/v1/disassembly/plan \
  -H "Content-Type: application/json" \
  -d '{"battery_model": "X123", "context": [], "debug": false}'
```

---

## 常见问题

### Q1: 启动后端时报错 "ModuleNotFoundError"

**原因**: 虚拟环境未激活或依赖未安装

**解决方法**:
```bash
# 确保激活虚拟环境
venv\Scripts\activate

# 重新安装依赖
pip install -r requirements.txt
```

### Q2: Neo4j连接失败 "Connection refused"

**原因**: Neo4j未启动或端口配置错误

**解决方法**:
1. 确认Neo4j正在运行 (检查Neo4j Desktop或Docker)
2. 检查 .env 中的 NEO4J_URI 是否正确
3. 检查NEO4j密码是否匹配

```bash
# 测试Neo4j连接
docker exec -it <neo4j_container> cypher-shell -u neo4j -p your_password "MATCH (n) RETURN count(n)"
```

### Q3: OpenAI API错误 "Invalid API key"

**原因**: API Key配置错误或余额不足

**解决方法**:
1. 检查 .env 中 OPENAI_API_KEY 是否正确
2. 确认API Key有余额: https://platform.openai.com/account/usage
3. 检查网络能否访问OpenAI: `curl https://api.openai.com/v1/models`

### Q4: 前端无法访问API (CORS错误)

**原因**: 后端CORS配置问题

**解决方法**:
检查 `src/main.py` 中的CORS配置:
```python
# 确保允许你的前端地址
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],  # 前端地址
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
```

### Q5: Docker构建失败

**原因**: Docker镜像下载慢或网络问题

**解决方法**:
```bash
# 使用国内镜像 (如果可用)
# 或者等待重试

# 查看详细错误
docker-compose build --no-cache
```

### Q6: 端口被占用

**原因**: 3000或8000端口被其他程序占用

**解决方法**:
```bash
# 查找占用端口的进程 (Windows)
netstat -ano | findstr :3000
netstat -ano | findstr :8000

# 结束进程 (替换 <PID>)
taskkill /PID <PID> /F

# 或者修改docker-compose.yml中的端口映射
```

### Q7: 前端npm install失败

**原因**: Node版本不对或npm源问题

**解决方法**:
```bash
# 确认Node版本
node --version  # 需要18+

# 使用淘宝镜像 (国内)
npm config set registry https://registry.npmmirror.com
npm install

# 或直接指定
npm install --registry https://registry.npmmirror.com
```

---

## 开发技巧

### 使用IDE (推荐PyCharm/VSCode)

**Python后端 (VSCode)**:
1. 安装 Python 扩展
2. 安装 Pylance 扩展
3. 选择虚拟环境中的Python解释器
4. 按F5启动调试

**前端 (VSCode)**:
1. 安装 ESLint 扩展
2. 安装 Prettier 扩展
3. 安装 React 扩展
4. 使用 `npm run dev` 启动

### 热重载

- **后端**: uvicorn的 `--reload` 参数支持热重载
- **前端**: Vite默认支持热重载

修改代码后会自动重新加载。

### 查看日志

```bash
# Docker方式
docker-compose logs -f backend
docker-compose logs -f frontend

# 直接运行方式
# 日志直接输出在终端窗口
```

### 运行测试

```bash
# 所有测试
python -m pytest tests/ -v

# 单个模块测试
python -m pytest tests/graphrag/ -v

# 带覆盖率
python -m pytest tests/ --cov=src --cov-report=html
```

---

## 总结

| 步骤 | 命令 | 说明 |
|------|------|------|
| 1. 克隆 | `git clone ...` | 获取代码 |
| 2. 配置 | `cp .env.example .env` + 编辑 | 设置环境变量 |
| 3. Docker | `docker-compose up -d` | 一键启动 |
| 或 | | |
| 3a. 后端 | `venv\Scripts\activate && uvicorn src.main:app` | 启动后端 |
| 3b. 前端 | `cd frontend && npm run dev` | 启动前端 |
| 4. 验证 | http://localhost:3000 | 访问界面 |

**祝你开发愉快! 🚀**
