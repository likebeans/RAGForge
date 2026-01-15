# 系统架构

Self-RAG Pipeline 采用现代化的微服务架构设计，支持高并发、高可用和水平扩展。本节详细介绍系统的整体架构、核心组件和设计决策。

## 架构概览

### 整体架构图

```
┌─────────────────────────────────────────────────────────────────┐
│                        客户端层                                │
├─────────────────┬─────────────────┬─────────────────────────────┤
│   Web 前端      │   Python SDK    │      第三方应用             │
│   (Next.js)     │                 │   (OpenAI 兼容接口)         │
└─────────────────┴─────────────────┴─────────────────────────────┘
                                │
                   ┌─────────────────────────┐
                   │      API 网关层         │
                   │   (FastAPI + 中间件)    │
                   └─────────────────────────┘
                                │
        ┌───────────────────────┼───────────────────────┐
        │                       │                       │
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   认证授权层    │    │   业务逻辑层    │    │   算法框架层    │
│  (API Key 认证) │    │  (租户/KB 管理) │    │ (可插拔算法)    │
└─────────────────┘    └─────────────────┘    └─────────────────┘
                                │
        ┌───────────────────────┼───────────────────────┐
        │                       │                       │
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   数据存储层    │    │   向量存储层    │    │   外部服务层    │
│  (PostgreSQL)   │    │    (Qdrant)     │    │ (LLM 提供商)    │
└─────────────────┘    └─────────────────┘    └─────────────────┘
```

### 核心设计原则

1. **多租户优先**：从架构层面支持多租户隔离和管理
2. **可插拔设计**：算法组件可以灵活替换和扩展
3. **异步优先**：全面采用异步编程提升性能
4. **标准兼容**：提供 OpenAI 兼容接口降低集成成本
5. **云原生**：支持容器化部署和水平扩展

## 核心组件

### 1. API 网关层

**职责**：请求路由、认证授权、限流、日志记录

**技术栈**：
- FastAPI：高性能异步 Web 框架
- Pydantic：数据验证和序列化
- 中间件：请求追踪、审计日志、CORS

**关键特性**：
- OpenAI 兼容接口
- 自动 API 文档生成
- 请求/响应验证
- 异常处理和错误码标准化

### 2. 认证授权层

**职责**：API Key 管理、租户识别、权限控制

**认证流程**：
```
Client Request → API Key 验证 → 租户识别 → 权限检查 → 业务逻辑
```

**权限模型**：
- `admin`：全部权限 + API Key 管理
- `write`：创建/删除 KB、上传文档、检索
- `read`：仅检索和列表查看

### 3. 业务逻辑层

**核心服务**：

#### 租户管理服务
- 租户创建、禁用、配额管理
- API Key 生成和管理
- 多租户数据隔离

#### 知识库管理服务
- 知识库 CRUD 操作
- 配置管理和验证
- 文档上传和处理

#### 检索服务
- 多算法检索支持
- 结果融合和重排序
- 性能监控和优化

#### RAG 生成服务
- 多 LLM 提供商集成
- 上下文管理和优化
- 流式响应支持

### 4. 算法框架层

**可插拔组件架构**：

```python
# 组件注册机制
@register_chunker("recursive")
class RecursiveChunker(BaseChunker):
    def chunk(self, text: str) -> List[str]:
        # 实现递归切分逻辑
        pass

@register_retriever("hybrid")
class HybridRetriever(BaseRetriever):
    async def retrieve(self, query: str, **kwargs) -> List[Result]:
        # 实现混合检索逻辑
        pass
```

**支持的算法类型**：
- **切分器**：Simple、Sliding Window、Recursive、Markdown、Code
- **检索器**：Dense、BM25、Hybrid、RAPTOR、HyDE、Multi-Query
- **增强器**：Document Summarizer、Chunk Enricher
- **后处理器**：Context Window、Rerank

### 5. 数据存储层

#### PostgreSQL（主数据库）
- **用途**：元数据存储、用户管理、配置管理
- **特性**：ACID 事务、复杂查询、数据一致性
- **表结构**：
  - `tenants`：租户信息
  - `api_keys`：API 密钥
  - `knowledge_bases`：知识库元数据
  - `documents`：文档信息
  - `chunks`：文档块信息
  - `audit_logs`：审计日志

#### Qdrant（向量数据库）
- **用途**：向量存储和检索
- **特性**：高性能向量搜索、过滤支持、集群部署
- **隔离策略**：
  - Partition 模式：共享 Collection，通过字段过滤
  - Collection 模式：每租户独立 Collection
  - Auto 模式：根据数据量自动选择

### 6. 外部服务层

#### LLM 提供商集成
支持多种 LLM 提供商：
- **OpenAI**：GPT-3.5/4 系列
- **Ollama**：本地部署模型
- **Qwen**：阿里云通义千问
- **智谱 AI**：GLM 系列
- **DeepSeek**：DeepSeek 系列

#### Embedding 提供商
- **OpenAI**：text-embedding-ada-002
- **Ollama**：本地 embedding 模型
- **多云支持**：SiliconFlow、智谱等

## 数据流架构

### 文档摄取流程

```
文档上传 → 格式检测 → 内容提取 → 文档切分 → 向量化 → 存储索引
    ↓         ↓         ↓         ↓        ↓        ↓
  验证权限   解析内容   清理文本   算法切分  批量嵌入  多存储写入
```

### 检索查询流程

```
用户查询 → 查询预处理 → 向量检索 → 结果融合 → 重排序 → 上下文生成 → LLM 生成
    ↓         ↓          ↓        ↓        ↓        ↓         ↓
  权限验证   查询增强    多路检索   算法融合  可选重排  上下文构建  流式响应
```

## 多租户架构

### 租户隔离策略

#### 1. 应用层隔离
- 所有 API 请求通过 API Key 识别租户
- 数据库查询强制添加 `tenant_id` 过滤
- 业务逻辑层面的权限控制

#### 2. 数据层隔离
- **PostgreSQL**：通过 `tenant_id` 字段实现行级隔离
- **Qdrant**：支持三种隔离模式
  - Partition：共享 Collection + 字段过滤
  - Collection：每租户独立 Collection
  - Auto：自动选择最优策略

#### 3. 资源隔离
- API 限流：每个 API Key 独立限流配置
- 存储配额：租户级别的存储限制
- 计算资源：可配置的并发限制

### 租户管理

```python
# 租户创建
POST /admin/tenants
{
  "name": "company-name",
  "quota": {
    "max_knowledge_bases": 10,
    "max_documents": 1000,
    "max_storage_mb": 5000
  }
}

# 返回初始 admin API Key
{
  "tenant_id": "uuid",
  "api_key": "kb_sk_xxx",
  "role": "admin"
}
```

## 性能架构

### 异步处理

全面采用异步编程模式：

```python
# 数据库操作
async def get_knowledge_bases(tenant_id: str) -> List[KnowledgeBase]:
    async with get_db_session() as db:
        result = await db.execute(
            select(KnowledgeBase).where(KnowledgeBase.tenant_id == tenant_id)
        )
        return result.scalars().all()

# HTTP 客户端
async def call_embedding_api(texts: List[str]) -> List[List[float]]:
    async with httpx.AsyncClient() as client:
        response = await client.post(embedding_url, json={"texts": texts})
        return response.json()["embeddings"]
```

### 缓存策略

#### 1. 应用层缓存
- 租户信息缓存（Redis）
- API Key 验证结果缓存
- 知识库配置缓存

#### 2. 向量检索缓存
- 查询结果缓存
- 向量计算结果缓存
- 热点数据预加载

#### 3. LLM 调用缓存
- 相同查询结果缓存
- Embedding 结果缓存
- 生成内容缓存

### 批处理优化

#### 文档处理
- 批量文档上传
- 并行切分处理
- 批量向量化

#### 检索优化
- 批量向量查询
- 并行多路检索
- 结果流式返回

## 安全架构

### 认证安全
- API Key 使用 SHA256 哈希存储
- 支持 API Key 过期和轮换
- 请求签名验证（可选）

### 数据安全
- 传输层 TLS 加密
- 数据库连接加密
- 敏感数据脱敏

### 访问控制
- 基于角色的权限控制（RBAC）
- 租户级别的数据隔离
- API 限流和防护

### 审计日志
- 完整的 API 调用记录
- 数据访问审计
- 安全事件监控

## 监控架构

### 应用监控
- 结构化日志（JSON 格式）
- 请求追踪（X-Request-ID）
- 性能指标收集

### 基础设施监控
- 数据库性能监控
- 向量数据库监控
- 系统资源监控

### 业务监控
- 租户使用统计
- API 调用分析
- 错误率监控

## 扩展架构

### 水平扩展
- 无状态应用设计
- 负载均衡支持
- 数据库读写分离

### 组件扩展
- 可插拔算法框架
- 自定义中间件
- 第三方集成接口

### 部署扩展
- Docker 容器化
- Kubernetes 支持
- 云原生部署

## 技术选型

### 后端技术栈
- **Python 3.11+**：现代语言特性
- **FastAPI**：高性能异步框架
- **SQLAlchemy 2.0**：现代 ORM
- **Alembic**：数据库迁移
- **uv**：快速包管理

### 数据库选型
- **PostgreSQL**：成熟稳定的关系数据库
- **Qdrant**：专业的向量数据库
- **Redis**：高性能缓存（可选）

### AI/ML 框架
- **LlamaIndex**：RAG 框架集成
- **多提供商支持**：降低供应商锁定风险
- **标准接口**：OpenAI 兼容性

## 部署架构

### 开发环境
```bash
# 本地开发
docker-compose up -d  # 基础设施
uv run uvicorn app.main:app --reload  # API 服务
npm run dev  # 前端服务
```

### 生产环境
```yaml
# docker-compose.prod.yml
version: '3.8'
services:
  api:
    image: self-rag-pipeline:latest
    replicas: 3
    environment:
      - DATABASE_URL=postgresql://...
      - QDRANT_URL=http://qdrant:6333
  
  db:
    image: postgres:15
    volumes:
      - postgres_data:/var/lib/postgresql/data
  
  qdrant:
    image: qdrant/qdrant:v1.7.0
    volumes:
      - qdrant_data:/qdrant/storage
```

## 下一步

深入了解各个组件的详细设计：

- **[系统设计](./system-design)** - 详细的系统设计文档
- **[API 规范](./api-specification)** - 完整的 API 接口文档
- **[管道架构](./pipeline-architecture)** - 算法框架详细设计
- **[架构决策](./decisions)** - 重要的架构决策记录

---

想了解更多技术细节？查看 [系统设计](./system-design) 或 [API 规范](./api-specification)。