# 部署指南

本文档详细说明动力电池拆卸知识图谱系统的部署方法。

## 目录

- [环境要求](#环境要求)
- [快速部署 (Docker)](#快速部署-docker)
- [手动部署](#手动部署)
- [生产环境配置](#生产环境配置)
- [验证部署](#验证部署)
- [故障排除](#故障排除)

---

## 环境要求

### 最低要求

| 组件 | 要求 |
|------|------|
| CPU | 4核 |
| 内存 | 8GB |
| 磁盘 | 20GB |
| Docker | 20.10+ |
| Docker Compose | 2.0+ |

### 推荐配置

| 组件 | 要求 |
|------|------|
| CPU | 8核+ |
| 内存 | 16GB+ |
| 磁盘 | 50GB+ (SSD) |
| Docker | 24.0+ |
| Docker Compose | 2.20+ |

### 外部服务

- **Neo4j 5.20+**: 图数据库 (已包含在docker-compose中)
- **OpenAI API**: GPT-4o 访问权限

---

## 快速部署 (Docker)

### 1. 克隆项目

```bash
git clone https://github.com/01Rit/EVB_KG_LLM.git
cd EVB_KG_LLM
```

### 2. 配置环境变量

```bash
# 复制环境变量模板
cp .env.example .env

# 编辑 .env 文件，填入你的配置
nano .env
```

**必需配置：**
```env
NEO4J_URI=bolt://neo4j:7687
NEO4J_USER=neo4j
NEO4J_PASSWORD=your_secure_password
OPENAI_API_KEY=sk-your-openai-api-key
OPENAI_BASE_URL=https://api.openai.com/v1
```

### 3. 启动服务

```bash
# 构建并启动所有服务
docker-compose up -d

# 查看服务状态
docker-compose ps

# 查看日志
docker-compose logs -f
```

### 4. 访问应用

部署成功后访问：

| 服务 | 地址 |
|------|------|
| 前端界面 | http://localhost:3000 |
| API文档 | http://localhost:8000/docs |
| Neo4j Browser | http://localhost:7474 |

---

## 手动部署

### 后端部署

#### 1. 安装依赖

```bash
# 创建虚拟环境
python -m venv venv
source venv/bin/activate  # Linux/Mac
# venv\Scripts\activate   # Windows

# 安装依赖
pip install -r requirements.txt
```

#### 2. 配置环境变量

```bash
export NEO4J_URI=bolt://localhost:7687
export NEO4J_USER=neo4j
export NEO4J_PASSWORD=your_password
export OPENAI_API_KEY=sk-your-api-key
export OPENAI_BASE_URL=https://api.openai.com/v1
```

#### 3. 启动服务

```bash
# 启动Neo4j (单独安装)
# 请参考 https://neo4j.com/docs/operations-manual/current/

# 启动后端
uvicorn src.main:app --host 0.0.0.0 --port 8000
```

### 前端部署

#### 1. 安装依赖

```bash
cd frontend
npm install
```

#### 2. 构建

```bash
npm run build
```

#### 3. 配置Nginx

```nginx
server {
    listen 3000;
    server_name localhost;
    root /path/to/EVB_KG_LLM/frontend/dist;
    index index.html;

    location / {
        try_files $uri $uri/ /index.html;
    }

    location /api/ {
        proxy_pass http://localhost:8000;
        proxy_http_version 1.1;
        proxy_set_header Host $host;
    }
}
```

#### 4. 启动Nginx

```bash
nginx -c /path/to/nginx.conf
```

---

## 生产环境配置

### 1. 安全配置

#### 使用环境变量

```bash
# 不要在 .env 文件中存储敏感信息
# 使用 Docker secrets 或 K8s secrets
```

#### HTTPS配置

```nginx
server {
    listen 443 ssl http2;
    server_name your-domain.com;

    ssl_certificate /path/to/fullchain.pem;
    ssl_certificate_key /path/to/privkey.pem;

    # 安全头
    add_header X-Frame-Options "SAMEORIGIN" always;
    add_header X-Content-Type-Options "nosniff" always;
    add_header X-XSS-Protection "1; mode=block" always;
}
```

### 2. Neo4j生产配置

```yaml
# neo4j.conf
dbms.memory.heap.initial_size=4g
dbms.memory.heap.max_size=8g
dbms.memory.pagecache.size=2g
dbms.transaction.timeout=60s
```

### 3. 反向代理配置 (Nginx)

```nginx
upstream backend {
    server localhost:8000;
}

upstream frontend {
    server localhost:3000;
}

server {
    listen 80;
    server_name your-domain.com;
    return 301 https://$server_name$request_uri;
}

server {
    listen 443 ssl http2;
    server_name your-domain.com;

    ssl_certificate /path/to/cert.pem;
    ssl_certificate_key /path/to/key.pem;

    client_max_body_size 10M;

    location / {
        proxy_pass http://frontend;
    }

    location /api/ {
        proxy_pass http://backend;
    }

    location /docs/ {
        proxy_pass http://backend;
    }
}
```

### 4. Docker生产部署

```yaml
# docker-compose.prod.yml
version: '3.8'

services:
  frontend:
    restart: always
    ports:
      - "80:3000"
    environment:
      - NODE_ENV=production

  backend:
    restart: always
    environment:
      - NEO4J_URI=${NEO4J_URI}
      - NEO4J_USER=${NEO4J_USER}
      - NEO4J_PASSWORD=${NEO4J_PASSWORD}
      - OPENAI_API_KEY=${OPENAI_API_KEY}
    deploy:
      resources:
        limits:
          memory: 4G
        reservations:
          memory: 2G

  neo4j:
    restart: always
    ports:
      - "7474:7474"
      - "7687:7687"
    volumes:
      - neo4j_data:/data
      - ./neo4j.conf:/conf/neo4j.conf
    environment:
      - NEO4J_AUTH=neo4j/${NEO4J_PASSWORD}
```

---

## 验证部署

### 1. 检查服务状态

```bash
# 检查容器状态
docker-compose ps

# 检查健康状态
curl http://localhost:8000/api/v1/health
```

### 2. 验证API

```bash
# 健康检查
curl http://localhost:8000/api/v1/health

# 预期响应:
# {"status":"healthy","neo4j":"connected","milvus":"not_configured","llm":"available"}
```

### 3. 验证前端

在浏览器中访问 http://localhost:3000

### 4. 运行测试

```bash
python -m pytest tests/ -v
```

---

## 故障排除

### 常见问题

#### 1. Neo4j连接失败

```bash
# 检查Neo4j日志
docker-compose logs neo4j

# 检查Neo4j是否正常启动
docker-compose exec neo4j cypher-shell -u neo4j -p password "MATCH (n) RETURN count(n)"
```

#### 2. 前端无法访问API

```bash
# 检查后端日志
docker-compose logs backend

# 检查网络连接
docker-compose exec frontend curl http://backend:8000/api/v1/health
```

#### 3. OpenAI API错误

```bash
# 检查API Key配置
docker-compose logs backend | grep -i openai

# 验证API Key
curl -H "Authorization: Bearer $OPENAI_API_KEY" https://api.openai.com/v1/models
```

#### 4. 端口占用

```bash
# 检查端口占用
netstat -tlnp | grep 3000
netstat -tlnp | grep 8000

# 杀死占用进程
kill -9 <PID>
```

### 日志位置

| 服务 | 日志命令 |
|------|----------|
| frontend | `docker-compose logs -f frontend` |
| backend | `docker-compose logs -f backend` |
| neo4j | `docker-compose logs -f neo4j` |

### 数据备份

```bash
# 备份Neo4j数据
docker-compose exec neo4j neo4j-admin database dump --to-path=/data/backup/

# 备份配置
cp config.yaml config.yaml.backup
```

### 重启服务

```bash
# 重启所有服务
docker-compose restart

# 重启特定服务
docker-compose restart backend

# 完全重建
docker-compose down -v
docker-compose up -d --build
```

---

## 扩展部署

### 水平扩展

```yaml
# docker-compose.scale.yml
services:
  backend:
    deploy:
      replicas: 3

  nginx:
    image: nginx:alpine
    ports:
      - "80:80"
    volumes:
      - ./nginx.conf:/etc/nginx/nginx.conf:ro
```

### 使用Kubernetes

参考 K8s 部署清单 (待提供)

---

## 联系支持

如遇问题请提交 Issue: https://github.com/01Rit/EVB_KG_LLM/issues
