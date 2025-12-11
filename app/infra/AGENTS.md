# Infra 基础设施模块

向量存储、Embedding、LLM 和外部服务集成。

## 模块职责

- LLM 对话（Chat Completion）
- 向量化（Embedding）
- 重排（Rerank）
- 向量存储（Qdrant/Milvus/Elasticsearch）
- BM25 稀疏检索
- LlamaIndex 集成

## 核心文件

| 文件 | 说明 |
|------|------|
| `llm.py` | LLM 对话客户端（支持多种提供商） |
| `embeddings.py` | 文本向量化（支持多种提供商） |
| `rerank.py` | 重排模块（支持多种提供商） |
| `vector_store.py` | Qdrant 向量存储操作 |
| `bm25_store.py` | BM25 内存存储 |
| `llamaindex.py` | LlamaIndex 多后端集成 |

## 支持的模型提供商

| 提供商 | LLM | Embedding | Rerank | 说明 |
|--------|-----|-----------|--------|------|
| **Ollama** | ✅ | ✅ | ✅ | 本地部署，免费 |
| **OpenAI** | ✅ | ✅ | - | GPT-4, text-embedding-3 |
| **Gemini** | ✅ | ✅ | - | Google AI |
| **Qwen** | ✅ | ✅ | - | 阿里云 DashScope |
| **Kimi** | ✅ | - | - | 月之暗面 Moonshot |
| **DeepSeek** | ✅ | ✅ | - | DeepSeek |
| **智谱 AI** | ✅ | ✅ | ✅ | GLM 系列 |
| **SiliconFlow** | ✅ | ✅ | ✅ | 聚合多种开源模型 |
| **Cohere** | - | - | ✅ | 专业 Rerank 服务 |
| **vLLM** | ✅ | ✅ | ✅ | 自部署 vLLM 服务（OpenAI 兼容） |

## LLM 调用

```python
from app.infra.llm import chat_completion

# 简单调用
response = await chat_completion("你好，请介绍一下自己")

# 完整参数
response = await chat_completion(
    prompt="总结以下文档",
    system_prompt="你是一个专业的文档摘要助手",
    temperature=0.3,
    max_tokens=500,
)
```

## Embedding

```python
from app.infra.embeddings import get_embedding, get_embeddings

# 单个文本（使用环境变量配置）
vec = await get_embedding("什么是 RAG？")

# 批量文本
vecs = await get_embeddings(["文本1", "文本2"])

# 使用动态配置（知识库级别的 embedding 模型）
embedding_config = {
    "provider": "openai",
    "model": "text-embedding-3-small",
    "base_url": "https://api.openai.com/v1",
    "api_key": "sk-xxx",
}
vec = await get_embedding("什么是 RAG？", embedding_config=embedding_config)
```

### 动态 Embedding 配置

系统支持按知识库配置不同的 embedding 模型，确保入库和检索使用一致的模型：

| 配置来源 | 优先级 | 说明 |
|----------|--------|------|
| `embedding_config` 参数 | 高 | 来自知识库配置，动态传入 |
| 环境变量 | 低 | `EMBEDDING_PROVIDER`、`EMBEDDING_MODEL` |

**工作流程**：
1. 创建知识库时配置 embedding 模型
2. 入库时使用该配置进行向量化
3. 检索时自动从知识库配置读取，使用相同模型

## Rerank

```python
from app.infra.rerank import rerank_results

# 重排检索结果
reranked = await rerank_results(
    query="什么是机器学习",
    documents=["文档1内容", "文档2内容", ...],
    top_k=5,
)
# 返回: [{"index": 0, "score": 0.95, "text": "..."}, ...]
```

## 向量存储

### Qdrant（默认）
```python
from app.infra.vector_store import vector_store

# 插入向量
vector_store.upsert(tenant_id, kb_id, chunks)

# 搜索
results = vector_store.search(query, tenant_id, kb_ids, top_k=5)
```

### 多后端切换（LlamaIndex）
```python
from app.infra.llamaindex import build_index_by_store

# Qdrant（使用默认 embedding）
index = build_index_by_store("qdrant", tenant_id, kb_id)

# Milvus（带自定义 embedding 配置）
index = build_index_by_store(
    "milvus", 
    tenant_id, 
    kb_id, 
    params={"index_params": {"index_type": "IVF_PQ", ...}},
    embedding_config={"provider": "openai", "model": "text-embedding-3-small", ...}
)

# Elasticsearch（带自定义 embedding 配置）
index = build_index_by_store(
    "es", 
    tenant_id, 
    kb_id, 
    params={"body": {"mappings": {...}}},
    embedding_config=embedding_config
)
```

### LlamaIndex RealEmbedding

`RealEmbedding` 是 LlamaIndex 的 embedding 适配器，支持动态配置：

```python
from app.infra.llamaindex import RealEmbedding

# 使用环境变量配置
embed_model = RealEmbedding(dim=1024)

# 使用动态配置
embed_model = RealEmbedding(
    dim=1024,
    embedding_config={
        "provider": "ollama",
        "model": "bge-m3",
        "base_url": "http://localhost:11434",
    }
)
```

## BM25 存储

```python
from app.infra.bm25_store import bm25_store

# 插入文档
bm25_store.upsert_chunk(chunk_id, tenant_id, kb_id, text, metadata)

# 搜索
results = bm25_store.search(query, tenant_id, kb_ids, top_k=5)
```

注意：BM25 存储是内存实现，重启后需从数据库重建。

## 环境配置

### 模型提供商 API Keys

```bash
# Ollama（本地部署，无需 API Key）
OLLAMA_BASE_URL=http://localhost:11434

# OpenAI
OPENAI_API_KEY=sk-xxx
OPENAI_API_BASE=https://api.openai.com/v1  # 可选，自定义端点

# Google Gemini
GEMINI_API_KEY=AIzaSyXXX

# 阿里云通义千问 (DashScope)
QWEN_API_KEY=sk-xxx

# 月之暗面 Kimi (Moonshot)
KIMI_API_KEY=sk-xxx

# DeepSeek
DEEPSEEK_API_KEY=sk-xxx

# 智谱 AI (GLM)
ZHIPU_API_KEY=xxx

# SiliconFlow
SILICONFLOW_API_KEY=sk-xxx

# Cohere (Rerank)
COHERE_API_KEY=xxx
```

### 模型配置

```bash
# LLM 配置
LLM_PROVIDER=ollama          # ollama/openai/gemini/qwen/kimi/deepseek/zhipu/siliconflow
LLM_MODEL=qwen3:14b
LLM_TEMPERATURE=0.7
LLM_MAX_TOKENS=2048

# Embedding 配置
EMBEDDING_PROVIDER=ollama    # ollama/openai/gemini/qwen/zhipu/siliconflow
EMBEDDING_MODEL=bge-m3
EMBEDDING_DIM=1024           # 向量维度

# Rerank 配置
RERANK_PROVIDER=none         # ollama/cohere/zhipu/siliconflow/none
RERANK_MODEL=
RERANK_TOP_K=10
```

### 向量存储

```bash
# Qdrant
QDRANT_URL=http://localhost:6333
QDRANT_COLLECTION_PREFIX=kb_

# Milvus（可选）
MILVUS_HOST=localhost
MILVUS_PORT=19530

# Elasticsearch（可选）
ES_HOSTS=http://localhost:9200
ES_INDEX_PREFIX=kb_
```

## 常见向量维度

| 模型 | 维度 |
|------|------|
| OpenAI text-embedding-3-small | 1536 |
| OpenAI text-embedding-3-large | 3072 |
| BGE-M3 / BGE-Large-zh | 1024 |
| Qwen text-embedding-v3 | 1024 |
| Gemini text-embedding-004 | 768 |

## 添加新模型提供商

1. 在 `config.py` 添加提供商的 API Key 和 Base URL 配置
2. 在 `config.py` 的 `_get_provider_config()` 方法中添加新分支
3. 在 `embeddings.py` / `llm.py` / `rerank.py` 中实现对应的调用逻辑
4. 更新 `.env.example` 添加配置示例
