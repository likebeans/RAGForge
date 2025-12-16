# Schemas 数据模型模块

Pydantic 请求/响应模型定义。

## 模块职责

- 定义 API 请求体结构
- 定义 API 响应体结构
- 数据验证和序列化

## 核心文件

| 文件 | 说明 |
|------|------|
| `tenant.py` | 租户相关 schema（Admin API） |
| `api_key.py` | API Key 相关 schema（含角色） |
| `kb.py` | 知识库相关 schema |
| `document.py` | 文档相关 schema |
| `query.py` | 检索相关 schema |
| `rag.py` | RAG 生成相关 schema |
| `config.py` | 知识库配置 schema（Chunker/Retriever/Embedding/LLM） |
| `internal.py` | **服务层内部参数模型**（与 API Schema 解耦） |
| `pipeline.py` | Pipeline Playground API schema |

## Schema 命名规范

| 后缀 | 用途 | 示例 |
|------|------|------|
| `Create` | 创建请求 | `KnowledgeBaseCreate` |
| `Update` | 更新请求 | `KnowledgeBaseUpdate` |
| `Response` | 响应模型 | `KnowledgeBaseResponse` |
| `List` | 列表响应 | `KnowledgeBaseList` |

## 使用示例

### 定义 Schema
```python
from pydantic import BaseModel, Field

class ItemCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=255)
    description: str | None = None

class ItemResponse(BaseModel):
    id: str
    name: str
    created_at: datetime
    
    class Config:
        from_attributes = True  # 支持从 ORM 对象转换
```

### 在路由中使用
```python
@router.post("/items", response_model=ItemResponse)
async def create_item(data: ItemCreate, db: AsyncSession = Depends(get_db)):
    item = Item(**data.model_dump())
    db.add(item)
    await db.commit()
    return item
```

## 常用字段验证

```python
from pydantic import Field, validator

class MySchema(BaseModel):
    # 字符串长度限制
    name: str = Field(..., min_length=1, max_length=100)
    
    # 数值范围
    top_k: int = Field(default=5, ge=1, le=100)
    
    # 可选字段
    description: str | None = None
    
    # 列表
    kb_ids: list[str] = Field(..., min_length=1)
    
    # 自定义验证
    @validator("name")
    def validate_name(cls, v):
        if not v.strip():
            raise ValueError("name cannot be empty")
        return v.strip()
```

## 注意事项

- 请求模型必须验证所有输入
- 响应模型设置 `from_attributes = True` 以支持 ORM 转换
- 敏感字段（如密码哈希）不应出现在响应模型中
- 使用 `Field` 提供字段描述，自动生成 OpenAPI 文档

---

## 服务层内部参数模型 (internal.py)

`internal.py` 定义服务层函数的参数对象，与 API Schema 解耦，提供更好的参数验证和文档化。

### 设计目的

- **解耦**：服务层参数与 API 请求/响应模型分离，便于独立演进
- **验证**：使用 Pydantic `Field` 提供参数验证（范围、长度等）
- **文档化**：每个字段带描述，提升代码可读性

### 内部参数模型

| 模型 | 说明 | 对应服务函数 |
|------|------|-------------|
| `LLMParams` | LLM 调用参数 | 通用 LLM 调用 |
| `RetrieveParams` | 检索参数 | `services.query.retrieve_chunks` |
| `RAGParams` | RAG 生成参数 | `services.rag.generate_rag_response` |
| `IngestionParams` | 文档摄取参数 | `services.ingestion.ingest_document` |
| `RetryChunksParams` | 重试失败 chunks 参数 | `services.ingestion.retry_failed_chunks` |

### 使用示例

```python
from app.schemas.internal import RAGParams, RetrieveParams, IngestionParams

# RAG 生成
params = RAGParams(
    query="问题内容",
    kb_ids=["kb1", "kb2"],
    top_k=5,
    temperature=0.7,
)
result = await generate_rag_response(session, tenant_id, params)

# 检索
params = RetrieveParams(
    query="搜索内容",
    top_k=10,
    score_threshold=0.5,
    metadata_filter={"source": "pdf"},
)
chunks, retriever_name, acl_blocked = await retrieve_chunks(
    tenant_id=tenant_id,
    kbs=kbs,
    params=params,
    session=session,
)
if acl_blocked:
    print("检索结果被 ACL 过滤")

# 文档摄取
params = IngestionParams(
    title="文档标题",
    content="文档内容...",
    metadata={"author": "张三"},
    source="manual",
    generate_doc_summary=True,
)
result = await ingest_document(session, tenant_id=tenant_id, kb=kb, params=params)
```

### 字段定义规范

```python
from pydantic import BaseModel, Field

class MyParams(BaseModel):
    """参数描述"""
    
    # 必填字段，带验证
    query: str = Field(
        ...,                    # ... 表示必填
        min_length=1,           # 最小长度
        description="查询语句"   # 字段描述
    )
    
    # 带范围的数值
    top_k: int = Field(
        default=5,              # 默认值
        ge=1, le=100,           # 范围限制
        description="返回数量"
    )
    
    # 可选字段
    score_threshold: float | None = Field(
        default=None,
        ge=0.0, le=1.0,
        description="分数阈值"
    )
```

### API 路由中的使用模式

```python
# routes/query.py
from app.schemas.internal import RetrieveParams

@router.post("/v1/retrieve")
async def retrieve(payload: RetrieveRequest, ...):
    # 从 API 请求构建内部参数对象
    params = RetrieveParams(
        query=payload.query,
        top_k=payload.top_k,
        score_threshold=payload.score_threshold,
        metadata_filter=payload.metadata_filter,
        retriever_override=payload.retriever_override,
    )
    
    # 调用服务层
    results, retriever_name, acl_blocked = await retrieve_chunks(
        tenant_id=tenant.id,
        kbs=kbs,
        params=params,
        session=db,
    )
    if acl_blocked:
        raise HTTPException(status_code=403, detail="检索结果被 ACL 过滤")
```

---

## 模型覆盖配置 (config.py)

`config.py` 定义 LLM/Embedding/Rerank 的覆盖配置，支持请求级动态切换模型。

### EmbeddingOverrideConfig

用于请求级覆盖 Embedding 配置，优先级最高。

```python
class EmbeddingOverrideConfig(BaseModel):
    provider: EmbeddingProvider  # 必填：提供商（ollama/openai/siliconflow 等）
    model: str                   # 必填：模型名称
    api_key: str | None = None   # 可选：API Key（未指定时使用环境变量）
    base_url: str | None = None  # 可选：API Base URL
```

**配置优先级**：`请求参数 > 知识库配置 > 环境变量`

### LLMConfig

用于请求级覆盖 LLM 配置。

```python
class LLMConfig(BaseModel):
    provider: LLMProvider        # 必填：提供商
    model: str                   # 必填：模型名称
    api_key: str | None = None   # 可选：API Key
    base_url: str | None = None  # 可选：API Base URL
```

### 参数传递流程

前端通过 Playground API 传递 Embedding 配置到检索器：

```
Frontend (embeddingApiKey/embeddingBaseUrl)
    ↓
PlaygroundRunRequest.embedding_override
    ↓
RAGParams.embedding_override
    ↓
RetrieveParams.embedding_override
    ↓
Retriever (dense/hybrid/fusion 等)
```

**使用示例**：
```python
# Pipeline Playground API 请求
{
    "query": "问题内容",
    "knowledge_base_ids": ["kb1"],
    "embedding_override": {
        "provider": "siliconflow",
        "model": "BAAI/bge-m3",
        "api_key": "sk-xxx",
        "base_url": "https://api.siliconflow.cn/v1"
    }
}

# 后端路由传递到 RAGParams
rag_params = RAGParams(
    query=payload.query,
    kb_ids=payload.knowledge_base_ids,
    embedding_override=payload.embedding_override,  # 传递给检索
)

# RAG 服务传递到 RetrieveParams
retrieve_params = RetrieveParams(
    query=params.query,
    embedding_override=params.embedding_override,
)

# 检索服务传递给检索器
retriever = get_retriever(params.retriever_override)
results = await retriever.retrieve(
    ...,
    embedding_config=params.embedding_override,  # 检索器使用
)
```

**注意事项**：
- 前端未传递 `api_key` 时，后端自动使用环境变量（如 `SILICONFLOW_API_KEY`）
- 确保检索时使用的 Embedding 模型与入库时一致，否则向量空间不匹配
