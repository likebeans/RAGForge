# Phase 2 进度与记录

## 1. LlamaIndex 接入
- 引入依赖：`llama-index-core`、`llama-index-vector-stores-qdrant`、`llama-index-retrievers-bm25`、`llama-index-llms-openai`（当前使用 HashEmbedding 占位）。
- Chunker 算子：`llama_sentence`(SentenceSplitter)、`llama_token`(TokenTextSplitter)，注册至 operator_registry。
- Retriever 算子：`llama_dense`(Qdrant VectorStoreIndex)、`llama_bm25`(基于 DB chunks 构造 BM25)、`llama_hybrid`(dense+bm25 加权)。
- 适配层：`app/infra/llamaindex.py` 支持按 store 类型构建 VectorStoreIndex（qdrant/milvus/es），提供 HashEmbedding 和 chunk→TextNode 转换。

## 2. 多后端存储/检索
- 默认：Qdrant（向量）+ 内存 BM25。
- 可配置 store 类型：`ingestion.store.type` 支持 `qdrant|milvus|es`，参数 `params` 支持连接/collection/index 配置。若 milvus/es 配置缺失则跳过写入并打印错误。
- 检索：按 KB `config.query.retriever` 选择算子；Hybrid 支持加权融合 dense/bm25；冲突配置可用 `allow_mixed` 允许混合。

## 3. 配置校验
- `config_validation` 校验 chunker/retriever/store 是否注册，未知即 400。
- KB PATCH/POST 在保存前校验；响应包含 `config`。

## 4. Ingestion/Query 行为
- Ingestion：chunk → Qdrant + BM25，若配置指定 milvus/es 也尝试写入对应存储（通过 LlamaIndex）。
- Query：按 KB 配置选择 retriever，默认 dense；LlamaIndex BM25 会从数据库拉取 chunk 构建节点。

## 5. 已验测试
- e2e（API_KEY=root，API_BASE=8020）通过，覆盖创建 KB → 文档入库 → 检索。

## 6. 配置样例
- LlamaIndex 分块+检索（Qdrant）
```json
{
  "config": {
    "ingestion": {
      "chunker": {"name": "llama_sentence", "params": {"max_tokens": 512, "chunk_overlap": 50}}
    },
    "query": {
      "retriever": {"name": "llama_dense", "params": {"top_k": 5}}
    }
  }
}
```
- Milvus IVF_PQ 示例
```json
{
  "config": {
    "ingestion": {
      "chunker": {"name": "llama_sentence", "params": {"max_tokens": 512, "chunk_overlap": 50}},
      "store": {
        "type": "milvus",
        "params": {
          "host": "milvus-host",
          "port": 19530,
          "index_params": {"index_type": "IVF_PQ", "metric_type": "COSINE", "params": {"nlist": 128, "m": 16}},
          "search_params": {"metric_type": "COSINE", "params": {"nprobe": 16}},
          "skip_qdrant": true
        }
      }
    },
    "query": {
      "retriever": {"name": "llama_dense", "params": {"store_type": "milvus", "top_k": 5}}
    }
  }
}
```
- Elasticsearch dense_vector 示例
```json
{
  "config": {
    "ingestion": {
      "store": {
        "type": "es",
        "params": {
          "hosts": "http://es:9200",
          "index": "kb_es_example",
          "body": {
            "settings": {"index": {"refresh_interval": "1s"}},
            "mappings": {
              "properties": {
                "text": {"type": "text"},
                "metadata": {"type": "object"},
                "vector": {"type": "dense_vector", "dims": 256, "index": true, "similarity": "cosine"}
              }
            }
          },
          "skip_qdrant": true
        }
      }
    },
    "query": {
      "retriever": {"name": "llama_dense", "params": {"store_type": "es", "top_k": 5}}
    }
  }
}
```

## 7. 待办
- 落地 Milvus/ES 生产化（连接、索引参数、PQ/IVF/HNSW 配置）。
- 更细粒度配置校验（参数范围、必填项）。
- 依赖精简：LlamaIndex 拉取 pillow/nltk，可在镜像优化。
