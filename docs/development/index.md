# 开发文档

欢迎来到 Self-RAG Pipeline 开发文档！本节为开发者提供完整的开发指南，包括代码贡献、测试、调试和扩展开发。

## 概述

Self-RAG Pipeline 采用现代化的 Python 技术栈，基于 FastAPI + SQLAlchemy 2.0 构建，支持异步操作和高性能处理。项目采用模块化设计，便于扩展和维护。

## 技术栈

### 后端核心
- **Python 3.11+**：现代 Python 特性支持
- **FastAPI**：高性能异步 Web 框架
- **SQLAlchemy 2.0**：现代 ORM，支持异步操作
- **Alembic**：数据库迁移管理
- **uv**：快速的 Python 包管理器

### 数据存储
- **PostgreSQL**：主数据库，存储元数据
- **Qdrant**：向量数据库（默认）
- **可选支持**：Milvus、Elasticsearch

### AI/ML 框架
- **LlamaIndex**：RAG 框架集成
- **多 LLM 提供商**：OpenAI、Ollama、Qwen 等
- **多 Embedding 提供商**：支持各种向量化模型

### 前端
- **Next.js 14**：React 框架
- **TypeScript**：类型安全
- **Tailwind CSS**：样式框架

## 开发环境设置

### 1. 克隆项目
```bash
git clone https://github.com/your-org/self-rag-pipeline.git
cd self-rag-pipeline
```

### 2. 安装依赖
```bash
# 安装 uv（如果还没有）
curl -LsSf https://astral.sh/uv/install.sh | sh

# 安装 Python 依赖
uv sync
```

### 3. 启动基础设施
```bash
# 启动 PostgreSQL + Qdrant
docker compose up -d db qdrant

# 运行数据库迁移
uv run alembic upgrade head
```

### 4. 启动开发服务器
```bash
# 后端 API 服务（端口 8020）
uv run uvicorn app.main:app --reload --port 8020

# 前端开发服务器（端口 3000）
cd frontend
npm install
npm run dev
```

## 项目结构

```
self-rag-pipeline/
├── app/                    # 后端应用
│   ├── main.py            # FastAPI 应用入口
│   ├── config.py          # 配置管理
│   ├── api/               # API 路由层
│   ├── auth/              # 认证模块
│   ├── models/            # 数据模型
│   ├── schemas/           # Pydantic 模式
│   ├── pipeline/          # 算法框架
│   ├── services/          # 业务逻辑
│   ├── infra/             # 基础设施
│   └── middleware/        # 中间件
├── frontend/              # 前端应用
├── docs/                  # 文档
├── tests/                 # 测试文件
├── alembic/               # 数据库迁移
├── sdk/                   # Python SDK
└── scripts/               # 工具脚本
```

## 开发工作流

### 代码规范

我们使用以下工具确保代码质量：

```bash
# 代码格式化
uv run ruff format .

# 代码检查
uv run ruff check --fix .

# 类型检查
uv run mypy app/

# 运行测试
uv run pytest tests/ -v
```

### Git 工作流

1. **创建功能分支**
   ```bash
   git checkout -b feature/your-feature-name
   ```

2. **提交代码**
   ```bash
   git add .
   git commit -m "feat: add new feature description"
   ```

3. **推送并创建 PR**
   ```bash
   git push origin feature/your-feature-name
   ```

### 提交信息规范

使用 [Conventional Commits](https://www.conventionalcommits.org/) 规范：

- `feat:` 新功能
- `fix:` 错误修复
- `docs:` 文档更新
- `style:` 代码格式调整
- `refactor:` 代码重构
- `test:` 测试相关
- `chore:` 构建或工具相关

## 开发指南

### 🚀 快速开始
- **[贡献指南](./contributing)** - 如何参与项目开发
- **[测试指南](./testing)** - 编写和运行测试

### 🔧 核心开发
- **[管道开发](./pipeline-development)** - 开发自定义算法组件
- **[多租户开发](./multi-tenant-development)** - 多租户功能开发

### 🐛 问题排查
- **[开发问题排查](./troubleshooting)** - 常见开发问题解决

## 核心概念

### 可插拔算法框架

Self-RAG Pipeline 的核心优势是可插拔的算法框架，支持：

- **切分器（Chunkers）**：文档切分策略
- **检索器（Retrievers）**：检索算法实现
- **增强器（Enrichers）**：文档增强处理
- **后处理器（Postprocessors）**：结果后处理

### 异步编程模式

项目全面采用异步编程：

```python
# 数据库操作
async def get_user(db: AsyncSession, user_id: int):
    result = await db.execute(select(User).where(User.id == user_id))
    return result.scalar_one_or_none()

# HTTP 客户端
async def call_llm_api(prompt: str):
    async with httpx.AsyncClient() as client:
        response = await client.post(url, json={"prompt": prompt})
        return response.json()
```

### 多租户架构

每个请求都通过租户上下文处理：

```python
# 依赖注入获取当前租户
async def get_current_tenant(
    api_key: str = Depends(get_api_key)
) -> Tenant:
    # 验证 API Key 并返回租户信息
    pass

# 业务逻辑中使用租户上下文
async def create_knowledge_base(
    kb_data: KBCreate,
    tenant: Tenant = Depends(get_current_tenant)
):
    # 在租户上下文中创建知识库
    pass
```

## API 开发

### 路由组织

```python
# app/api/routes/knowledge_bases.py
from fastapi import APIRouter, Depends

router = APIRouter(prefix="/v1/knowledge-bases", tags=["knowledge-bases"])

@router.post("/", response_model=KnowledgeBaseResponse)
async def create_knowledge_base(
    kb_data: KnowledgeBaseCreate,
    tenant: Tenant = Depends(get_current_tenant),
    db: AsyncSession = Depends(get_db)
):
    """创建知识库"""
    pass
```

### 错误处理

```python
from app.exceptions import KnowledgeBaseNotFoundError

@router.get("/{kb_id}")
async def get_knowledge_base(kb_id: str, tenant: Tenant = Depends(get_current_tenant)):
    kb = await kb_service.get_by_id(kb_id, tenant.id)
    if not kb:
        raise KnowledgeBaseNotFoundError(f"Knowledge base {kb_id} not found")
    return kb
```

## 数据库开发

### 模型定义

```python
# app/models/knowledge_base.py
from sqlalchemy import Column, String, DateTime, Text, Boolean
from sqlalchemy.dialects.postgresql import UUID
from app.db.base import Base

class KnowledgeBase(Base):
    __tablename__ = "knowledge_bases"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id = Column(UUID(as_uuid=True), ForeignKey("tenants.id"), nullable=False)
    name = Column(String(255), nullable=False)
    description = Column(Text)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
```

### 迁移管理

```bash
# 创建迁移
uv run alembic revision --autogenerate -m "add knowledge base table"

# 应用迁移
uv run alembic upgrade head

# 回滚迁移
uv run alembic downgrade -1
```

## 测试开发

### 单元测试

```python
# tests/test_knowledge_base.py
import pytest
from app.services.knowledge_base import KnowledgeBaseService

@pytest.mark.asyncio
async def test_create_knowledge_base():
    service = KnowledgeBaseService()
    kb = await service.create(name="Test KB", tenant_id="tenant-1")
    assert kb.name == "Test KB"
```

### 集成测试

```python
# tests/test_api.py
from httpx import AsyncClient

@pytest.mark.asyncio
async def test_create_kb_api(client: AsyncClient, auth_headers):
    response = await client.post(
        "/v1/knowledge-bases",
        json={"name": "Test KB"},
        headers=auth_headers
    )
    assert response.status_code == 201
```

## 性能优化

### 数据库优化

- 使用连接池
- 合理的索引设计
- 批量操作优化
- 查询优化

### 缓存策略

- Redis 缓存热点数据
- 应用层缓存
- 向量检索结果缓存

### 异步处理

- 文档处理异步化
- 批量向量化
- 后台任务队列

## 部署和运维

### Docker 构建

```bash
# 构建镜像
docker build -t self-rag-pipeline .

# 运行容器
docker run -p 8020:8020 self-rag-pipeline
```

### 环境配置

```bash
# .env 文件
DATABASE_URL=postgresql+asyncpg://user:pass@localhost:5432/db
QDRANT_URL=http://localhost:6333
LLM_PROVIDER=ollama
LLM_MODEL=qwen2.5:14b
```

## 贡献指南

我们欢迎各种形式的贡献：

1. **🐛 报告问题**：发现 bug 请提交 Issue
2. **💡 功能建议**：有好的想法请分享
3. **📝 改进文档**：帮助完善文档
4. **🔧 代码贡献**：提交 Pull Request

详细的贡献流程请查看 [贡献指南](./contributing)。

## 获取帮助

- **📖 文档**：查看完整的 [API 文档](../architecture/api-specification)
- **🐛 问题**：在 GitHub 上提交 [Issue](https://github.com/your-org/self-rag-pipeline/issues)
- **💬 讨论**：加入开发者社区讨论
- **📧 联系**：联系维护团队

---

准备开始开发了吗？从 [贡献指南](./contributing) 开始，或者直接查看 [测试指南](./testing) 了解如何运行测试。