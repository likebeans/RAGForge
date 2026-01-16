# App 应用核心模块

RAGForge 后端应用的核心代码目录。

## 目录结构

```
app/
├── main.py              # FastAPI 应用入口
├── config.py            # 配置管理（环境变量）
├── exceptions.py        # 自定义异常
├── api/                 # API 路由层
├── auth/                # 认证模块
├── db/                  # 数据库配置
├── infra/               # 基础设施层
├── middleware/          # 中间件
├── models/              # ORM 模型
├── pipeline/            # 算法框架
├── schemas/             # Pydantic 模型
└── services/            # 业务逻辑层
```

---

## 模块说明

### api/ - API 路由

| 文件 | 说明 |
|------|------|
| `deps.py` | 依赖注入（认证、数据库会话）|
| `routes/knowledge_bases.py` | 知识库 CRUD |
| `routes/documents.py` | 文档上传与管理 |
| `routes/retrieve.py` | 检索接口 |
| `routes/rag.py` | RAG 生成 |
| `routes/conversations.py` | 对话管理 |
| `routes/api_keys.py` | API Key 管理 |
| `routes/openai_compat.py` | OpenAI 兼容接口 |

### auth/ - 认证

| 文件 | 说明 |
|------|------|
| `api_key.py` | API Key 认证、角色权限、限流 |

### services/ - 业务逻辑

| 文件 | 说明 |
|------|------|
| `ingestion.py` | 文档摄取（切分、向量化、入库）|
| `query.py` | 检索服务 |
| `rag.py` | RAG 生成服务 |
| `acl.py` | ACL 权限服务 |
| `audit.py` | 审计日志服务 |

### infra/ - 基础设施

| 文件 | 说明 |
|------|------|
| `llm.py` | LLM 客户端（多提供商）|
| `embeddings.py` | 向量化服务 |
| `rerank.py` | 重排序服务 |
| `vector_store.py` | Qdrant 操作 |
| `bm25_store.py` | BM25 存储 |
| `logging.py` | 结构化日志 |

### models/ - 数据模型

| 文件 | 说明 |
|------|------|
| `tenant.py` | 租户 |
| `api_key.py` | API Key |
| `knowledge_base.py` | 知识库 |
| `document.py` | 文档 |
| `chunk.py` | 文档块 |
| `conversation.py` | 对话和消息 |

### schemas/ - 请求/响应模型

| 文件 | 说明 |
|------|------|
| `knowledge_base.py` | 知识库 Schema |
| `document.py` | 文档 Schema |
| `retrieve.py` | 检索请求/响应 |
| `rag.py` | RAG 请求/响应 |
| `config.py` | 配置类型定义 |

### pipeline/ - 算法框架

详见 [pipeline/README.md](./pipeline/README.md)

### middleware/ - 中间件

| 文件 | 说明 |
|------|------|
| `audit.py` | 审计日志中间件 |
| `request_trace.py` | 请求追踪中间件 |

---

## 核心流程

### 文档入库流程

```
上传文档 → 解析内容 → 切分 Chunks → 向量化 → 存储到 Qdrant + PostgreSQL
                                    ↓
                              可选：RAPTOR 索引
                              可选：BM25 索引
```

### 检索流程

```
查询请求 → 检索器选择 → 向量/BM25/混合检索 → ACL 过滤 → 返回结果
```

### RAG 流程

```
查询请求 → 检索相关文档 → 构建 Prompt → LLM 生成 → 返回答案
```

---

## 配置管理

配置通过环境变量加载，定义在 `config.py`：

```python
from app.config import settings

# 数据库
settings.database_url

# 向量存储
settings.qdrant_host
settings.qdrant_port

# LLM 提供商
settings.llm_provider
settings.llm_model
```

---

## 开发指南

### 添加新 API

1. 在 `api/routes/` 创建路由文件
2. 在 `api/__init__.py` 注册路由
3. 在 `schemas/` 定义请求/响应模型

### 添加新服务

1. 在 `services/` 创建服务文件
2. 使用依赖注入获取数据库会话
3. 在路由中调用服务

### 添加新模型

1. 在 `models/` 创建模型文件
2. 在 `models/__init__.py` 导出
3. 创建 Alembic 迁移：`uv run alembic revision --autogenerate -m "描述"`
4. 执行迁移：`uv run alembic upgrade head`
