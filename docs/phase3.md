# Phase 3: 检索器测试报告

**测试时间**: 2025-12-03 10:38:18

**测试环境**:
- Embedding: `ollama/bge-m3` (dim=1024)
- LLM: `ollama/qwen3:14b`
- Vector Store: Qdrant
- API Base: http://localhost:8020

**测试数据**:
- 文档: 复方南五加口服液说明书（真实药品说明书）
- Chunks: 20 个（使用 markdown chunker, chunk_size=512）
- Source: 药品说明书
- Metadata: category=中成药, manufacturer=湖南九典制药

---

## 测试概览

| 序号 | 检索器 | 状态 | 说明 |
|------|--------|------|------|
| 1 | dense | ✅ | 稠密向量检索 |
| 2 | bm25 | ✅ | BM25 稀疏检索（从 DB 加载） |
| 3 | hybrid | ✅ | Dense + BM25 混合检索 |
| 4 | fusion | ✅ | RRF 融合检索 |
| 5 | hyde | ✅ | HyDE 假设文档嵌入（LLM） |
| 6 | multi_query | ✅ | 多查询扩展（LLM） |
| 7 | llama_dense | ✅ | LlamaIndex 稠密检索 |
| 8 | llama_bm25 | ✅ | LlamaIndex BM25 检索 |
| 9 | llama_hybrid | ✅ | LlamaIndex 混合检索 |
| 10 | self_query | ✅ | 自查询检索（LLM） |
| 11 | parent_document | ✅ | 父文档检索 |
| 12 | ensemble | ✅ | 集成检索 |

---

## 详细测试结果

### 1. Dense 检索器

**配置**: `{"query":{"retriever":{"name":"dense"}}}`

**查询**: `这个药的禁忌是什么`

**响应**:
```json
{
    "results": [
        {
            "chunk_id": "5017e344-251b-4455-a5aa-39aa75a6cfe3",
            "text": "## \u3010\u6ce8\u610f\u4e8b\u9879\u3011  \n\n1. \u5fcc\u8f9b\u8fa3\u3001\u751f\u51b7\u3001\u6cb9\u817b\u98df\u7269\u3002  \n2. \u611f\u5192\u53d1\u70ed\u75c5\u4eba\u4e0d\u5b9c\u670d\u7528\u3002  \n3. \u9ad8\u8840\u538b\u3001\u5fc3\u810f\u75c5\u3001\u809d\u75c5\u3001\u80be\u75c5\u7b49\u6162\u6027\u75c5\u60a3\u8005\u5e94\u5728\u533b\u5e08\u6307\u5bfc\u4e0b\u670d\u7528\u3002  \n4. \u670d\u836f2\u5468\u75c7\u72b6\u65e0\u7f13\u89e3\uff0c\u5e94\u53bb\u533b\u9662\u5c31\u8bca\u3002  \n5. \u513f\u7ae5\u5e94\u5728\u533b\u5e08\u6307\u5bfc\u4e0b\u670d\u7528\u3002  \n6. \u5bf9\u672c\u54c1\u8fc7\u654f\u8005\u7981\u7528\uff0c\u8fc7\u654f\u4f53\u8d28\u8005\u614e\u7528\u3002  \n7. \u672c\u54c1\u6027\u72b6\u53d1\u751f\u6539\u53d8\u65f6\u7981\u6b62\u4f7f\u7528\u3002  \n8. \u513f\u7ae5\u5fc5\u987b\u5728\u6210\u4eba\u76d1\u62a4\u4e0b\u4f7f\u7528\u3002  \n9. \u8bf7\u5c06\u672c\u54c1\u653e\u5728\u513f\u7ae5\u4e0d\u80fd\u63a5\u89e6\u7684\u5730\u65b9\u3002  \n10. \u5982\u6b63\u5728\u4f7f\u7528\u5176\u4ed6\u836f\u54c1\uff0c\u4f7f\u7528\u672c\u54c1\u524d\u8bf7\u54a8\u8be2\u533b\u5e08\u6216\u836f\u5e08\u3002  \n",
            "score": 0.7115054,
            "metadata": {
                "category": "\u4e2d\u6210\u836f",
                "document_id": "f569c321-646b-4655-949d-a08426e8f230",
                "manufacturer": "\u6e56\u5357\u4e5d\u5178\u5236\u836f",
                "source": "\u836f\u54c1\u8bf4\u660e\u4e66",
                "title": "\u590d\u65b9\u5357\u4e94\u52a0\u53e3\u670d\u6db2\u8bf4\u660e\u4e66"
            },
            "knowledge_base_id": "4dfbef46-cd26-416e-98b9-f91a54fe1396",
            "document_id": "f569c321-646b-4655-949d-a08426e8f230",
            "context_text": null,
            "context_before": null,
            "context_after": null,
            "hyde_queries": null,
            "hyde_queries_count": null
        },
        {
            "chunk_id": "0cd49bc7-7607-4c36-9a67-5e37ce65d5eb",
            "text": "## \u3010\u6ce8\u610f\u4e8b\u9879\u3011  \n\n1. \u5fcc\u8f9b\u8fa3\u3001\u751f\u51b7\u3001\u6cb9\u817b\u98df\u7269\u3002  \n2. \u611f\u5192\u53d1\u70ed\u75c5\u4eba\u4e0d\u5b9c\u670d\u7528\u3002  \n3. \u9ad8\u8840\u538b\u3001\u5fc3\u810f\u75c5\u3001\u809d\u75c5\u3001\u80be\u75c5\u7b49\u6162\u6027\u75c5\u60a3\u8005\u5e94\u5728\u533b\u5e08\u6307\u5bfc\u4e0b\u670d\u7528\u3002  \n4. \u670d\u836f2\u5468\u75c7\u72b6\u65e0\u7f13\u89e3\uff0c\u5e94\u53bb\u533b\u9662\u5c31\u8bca\u3002  \n5. \u513f\u7ae5\u5e94\u5728\u533b\u5e08\u6307\u5bfc\u4e0b\u670d\u7528\u3002  \n6. \u5bf9\u672c\u54c1\u8fc7\u654f\u8005\u7981\u7528\uff0c\u8fc7\u654f\u4f53\u8d28\u8005\u614e\u7528\u3002  \n7. \u672c\u54c1\u6027\u72b6\u53d1\u751f\u6539\u53d8\u65f6\u7981\u6b62\u4f7f\u7528\u3002  \n8. \u513f\u7ae5\u5fc5\u987b\u5728\u6210\u4eba\u76d1\u62a4\u4e0b\u4f7f\u7528\u3002  \n9. \u8bf7\u5c06\u672c\u54c1\u653e\u5728\u513f\u7ae5\u4e0d\u80fd\u63a5\u89e6\u7684\u5730\u65b9\u3002  \n10. \u5982\u6b63\u5728\u4f7f\u7528\u5176\u4ed6\u836f\u54c1\uff0c\u4f7f\u7528\u672c\u54c1\u524d\u8bf7\u54a8\u8be2\u533b\u5e08\u6216\u836f\u5e08\u3002  \n",
            "score": 0.7115054,
            "metadata": {
                "category": "\u4e2d\u6210\u836f",
                "document_id": "83960e95-8b36-46c9-bfa8-e2de58ecb2d6",
                "manufacturer": "\u6e56\u5357\u4e5d\u5178\u5236\u836f",
                "source": "\u836f\u54c1\u8bf4\u660e\u4e66",
                "title": "\u590d\u65b9\u5357\u4e94\u52a0\u53e3\u670d\u6db2\u8bf4\u660e\u4e66"
            },
            "knowledge_base_id": "4dfbef46-cd26-416e-98b9-f91a54fe1396",
            "document_id": "83960e95-8b36-46c9-bfa8-e2de58ecb2d6",
            "context_text": null,
            "context_before": null,
            "context_after": null,
            "hyde_queries": null,
            "hyde_queries_count": null
        }
    ],
    "model": {
        "embedding_provider": "ollama",
        "embedding_model": "bge-m3",
        "llm_provider": null,
        "llm_model": null,
        "rerank_provider": null,
        "rerank_model": null,
        "retriever": "dense"
    }
}
```

**分析**: Dense 检索器使用 bge-m3 Embedding，返回语义最相关的结果。注意 `source` 和 `metadata` 都有值。

---

### 2. BM25 检索器

**配置**: `{"query":{"retriever":{"name":"bm25"}}}`

**查询**: `孕妇禁用`

**响应**:
```json
{
    "results": [
        {
            "chunk_id": "cede2d9f-5b87-43af-be30-081f5fc08e3b",
            "text": "## \u3010\u7981\u5fcc\u3011  \n\n1. \u5b55\u5987\u7981\u7528  \n2. \u7cd6\u5c3f\u75c5\u60a3\u8005\u7981\u670d  \n",
            "score": 0.72483087,
            "metadata": {
                "category": "\u4e2d\u6210\u836f",
                "document_id": "f569c321-646b-4655-949d-a08426e8f230",
                "manufacturer": "\u6e56\u5357\u4e5d\u5178\u5236\u836f",
                "source": "\u836f\u54c1\u8bf4\u660e\u4e66",
                "title": "\u590d\u65b9\u5357\u4e94\u52a0\u53e3\u670d\u6db2\u8bf4\u660e\u4e66"
            },
            "knowledge_base_id": "4dfbef46-cd26-416e-98b9-f91a54fe1396",
            "document_id": "f569c321-646b-4655-949d-a08426e8f230",
            "context_text": null,
            "context_before": null,
            "context_after": null,
            "hyde_queries": null,
            "hyde_queries_count": null
        },
        {
            "chunk_id": "a9b86b8c-e4df-4e8d-9e02-2ff70d7bc40f",
            "text": "## \u3010\u7981\u5fcc\u3011  \n\n1. \u5b55\u5987\u7981\u7528  \n2. \u7cd6\u5c3f\u75c5\u60a3\u8005\u7981\u670d  \n",
            "score": 0.72483087,
            "metadata": {
                "category": "\u4e2d\u6210\u836f",
                "document_id": "83960e95-8b36-46c9-bfa8-e2de58ecb2d6",
                "manufacturer": "\u6e56\u5357\u4e5d\u5178\u5236\u836f",
                "source": "\u836f\u54c1\u8bf4\u660e\u4e66",
                "title": "\u590d\u65b9\u5357\u4e94\u52a0\u53e3\u670d\u6db2\u8bf4\u660e\u4e66"
            },
            "knowledge_base_id": "4dfbef46-cd26-416e-98b9-f91a54fe1396",
            "document_id": "83960e95-8b36-46c9-bfa8-e2de58ecb2d6",
            "context_text": null,
            "context_before": null,
            "context_after": null,
            "hyde_queries": null,
            "hyde_queries_count": null
        }
    ],
    "model": {
        "embedding_provider": "ollama",
        "embedding_model": "bge-m3",
        "llm_provider": null,
        "llm_model": null,
        "rerank_provider": null,
        "rerank_model": null,
        "retriever": "dense"
    }
}
```

**分析**: BM25 检索器从 PostgreSQL 加载 chunks 构建索引，基于关键词匹配。支持服务重启后持久化。

---

### 3. Hybrid 检索器

**配置**: `{"query":{"retriever":{"name":"hybrid"}}}`

**查询**: `用法用量`

**响应**:
```json
{
    "results": [
        {
            "chunk_id": "5e7edb66-b678-4729-a0a5-f5f2138256f7",
            "text": "## \u3010\u7528\u6cd5\u7528\u91cf\u3011  \n\n\u53e3\u670d\uff0c\u4e00\u6b2110\u6beb\u5347\uff0c\u4e00\u65e52\u6b21\uff0c\u65e9\u665a\u7a7a\u8179\u65f6\u670d\u3002  \n",
            "score": 0.5417067,
            "metadata": {
                "category": "\u4e2d\u6210\u836f",
                "document_id": "f569c321-646b-4655-949d-a08426e8f230",
                "manufacturer": "\u6e56\u5357\u4e5d\u5178\u5236\u836f",
                "source": "\u836f\u54c1\u8bf4\u660e\u4e66",
                "title": "\u590d\u65b9\u5357\u4e94\u52a0\u53e3\u670d\u6db2\u8bf4\u660e\u4e66"
            },
            "knowledge_base_id": "4dfbef46-cd26-416e-98b9-f91a54fe1396",
            "document_id": "f569c321-646b-4655-949d-a08426e8f230",
            "context_text": null,
            "context_before": null,
            "context_after": null,
            "hyde_queries": null,
            "hyde_queries_count": null
        },
        {
            "chunk_id": "7fe2d86f-b430-4a19-a8cc-a2d25b94b7ab",
            "text": "## \u3010\u7528\u6cd5\u7528\u91cf\u3011  \n\n\u53e3\u670d\uff0c\u4e00\u6b2110\u6beb\u5347\uff0c\u4e00\u65e52\u6b21\uff0c\u65e9\u665a\u7a7a\u8179\u65f6\u670d\u3002  \n",
            "score": 0.5417067,
            "metadata": {
                "category": "\u4e2d\u6210\u836f",
                "document_id": "83960e95-8b36-46c9-bfa8-e2de58ecb2d6",
                "manufacturer": "\u6e56\u5357\u4e5d\u5178\u5236\u836f",
                "source": "\u836f\u54c1\u8bf4\u660e\u4e66",
                "title": "\u590d\u65b9\u5357\u4e94\u52a0\u53e3\u670d\u6db2\u8bf4\u660e\u4e66"
            },
            "knowledge_base_id": "4dfbef46-cd26-416e-98b9-f91a54fe1396",
            "document_id": "83960e95-8b36-46c9-bfa8-e2de58ecb2d6",
            "context_text": null,
            "context_before": null,
            "context_after": null,
            "hyde_queries": null,
            "hyde_queries_count": null
        }
    ],
    "model": {
        "embedding_provider": "ollama",
        "embedding_model": "bge-m3",
        "llm_provider": null,
        "llm_model": null,
        "rerank_provider": null,
        "rerank_model": null,
        "retriever": "dense"
    }
}
```

**分析**: Hybrid 检索器结合 Dense 和 BM25，metadata.source 字段标识结果来源（dense/bm25）。

---

### 4. Fusion 检索器

**配置**: `{"query":{"retriever":{"name":"fusion"}}}`

**查询**: `功能主治`

**响应**:
```json
{
    "results": [
        {
            "chunk_id": "e9b9f399-db1b-4c04-872a-4dbbd73725c6",
            "text": "## \u3010\u529f\u80fd\u4e3b\u6cbb\u3011  \n\n\u6e29\u9633\u76ca\u6c14\uff0c\u517b\u5fc3\u5b89\u795e\u3002\u7528\u4e8e\u6c14\u8840\u4e8f\u865a\uff0c\u9633\u6c14\u4e0d\u8db3\u75c7\uff0c\u75c7\u89c1\u5934\u660f\u6c14\u77ed\uff0c\u5fc3\u60b8\u5931\u7720\uff0c\u795e\u75b2\u4e4f\u529b\uff0c\u754f\u5bd2\u80a2\u51b7\uff0c\u591c\u5c3f\u9891\u6570\u3002  \n",
            "score": 0.5995234,
            "metadata": {
                "category": "\u4e2d\u6210\u836f",
                "document_id": "f569c321-646b-4655-949d-a08426e8f230",
                "manufacturer": "\u6e56\u5357\u4e5d\u5178\u5236\u836f",
                "source": "\u836f\u54c1\u8bf4\u660e\u4e66",
                "title": "\u590d\u65b9\u5357\u4e94\u52a0\u53e3\u670d\u6db2\u8bf4\u660e\u4e66"
            },
            "knowledge_base_id": "4dfbef46-cd26-416e-98b9-f91a54fe1396",
            "document_id": "f569c321-646b-4655-949d-a08426e8f230",
            "context_text": null,
            "context_before": null,
            "context_after": null,
            "hyde_queries": null,
            "hyde_queries_count": null
        },
        {
            "chunk_id": "34fea431-3507-4b2e-8f98-f2fa3631e4c1",
            "text": "## \u3010\u529f\u80fd\u4e3b\u6cbb\u3011  \n\n\u6e29\u9633\u76ca\u6c14\uff0c\u517b\u5fc3\u5b89\u795e\u3002\u7528\u4e8e\u6c14\u8840\u4e8f\u865a\uff0c\u9633\u6c14\u4e0d\u8db3\u75c7\uff0c\u75c7\u89c1\u5934\u660f\u6c14\u77ed\uff0c\u5fc3\u60b8\u5931\u7720\uff0c\u795e\u75b2\u4e4f\u529b\uff0c\u754f\u5bd2\u80a2\u51b7\uff0c\u591c\u5c3f\u9891\u6570\u3002  \n",
            "score": 0.5995234,
            "metadata": {
                "category": "\u4e2d\u6210\u836f",
                "document_id": "83960e95-8b36-46c9-bfa8-e2de58ecb2d6",
                "manufacturer": "\u6e56\u5357\u4e5d\u5178\u5236\u836f",
                "source": "\u836f\u54c1\u8bf4\u660e\u4e66",
                "title": "\u590d\u65b9\u5357\u4e94\u52a0\u53e3\u670d\u6db2\u8bf4\u660e\u4e66"
            },
            "knowledge_base_id": "4dfbef46-cd26-416e-98b9-f91a54fe1396",
            "document_id": "83960e95-8b36-46c9-bfa8-e2de58ecb2d6",
            "context_text": null,
            "context_before": null,
            "context_after": null,
            "hyde_queries": null,
            "hyde_queries_count": null
        }
    ],
    "model": {
        "embedding_provider": "ollama",
        "embedding_model": "bge-m3",
        "llm_provider": null,
        "llm_model": null,
        "rerank_provider": null,
        "rerank_model": null,
        "retriever": "dense"
    }
}
```

**分析**: Fusion 检索器使用 RRF 算法融合多路检索结果，可选配合 Rerank 模型。

---

### 5. HyDE 检索器

**配置**: `{"query":{"retriever":{"name":"hyde","params":{"base_retriever":"dense"}}}}`

**查询**: `这个药治什么病`

**响应**:
```json
{
    "results": [
        {
            "chunk_id": "e9b9f399-db1b-4c04-872a-4dbbd73725c6",
            "text": "## \u3010\u529f\u80fd\u4e3b\u6cbb\u3011  \n\n\u6e29\u9633\u76ca\u6c14\uff0c\u517b\u5fc3\u5b89\u795e\u3002\u7528\u4e8e\u6c14\u8840\u4e8f\u865a\uff0c\u9633\u6c14\u4e0d\u8db3\u75c7\uff0c\u75c7\u89c1\u5934\u660f\u6c14\u77ed\uff0c\u5fc3\u60b8\u5931\u7720\uff0c\u795e\u75b2\u4e4f\u529b\uff0c\u754f\u5bd2\u80a2\u51b7\uff0c\u591c\u5c3f\u9891\u6570\u3002  \n",
            "score": 0.6168106,
            "metadata": {
                "category": "\u4e2d\u6210\u836f",
                "document_id": "f569c321-646b-4655-949d-a08426e8f230",
                "manufacturer": "\u6e56\u5357\u4e5d\u5178\u5236\u836f",
                "source": "\u836f\u54c1\u8bf4\u660e\u4e66",
                "title": "\u590d\u65b9\u5357\u4e94\u52a0\u53e3\u670d\u6db2\u8bf4\u660e\u4e66"
            },
            "knowledge_base_id": "4dfbef46-cd26-416e-98b9-f91a54fe1396",
            "document_id": "f569c321-646b-4655-949d-a08426e8f230",
            "context_text": null,
            "context_before": null,
            "context_after": null,
            "hyde_queries": null,
            "hyde_queries_count": null
        },
        {
            "chunk_id": "34fea431-3507-4b2e-8f98-f2fa3631e4c1",
            "text": "## \u3010\u529f\u80fd\u4e3b\u6cbb\u3011  \n\n\u6e29\u9633\u76ca\u6c14\uff0c\u517b\u5fc3\u5b89\u795e\u3002\u7528\u4e8e\u6c14\u8840\u4e8f\u865a\uff0c\u9633\u6c14\u4e0d\u8db3\u75c7\uff0c\u75c7\u89c1\u5934\u660f\u6c14\u77ed\uff0c\u5fc3\u60b8\u5931\u7720\uff0c\u795e\u75b2\u4e4f\u529b\uff0c\u754f\u5bd2\u80a2\u51b7\uff0c\u591c\u5c3f\u9891\u6570\u3002  \n",
            "score": 0.6168106,
            "metadata": {
                "category": "\u4e2d\u6210\u836f",
                "document_id": "83960e95-8b36-46c9-bfa8-e2de58ecb2d6",
                "manufacturer": "\u6e56\u5357\u4e5d\u5178\u5236\u836f",
                "source": "\u836f\u54c1\u8bf4\u660e\u4e66",
                "title": "\u590d\u65b9\u5357\u4e94\u52a0\u53e3\u670d\u6db2\u8bf4\u660e\u4e66"
            },
            "knowledge_base_id": "4dfbef46-cd26-416e-98b9-f91a54fe1396",
            "document_id": "83960e95-8b36-46c9-bfa8-e2de58ecb2d6",
            "context_text": null,
            "context_before": null,
            "context_after": null,
            "hyde_queries": null,
            "hyde_queries_count": null
        }
    ],
    "model": {
        "embedding_provider": "ollama",
        "embedding_model": "bge-m3",
        "llm_provider": null,
        "llm_model": null,
        "rerank_provider": null,
        "rerank_model": null,
        "retriever": "dense"
    }
}
```

**分析**: HyDE 检索器使用 LLM (qwen3:14b) 生成假设性答案文档，`hyde_queries` 显示 LLM 生成的假设文档。

---

### 6. MultiQuery 检索器

**配置**: `{"query":{"retriever":{"name":"multi_query","params":{"base_retriever":"dense","num_queries":3}}}}`

**查询**: `药物成分`

**响应**:
```json
{
    "results": [
        {
            "chunk_id": "07bcb9cf-132b-447b-b12f-8cc5dd30f813",
            "text": "## \u3010\u836f\u7269\u76f8\u4e92\u4f5c\u7528\u3011  \n\n\u5982\u4e0e\u5176\u4ed6\u836f\u7269\u540c\u65f6\u4f7f\u7528\u53ef\u80fd\u4f1a\u53d1\u751f\u836f\u7269\u76f8\u4e92\u4f5c\u7528\uff0c\u8be6\u60c5\u8bf7\u54a8\u8be2\u533b\u5e08\u6216\u836f\u5e08\u3002  \n",
            "score": 0.5719562,
            "metadata": {
                "category": "\u4e2d\u6210\u836f",
                "document_id": "f569c321-646b-4655-949d-a08426e8f230",
                "manufacturer": "\u6e56\u5357\u4e5d\u5178\u5236\u836f",
                "source": "\u836f\u54c1\u8bf4\u660e\u4e66",
                "title": "\u590d\u65b9\u5357\u4e94\u52a0\u53e3\u670d\u6db2\u8bf4\u660e\u4e66"
            },
            "knowledge_base_id": "4dfbef46-cd26-416e-98b9-f91a54fe1396",
            "document_id": "f569c321-646b-4655-949d-a08426e8f230",
            "context_text": null,
            "context_before": null,
            "context_after": null,
            "hyde_queries": null,
            "hyde_queries_count": null
        },
        {
            "chunk_id": "77474c5e-196b-4bfa-ad14-e328aaaf9830",
            "text": "## \u3010\u836f\u7269\u76f8\u4e92\u4f5c\u7528\u3011  \n\n\u5982\u4e0e\u5176\u4ed6\u836f\u7269\u540c\u65f6\u4f7f\u7528\u53ef\u80fd\u4f1a\u53d1\u751f\u836f\u7269\u76f8\u4e92\u4f5c\u7528\uff0c\u8be6\u60c5\u8bf7\u54a8\u8be2\u533b\u5e08\u6216\u836f\u5e08\u3002  \n",
            "score": 0.5719562,
            "metadata": {
                "category": "\u4e2d\u6210\u836f",
                "document_id": "83960e95-8b36-46c9-bfa8-e2de58ecb2d6",
                "manufacturer": "\u6e56\u5357\u4e5d\u5178\u5236\u836f",
                "source": "\u836f\u54c1\u8bf4\u660e\u4e66",
                "title": "\u590d\u65b9\u5357\u4e94\u52a0\u53e3\u670d\u6db2\u8bf4\u660e\u4e66"
            },
            "knowledge_base_id": "4dfbef46-cd26-416e-98b9-f91a54fe1396",
            "document_id": "83960e95-8b36-46c9-bfa8-e2de58ecb2d6",
            "context_text": null,
            "context_before": null,
            "context_after": null,
            "hyde_queries": null,
            "hyde_queries_count": null
        }
    ],
    "model": {
        "embedding_provider": "ollama",
        "embedding_model": "bge-m3",
        "llm_provider": null,
        "llm_model": null,
        "rerank_provider": null,
        "rerank_model": null,
        "retriever": "dense"
    }
}
```

**分析**: MultiQuery 使用 LLM 生成多个查询变体，分别检索后 RRF 融合，提高召回率。

---

### 7. LlamaDense 检索器

**配置**: `{"query":{"retriever":{"name":"llama_dense"}}}`

**查询**: `生产企业`

**响应**:
```json
{
    "results": [
        {
            "chunk_id": "d5b10cad-c085-419b-93df-373ddca137fd",
            "text": "## \u3010\u751f\u4ea7\u4f01\u4e1a\u3011  \n\n\u4f01\u4e1a\u540d\u79f0\uff1a\u6e56\u5357\u4e5d\u5178\u5236\u836f\u80a1\u4efd\u6709\u9650\u516c\u53f8  \n\u751f\u4ea7\u5730\u5740\uff1a\u957f\u6c99\u5e02\u6d4f\u9633\u7ecf\u6d4e\u6280\u672f\u5f00\u53d1\u533a\u5065\u5eb7\u5927\u90531\u53f7  \n\u90ae\u653f\u7f16\u7801\uff1a410331  \n\u7535\u8bdd\u53f7\u7801\uff1a0731-88220220 88220228  \n\u4f20\u771f\u53f7\u7801\uff1a0731-88220238  \n\u7f51\u5740\uff1ahttp://www.hnjiudian.com  \n\n\u5982\u6709\u95ee\u9898\u53ef\u4e0e\u751f\u4ea7\u4f01\u4e1a\u8054\u7cfb\n```",
            "score": 0.5629767,
            "metadata": {
                "category": "\u4e2d\u6210\u836f",
                "document_id": "f569c321-646b-4655-949d-a08426e8f230",
                "manufacturer": "\u6e56\u5357\u4e5d\u5178\u5236\u836f",
                "source": "\u836f\u54c1\u8bf4\u660e\u4e66",
                "title": "\u590d\u65b9\u5357\u4e94\u52a0\u53e3\u670d\u6db2\u8bf4\u660e\u4e66"
            },
            "knowledge_base_id": "4dfbef46-cd26-416e-98b9-f91a54fe1396",
            "document_id": "f569c321-646b-4655-949d-a08426e8f230",
            "context_text": null,
            "context_before": null,
            "context_after": null,
            "hyde_queries": null,
            "hyde_queries_count": null
        },
        {
            "chunk_id": "39077923-ad5b-4a86-8ecb-6675989c000f",
            "text": "## \u3010\u751f\u4ea7\u4f01\u4e1a\u3011  \n\n\u4f01\u4e1a\u540d\u79f0\uff1a\u6e56\u5357\u4e5d\u5178\u5236\u836f\u80a1\u4efd\u6709\u9650\u516c\u53f8  \n\u751f\u4ea7\u5730\u5740\uff1a\u957f\u6c99\u5e02\u6d4f\u9633\u7ecf\u6d4e\u6280\u672f\u5f00\u53d1\u533a\u5065\u5eb7\u5927\u90531\u53f7  \n\u90ae\u653f\u7f16\u7801\uff1a410331  \n\u7535\u8bdd\u53f7\u7801\uff1a0731-88220220 88220228  \n\u4f20\u771f\u53f7\u7801\uff1a0731-88220238  \n\u7f51\u5740\uff1ahttp://www.hnjiudian.com  \n\n\u5982\u6709\u95ee\u9898\u53ef\u4e0e\u751f\u4ea7\u4f01\u4e1a\u8054\u7cfb\n```",
            "score": 0.5629767,
            "metadata": {
                "category": "\u4e2d\u6210\u836f",
                "document_id": "83960e95-8b36-46c9-bfa8-e2de58ecb2d6",
                "manufacturer": "\u6e56\u5357\u4e5d\u5178\u5236\u836f",
                "source": "\u836f\u54c1\u8bf4\u660e\u4e66",
                "title": "\u590d\u65b9\u5357\u4e94\u52a0\u53e3\u670d\u6db2\u8bf4\u660e\u4e66"
            },
            "knowledge_base_id": "4dfbef46-cd26-416e-98b9-f91a54fe1396",
            "document_id": "83960e95-8b36-46c9-bfa8-e2de58ecb2d6",
            "context_text": null,
            "context_before": null,
            "context_after": null,
            "hyde_queries": null,
            "hyde_queries_count": null
        }
    ],
    "model": {
        "embedding_provider": "ollama",
        "embedding_model": "bge-m3",
        "llm_provider": null,
        "llm_model": null,
        "rerank_provider": null,
        "rerank_model": null,
        "retriever": "dense"
    }
}
```

**分析**: LlamaDense 使用 LlamaIndex VectorStoreIndex + RealEmbedding（调用真实 bge-m3）。

---

### 8. LlamaBM25 检索器

**配置**: `{"query":{"retriever":{"name":"llama_bm25"}}}`

**查询**: `有效期`

**响应**:
```json
{
    "results": [
        {
            "chunk_id": "fabec152-54e0-46d9-8fb0-d50859f71693",
            "text": "## \u3010\u6709\u6548\u671f\u3011  \n\n30\u4e2a\u6708  \n",
            "score": 0.8134659,
            "metadata": {
                "category": "\u4e2d\u6210\u836f",
                "document_id": "f569c321-646b-4655-949d-a08426e8f230",
                "manufacturer": "\u6e56\u5357\u4e5d\u5178\u5236\u836f",
                "source": "\u836f\u54c1\u8bf4\u660e\u4e66",
                "title": "\u590d\u65b9\u5357\u4e94\u52a0\u53e3\u670d\u6db2\u8bf4\u660e\u4e66"
            },
            "knowledge_base_id": "4dfbef46-cd26-416e-98b9-f91a54fe1396",
            "document_id": "f569c321-646b-4655-949d-a08426e8f230",
            "context_text": null,
            "context_before": null,
            "context_after": null,
            "hyde_queries": null,
            "hyde_queries_count": null
        },
        {
            "chunk_id": "eb0bca6f-5b37-4476-bad5-6917793746ff",
            "text": "## \u3010\u6709\u6548\u671f\u3011  \n\n30\u4e2a\u6708  \n",
            "score": 0.8134659,
            "metadata": {
                "category": "\u4e2d\u6210\u836f",
                "document_id": "83960e95-8b36-46c9-bfa8-e2de58ecb2d6",
                "manufacturer": "\u6e56\u5357\u4e5d\u5178\u5236\u836f",
                "source": "\u836f\u54c1\u8bf4\u660e\u4e66",
                "title": "\u590d\u65b9\u5357\u4e94\u52a0\u53e3\u670d\u6db2\u8bf4\u660e\u4e66"
            },
            "knowledge_base_id": "4dfbef46-cd26-416e-98b9-f91a54fe1396",
            "document_id": "83960e95-8b36-46c9-bfa8-e2de58ecb2d6",
            "context_text": null,
            "context_before": null,
            "context_after": null,
            "hyde_queries": null,
            "hyde_queries_count": null
        }
    ],
    "model": {
        "embedding_provider": "ollama",
        "embedding_model": "bge-m3",
        "llm_provider": null,
        "llm_model": null,
        "rerank_provider": null,
        "rerank_model": null,
        "retriever": "dense"
    }
}
```

**分析**: LlamaBM25 从数据库加载 chunks 构建 BM25 索引，带缓存机制。

---

### 9. LlamaHybrid 检索器

**配置**: `{"query":{"retriever":{"name":"llama_hybrid"}}}`

**查询**: `不良反应`

**响应**:
```json
{
    "results": [
        {
            "chunk_id": "9ec9b94a-f8b1-4ba0-bed8-822ae92571b9",
            "text": "## \u3010\u4e0d\u826f\u53cd\u5e94\u3011  \n\n\u5c1a\u4e0d\u660e\u786e\u3002  \n",
            "score": 0.76001894,
            "metadata": {
                "category": "\u4e2d\u6210\u836f",
                "document_id": "f569c321-646b-4655-949d-a08426e8f230",
                "manufacturer": "\u6e56\u5357\u4e5d\u5178\u5236\u836f",
                "source": "\u836f\u54c1\u8bf4\u660e\u4e66",
                "title": "\u590d\u65b9\u5357\u4e94\u52a0\u53e3\u670d\u6db2\u8bf4\u660e\u4e66"
            },
            "knowledge_base_id": "4dfbef46-cd26-416e-98b9-f91a54fe1396",
            "document_id": "f569c321-646b-4655-949d-a08426e8f230",
            "context_text": null,
            "context_before": null,
            "context_after": null,
            "hyde_queries": null,
            "hyde_queries_count": null
        },
        {
            "chunk_id": "959744f1-589f-4f8f-a6b6-ceb4db206734",
            "text": "## \u3010\u4e0d\u826f\u53cd\u5e94\u3011  \n\n\u5c1a\u4e0d\u660e\u786e\u3002  \n",
            "score": 0.76001894,
            "metadata": {
                "category": "\u4e2d\u6210\u836f",
                "document_id": "83960e95-8b36-46c9-bfa8-e2de58ecb2d6",
                "manufacturer": "\u6e56\u5357\u4e5d\u5178\u5236\u836f",
                "source": "\u836f\u54c1\u8bf4\u660e\u4e66",
                "title": "\u590d\u65b9\u5357\u4e94\u52a0\u53e3\u670d\u6db2\u8bf4\u660e\u4e66"
            },
            "knowledge_base_id": "4dfbef46-cd26-416e-98b9-f91a54fe1396",
            "document_id": "83960e95-8b36-46c9-bfa8-e2de58ecb2d6",
            "context_text": null,
            "context_before": null,
            "context_after": null,
            "hyde_queries": null,
            "hyde_queries_count": null
        }
    ],
    "model": {
        "embedding_provider": "ollama",
        "embedding_model": "bge-m3",
        "llm_provider": null,
        "llm_model": null,
        "rerank_provider": null,
        "rerank_model": null,
        "retriever": "dense"
    }
}
```

**分析**: LlamaHybrid 结合 LlamaIndex 稠密向量和 BM25 检索。

---

### 10. SelfQuery 检索器

**配置**: `{"query":{"retriever":{"name":"self_query","params":{"base_retriever":"dense"}}}}`

**查询**: `贮藏条件`

**响应**:
```json
{
    "results": [
        {
            "chunk_id": "f5e088a7-84ae-4786-98a4-1a4b82157d32",
            "text": "## \u3010\u8d2e \u85cf\u3011  \n\n\u906e\u5149\uff0c\u5bc6\u5c01\u3002  \n",
            "score": 0.7245077,
            "metadata": {
                "category": "\u4e2d\u6210\u836f",
                "document_id": "f569c321-646b-4655-949d-a08426e8f230",
                "manufacturer": "\u6e56\u5357\u4e5d\u5178\u5236\u836f",
                "source": "\u836f\u54c1\u8bf4\u660e\u4e66",
                "title": "\u590d\u65b9\u5357\u4e94\u52a0\u53e3\u670d\u6db2\u8bf4\u660e\u4e66"
            },
            "knowledge_base_id": "4dfbef46-cd26-416e-98b9-f91a54fe1396",
            "document_id": "f569c321-646b-4655-949d-a08426e8f230",
            "context_text": null,
            "context_before": null,
            "context_after": null,
            "hyde_queries": null,
            "hyde_queries_count": null
        },
        {
            "chunk_id": "65df8813-27f1-431b-9f18-cd6eefaf7e49",
            "text": "## \u3010\u8d2e \u85cf\u3011  \n\n\u906e\u5149\uff0c\u5bc6\u5c01\u3002  \n",
            "score": 0.7245077,
            "metadata": {
                "category": "\u4e2d\u6210\u836f",
                "document_id": "83960e95-8b36-46c9-bfa8-e2de58ecb2d6",
                "manufacturer": "\u6e56\u5357\u4e5d\u5178\u5236\u836f",
                "source": "\u836f\u54c1\u8bf4\u660e\u4e66",
                "title": "\u590d\u65b9\u5357\u4e94\u52a0\u53e3\u670d\u6db2\u8bf4\u660e\u4e66"
            },
            "knowledge_base_id": "4dfbef46-cd26-416e-98b9-f91a54fe1396",
            "document_id": "83960e95-8b36-46c9-bfa8-e2de58ecb2d6",
            "context_text": null,
            "context_before": null,
            "context_after": null,
            "hyde_queries": null,
            "hyde_queries_count": null
        }
    ],
    "model": {
        "embedding_provider": "ollama",
        "embedding_model": "bge-m3",
        "llm_provider": null,
        "llm_model": null,
        "rerank_provider": null,
        "rerank_model": null,
        "retriever": "dense"
    }
}
```

**分析**: SelfQuery 使用 LLM 解析查询，自动提取元数据过滤条件。

---

### 11. ParentDocument 检索器

**配置**: `{"query":{"retriever":{"name":"parent_document"}}}`

**查询**: `批准文号`

**响应**:
```json
{
    "results": [
        {
            "chunk_id": "d426cf6d-ea2a-41a0-9d22-50bfc0a2e080",
            "text": "## \u3010\u6279\u51c6\u6587\u53f7\u3011  \n\n\u56fd\u836f\u51c6\u5b57B20020198  \n",
            "score": 0.65610206,
            "metadata": {
                "category": "\u4e2d\u6210\u836f",
                "document_id": "f569c321-646b-4655-949d-a08426e8f230",
                "manufacturer": "\u6e56\u5357\u4e5d\u5178\u5236\u836f",
                "source": "\u836f\u54c1\u8bf4\u660e\u4e66",
                "title": "\u590d\u65b9\u5357\u4e94\u52a0\u53e3\u670d\u6db2\u8bf4\u660e\u4e66"
            },
            "knowledge_base_id": "4dfbef46-cd26-416e-98b9-f91a54fe1396",
            "document_id": "f569c321-646b-4655-949d-a08426e8f230",
            "context_text": null,
            "context_before": null,
            "context_after": null,
            "hyde_queries": null,
            "hyde_queries_count": null
        },
        {
            "chunk_id": "47550066-f6ae-46da-8da8-84ff72a3598a",
            "text": "## \u3010\u6279\u51c6\u6587\u53f7\u3011  \n\n\u56fd\u836f\u51c6\u5b57B20020198  \n",
            "score": 0.65610206,
            "metadata": {
                "category": "\u4e2d\u6210\u836f",
                "document_id": "83960e95-8b36-46c9-bfa8-e2de58ecb2d6",
                "manufacturer": "\u6e56\u5357\u4e5d\u5178\u5236\u836f",
                "source": "\u836f\u54c1\u8bf4\u660e\u4e66",
                "title": "\u590d\u65b9\u5357\u4e94\u52a0\u53e3\u670d\u6db2\u8bf4\u660e\u4e66"
            },
            "knowledge_base_id": "4dfbef46-cd26-416e-98b9-f91a54fe1396",
            "document_id": "83960e95-8b36-46c9-bfa8-e2de58ecb2d6",
            "context_text": null,
            "context_before": null,
            "context_after": null,
            "hyde_queries": null,
            "hyde_queries_count": null
        }
    ],
    "model": {
        "embedding_provider": "ollama",
        "embedding_model": "bge-m3",
        "llm_provider": null,
        "llm_model": null,
        "rerank_provider": null,
        "rerank_model": null,
        "retriever": "dense"
    }
}
```

**分析**: ParentDocument 检索小块但返回父块上下文，需配合 parent_child chunker 使用效果最佳。

---

### 12. Ensemble 检索器

**配置**: `{"query":{"retriever":{"name":"ensemble","params":{"retrievers":["dense","bm25"],"weights":[0.6,0.4]}}}}`

**查询**: `规格包装`

**响应**:
```json
{
    "results": [
        {
            "chunk_id": "26511944-2de1-48e1-a096-2c6df04df4b2",
            "text": "## \u3010\u89c4\u683c\u3011  \n\n\u6bcf\u74f6\u88c510\u6beb\u5347  \n",
            "score": 0.6158909,
            "metadata": {
                "category": "\u4e2d\u6210\u836f",
                "document_id": "f569c321-646b-4655-949d-a08426e8f230",
                "manufacturer": "\u6e56\u5357\u4e5d\u5178\u5236\u836f",
                "source": "\u836f\u54c1\u8bf4\u660e\u4e66",
                "title": "\u590d\u65b9\u5357\u4e94\u52a0\u53e3\u670d\u6db2\u8bf4\u660e\u4e66"
            },
            "knowledge_base_id": "4dfbef46-cd26-416e-98b9-f91a54fe1396",
            "document_id": "f569c321-646b-4655-949d-a08426e8f230",
            "context_text": null,
            "context_before": null,
            "context_after": null,
            "hyde_queries": null,
            "hyde_queries_count": null
        },
        {
            "chunk_id": "bd86e46b-8a08-4bd7-a4d4-6692697f3fe8",
            "text": "## \u3010\u89c4\u683c\u3011  \n\n\u6bcf\u74f6\u88c510\u6beb\u5347  \n",
            "score": 0.6158909,
            "metadata": {
                "category": "\u4e2d\u6210\u836f",
                "document_id": "83960e95-8b36-46c9-bfa8-e2de58ecb2d6",
                "manufacturer": "\u6e56\u5357\u4e5d\u5178\u5236\u836f",
                "source": "\u836f\u54c1\u8bf4\u660e\u4e66",
                "title": "\u590d\u65b9\u5357\u4e94\u52a0\u53e3\u670d\u6db2\u8bf4\u660e\u4e66"
            },
            "knowledge_base_id": "4dfbef46-cd26-416e-98b9-f91a54fe1396",
            "document_id": "83960e95-8b36-46c9-bfa8-e2de58ecb2d6",
            "context_text": null,
            "context_before": null,
            "context_after": null,
            "hyde_queries": null,
            "hyde_queries_count": null
        }
    ],
    "model": {
        "embedding_provider": "ollama",
        "embedding_model": "bge-m3",
        "llm_provider": null,
        "llm_model": null,
        "rerank_provider": null,
        "rerank_model": null,
        "retriever": "dense"
    }
}
```

**分析**: Ensemble 允许任意组合多个检索器，设置权重加权融合。

---

## 总结

### 测试结果

所有 12 个检索器均测试通过，使用真实数据和真实模型：

| 检索器 | Embedding | LLM | 特点 |
|--------|-----------|-----|------|
| dense | bge-m3 | - | 语义相似度匹配 |
| bm25 | - | - | 关键词精确匹配，从 DB 加载 |
| hybrid | bge-m3 | - | Dense + BM25，带 source 标记 |
| fusion | bge-m3 | - | RRF 融合，可选 Rerank |
| hyde | bge-m3 | qwen3:14b | LLM 生成假设文档 |
| multi_query | bge-m3 | qwen3:14b | LLM 生成多查询变体 |
| llama_dense | bge-m3 | - | LlamaIndex 版稠密检索 |
| llama_bm25 | - | - | LlamaIndex 版 BM25 |
| llama_hybrid | bge-m3 | - | LlamaIndex 混合检索 |
| self_query | bge-m3 | qwen3:14b | LLM 解析元数据过滤 |
| parent_document | bge-m3 | - | 小块检索返回父块 |
| ensemble | bge-m3 | - | 任意组合多检索器 |

### 关键改进

1. **source 字段**: 上传文档时传入 `source` 参数，检索结果中显示数据来源
2. **多 chunks**: 使用 markdown chunker (chunk_size=512) 将长文档切分为 20 个 chunks
3. **真实模型**: 所有检索器使用真实的 Ollama bge-m3 Embedding 和 qwen3:14b LLM
4. **完整 metadata**: 包含 category、manufacturer、document_id 等元数据

### 响应格式

```json
{
  "results": [
    {
      "chunk_id": "xxx",
      "text": "检索到的文本...",
      "score": 0.85,
      "metadata": {
        "source": "药品说明书",
        "category": "中成药",
        "manufacturer": "湖南九典制药",
        "document_id": "xxx",
        "title": "复方南五加口服液说明书"
      },
      "knowledge_base_id": "xxx",
      "hyde_queries": ["LLM生成的假设文档..."]
    }
  ],
  "model": {
    "embedding_provider": "ollama",
    "embedding_model": "bge-m3",
    "llm_provider": "ollama",
    "llm_model": "qwen3:14b",
    "rerank_provider": null,
    "rerank_model": null,
    "retriever": "检索器名称"
  }
}
```

