# RAG 优化算法参数完整手册

本文档详细总结后端所有 RAG 优化算法的参数配置，供前端开发参考，以实现对优化算法的完全控制。

## 目录

1. [切分器 (Chunkers)](#1-切分器-chunkers)
2. [检索器 (Retrievers)](#2-检索器-retrievers)
3. [查询变换 (Query Transforms)](#3-查询变换-query-transforms)
4. [与 RAGFlow/Dify 对比分析](#4-与-ragflowdify-对比分析)
5. [前端参数配置 JSON Schema](#5-前端参数配置-json-schema)
6. [待优化项](#6-待优化项)

---

## 1. 切分器 (Chunkers)

切分器负责将长文本切分为适合向量化和检索的片段。

### 1.1 simple - 简单段落切分

**说明**：按双换行符（`\n\n`）切分段落，超长段落按固定长度截断。

| 参数 | 类型 | 默认值 | 说明 |
|------|------|--------|------|
| `max_chars` | int | 800 | 单个片段最大字符数 |

**输出元数据**：无特殊元数据

---

### 1.2 sliding_window - 滑动窗口切分

**说明**：固定窗口大小滑动切分，保持片段间重叠。

| 参数 | 类型 | 默认值 | 说明 |
|------|------|--------|------|
| `window` | int | 800 | 窗口大小（字符数） |
| `overlap` | int | 200 | 相邻片段重叠字符数 |

**输出元数据**：
- `offset`: 片段在原文中的起始位置

---

### 1.3 parent_child - 父子分块

**说明**：生成大片段（父块）和小片段（子块），支持多粒度检索。子块检索后可回溯父块获取更完整上下文。

| 参数 | 类型 | 默认值 | 说明 |
|------|------|--------|------|
| `parent_chars` | int | 1600 | 父块大小（字符数） |
| `child_chars` | int | 400 | 子块大小（字符数） |
| `overlap` | int | 100 | 子块间重叠字符数 |

**输出元数据**：
- `parent_id`: 父块标识符（UUID），用于关联父子块
- `child`: 布尔值，标识是否为子块（`true`=子块，`false`/无=父块）
- `child_index`: 子块在父块中的索引位置

**配套检索器**：需配合 `parent_document` 检索器使用

---

### 1.4 recursive - 递归字符切分

**说明**：按优先级尝试多种分隔符，优先保持语义边界完整。**推荐通用文档使用**。

| 参数 | 类型 | 默认值 | 说明 |
|------|------|--------|------|
| `chunk_size` | int | 1024 | 目标块大小（字符数） |
| `chunk_overlap` | int | 256 | 重叠大小（字符数） |
| `separators` | list[str] | `["\n\n", "\n", "。", ".", " "]` | 分隔符优先级列表 |
| `keep_separator` | bool | True | 是否保留分隔符 |

**输出元数据**：无特殊元数据

---

### 1.5 markdown - Markdown 感知切分

**说明**：按 Markdown 标题层级切分，保留标题路径元数据。

| 参数 | 类型 | 默认值 | 说明 |
|------|------|--------|------|
| `headers_to_split_on` | list[tuple] | `[("#", "h1"), ("##", "h2"), ("###", "h3")]` | 切分的标题级别 |
| `chunk_size` | int | 1024 | 块大小（字符数） |
| `chunk_overlap` | int | 256 | 重叠大小（字符数） |
| `strip_headers` | bool | False | 是否移除标题 |

**输出元数据**：
- `h1`, `h2`, `h3`...: 各级标题内容
- `heading_path`: 标题路径（如 "第一章 > 1.1 简介"）

---

### 1.6 markdown_section - Markdown 分节切分

**说明**：基于 LlamaIndex 的 Markdown 分节切分，按标题/段落分块。

| 参数 | 类型 | 默认值 | 说明 |
|------|------|--------|------|
| `chunk_size` | int | 1200 | 块大小（字符数） |
| `chunk_overlap` | int | 200 | 重叠大小（字符数） |

**输出元数据**：
- `heading`: 所属标题

---

### 1.7 code - 代码感知切分

**说明**：按代码语法结构切分，保持函数/类完整性。

| 参数 | 类型 | 默认值 | 说明 |
|------|------|--------|------|
| `language` | str | "auto" | 代码语言：`auto`/`python`/`javascript`/`typescript`/`java`/`go`/`rust` |
| `max_chunk_size` | int | 2000 | 最大块大小（字符数） |
| `include_imports` | bool | True | 每块是否包含导入语句 |
| `filename` | str | None | 文件名（用于自动检测语言） |

**输出元数据**：
- `language`: 检测到的语言
- `function_name`: 函数名（如适用）
- `class_name`: 类名（如适用）
- `imports`: 导入语句列表

---

### 1.8 llama_sentence - LlamaIndex 句子切分

**说明**：基于 LlamaIndex SentenceSplitter，保持句子完整性。

| 参数 | 类型 | 默认值 | 说明 |
|------|------|--------|------|
| `max_tokens` | int | 512 | 每片段最大 Token 数 |
| `chunk_overlap` | int | 50 | 重叠 Token 数 |

**输出元数据**：继承 LlamaIndex 节点元数据

---

### 1.9 llama_token - LlamaIndex Token 切分

**说明**：严格按 Token 数量切分，适配 LLM 上下文限制。

| 参数 | 类型 | 默认值 | 说明 |
|------|------|--------|------|
| `max_tokens` | int | 512 | 每片段最大 Token 数 |
| `chunk_overlap` | int | 50 | 重叠 Token 数 |

**输出元数据**：无特殊元数据

---

## 2. 检索器 (Retrievers)

检索器从向量库和 BM25 索引中召回相关片段。

### 2.1 dense - 稠密向量检索

**说明**：基于 Qdrant 的语义向量检索。

| 参数 | 类型 | 默认值 | 说明 |
|------|------|--------|------|
| 无构造参数 | - | - | 使用全局 Embedding 配置 |

**运行时参数**：`top_k`

---

### 2.2 bm25 - BM25 稀疏检索

**说明**：基于内存 BM25 的关键词检索。

| 参数 | 类型 | 默认值 | 说明 |
|------|------|--------|------|
| 无构造参数 | - | - | 从 DB 加载词库 |

**运行时参数**：`top_k`

---

### 2.3 hybrid - 混合检索

**说明**：Dense + BM25 加权融合，兼顾语义和关键词。

| 参数 | 类型 | 默认值 | 说明 |
|------|------|--------|------|
| `dense_weight` | float | 0.7 | 稠密检索权重 |
| `sparse_weight` | float | 0.3 | 稀疏检索权重 |

**权重调优建议**：
| 场景 | dense_weight | sparse_weight |
|------|--------------|---------------|
| 通用问答 | 0.7 | 0.3 |
| 平衡场景 | 0.5 | 0.5 |
| 术语/实体检索 | 0.3 | 0.7 |
| 纯语义匹配 | 0.9 | 0.1 |

---

### 2.4 fusion - 融合检索（RRF + Rerank）

**说明**：支持 RRF 或加权融合，可选 Rerank 精排。

| 参数 | 类型 | 默认值 | 说明 |
|------|------|--------|------|
| `mode` | str | "rrf" | 融合模式：`rrf` / `weighted` |
| `dense_weight` | float | 0.7 | 稠密检索权重（weighted 模式） |
| `bm25_weight` | float | 0.3 | BM25 权重（weighted 模式） |
| `rrf_k` | int | 60 | RRF 常数（论文推荐值） |
| `rerank` | bool | False | 是否启用 Rerank |
| `rerank_model` | str | "BAAI/bge-reranker-base" | Rerank 模型 |
| `rerank_top_n` | int | 10 | Rerank 后返回数量 |
| `top_k` | int | 20 | 默认召回数量 |

---

### 2.5 hyde - HyDE 检索器

**说明**：使用 LLM 生成假设答案进行检索，解决"问题 vs 答案"语义鸿沟。

| 参数 | 类型 | 默认值 | 说明 |
|------|------|--------|------|
| `base_retriever` | str | "dense" | 底层检索器名称 |
| `base_retriever_params` | dict | {} | 底层检索器参数 |
| `hyde_config` | HyDEConfig | None | HyDE 配置对象 |
| `rrf_k` | int | 60 | RRF 融合常数 |

**HyDEConfig 参数**：
| 参数 | 类型 | 默认值 | 说明 |
|------|------|--------|------|
| `enabled` | bool | True | 是否启用 |
| `num_queries` | int | 4 | 生成假设答案数量 |
| `include_original` | bool | True | 是否保留原始查询 |
| `max_tokens` | int | 2000 | 假设答案最大 token |
| `model` | str | None | 使用的 LLM 模型 |

**输出扩展字段**：
- `hyde_queries`: LLM 生成的假设文档列表
- `hyde_queries_count`: 假设文档数量

---

### 2.6 multi_query - 多查询检索

**说明**：LLM 生成查询变体，多路召回后 RRF 融合。

| 参数 | 类型 | 默认值 | 说明 |
|------|------|--------|------|
| `base_retriever` | str | "dense" | 底层检索器名称 |
| `base_retriever_params` | dict | {} | 底层检索器参数 |
| `num_queries` | int | 3 | 生成查询变体数量 |
| `include_original` | bool | True | 是否保留原始查询 |
| `rrf_k` | int | 60 | RRF 融合常数 |

**输出扩展字段**：
- `generated_queries`: LLM 生成的查询变体列表
- `queries_count`: 查询变体数量
- `retrieval_details`: 每个查询的完整检索结果

---

### 2.7 parent_document - 父文档检索

**说明**：检索子块，返回对应父块，保留完整上下文。需配合 `parent_child` 切分器。

| 参数 | 类型 | 默认值 | 说明 |
|------|------|--------|------|
| `base_retriever` | str | "dense" | 底层检索器名称 |
| `base_retriever_params` | dict | {} | 底层检索器参数 |
| `return_parent` | bool | True | 是否返回父块 |
| `include_child` | bool | False | 是否包含匹配子块信息 |

**输出扩展字段**：
- `parent_id`: 父块标识
- `matched_children`: 匹配的子块列表（如 include_child=True）

---

### 2.8 llama_dense - LlamaIndex 稠密检索

**说明**：支持多向量存储后端（Qdrant/Milvus/ES）。

| 参数 | 类型 | 默认值 | 说明 |
|------|------|--------|------|
| `top_k` | int | 5 | 默认返回数量 |
| `store_type` | str | "qdrant" | 向量存储类型：`qdrant`/`milvus`/`es` |
| `store_params` | dict | {} | 存储参数 |

---

### 2.9 llama_bm25 - LlamaIndex BM25 检索

**说明**：带 TTL 缓存的 BM25 检索。

| 参数 | 类型 | 默认值 | 说明 |
|------|------|--------|------|
| `top_k` | int | 5 | 默认返回数量 |
| `max_chunks` | int | 5000 | 最大加载片段数 |
| `cache_ttl` | int | 60 | 缓存过期时间（秒） |

---

### 2.10 llama_hybrid - LlamaIndex 混合检索

| 参数 | 类型 | 默认值 | 说明 |
|------|------|--------|------|
| `dense_weight` | float | 0.7 | 稠密检索权重 |
| `bm25_weight` | float | 0.3 | BM25 检索权重 |
| `top_k` | int | 5 | 默认返回数量 |

---

## 3. 查询变换 (Query Transforms)

### 3.1 HyDEQueryTransform - 假设文档嵌入

**说明**：将用户问题转换为假设性答案。

| 参数 | 类型 | 默认值 | 说明 |
|------|------|--------|------|
| `num_queries` | int | 4 | 生成假设答案数量 |
| `include_original` | bool | True | 是否保留原始查询 |
| `max_tokens` | int | 256 | 假设答案最大 token |
| `model` | str | None | LLM 模型 |
| `prompt_template` | str | 默认模板 | 提示词模板 |

---

### 3.2 RAGFusionTransform - 多查询扩展

**说明**：生成多个查询变体，提高召回覆盖率。

| 参数 | 类型 | 默认值 | 说明 |
|------|------|--------|------|
| `num_queries` | int | 3 | 生成查询变体数量 |
| `include_original` | bool | True | 是否保留原始查询 |
| `max_tokens` | int | 500 | 每个变体最大 token |
| `model` | str | None | LLM 模型 |

---

## 4. 与 RAGFlow/Dify 对比分析

### 4.1 RAGFlow 特性

| 特性 | RAGFlow | 本项目 | 差距分析 |
|------|---------|--------|----------|
| **分块模式** | 通用/Q&A/书籍/论文/法律/演示文稿 | 通用切分器 | 🔴 缺少专业模板 |
| **视觉解析** | OCR、表格识别、图像描述 | 仅文本 | 🔴 不支持 |
| **智能分块** | 自动识别文档结构 | 手动选择 | 🟡 需手动配置 |
| **分块预览** | 实时预览 | ✅ 已实现 | ✅ |
| **知识图谱** | 支持 | 不支持 | 🔴 缺失 |

### 4.2 Dify 特性

| 特性 | Dify | 本项目 | 差距分析 |
|------|------|--------|----------|
| **父子模式** | Parent-Child Mode | ✅ parent_child 切分器 | ✅ |
| **全文模式** | Full-Text Mode | ✅ 支持 | ✅ |
| **分块大小** | 可配置 | ✅ 支持 | ✅ |
| **重叠设置** | 可配置 | ✅ 支持 | ✅ |
| **清洗规则** | 多种预设 | 🟡 简单清洗 | 🟡 |
| **索引策略** | 高质量/经济 | 单一策略 | 🟡 |
| **检索模式** | 语义/全文/混合 | ✅ 支持 | ✅ |
| **Rerank** | 支持 | ✅ fusion 检索器 | ✅ |
| **分数阈值** | 可配置 | 🟡 需添加 | 🟡 |
| **Top-K** | 可配置 | ✅ 支持 | ✅ |

### 4.3 建议增强

1. **添加分数阈值过滤**：检索结果按相似度分数过滤
2. **添加专业文档模板**：Q&A、法律、技术文档等预设
3. **增强文本清洗**：去除特殊字符、URL、邮箱等
4. **支持元数据过滤**：按文档属性过滤检索范围

---

## 5. 前端参数配置 JSON Schema

### 5.1 切分器参数配置

```typescript
// 切分器参数配置类型
interface ChunkerParams {
  simple: {
    max_chars: number;  // 默认 800
  };
  sliding_window: {
    window: number;     // 默认 800
    overlap: number;    // 默认 200
  };
  parent_child: {
    parent_chars: number;  // 默认 1600
    child_chars: number;   // 默认 400
    overlap: number;       // 默认 100
  };
  recursive: {
    chunk_size: number;        // 默认 1024
    chunk_overlap: number;     // 默认 256
    separators?: string[];     // 可选，默认 ["\n\n", "\n", "。", ".", " "]
    keep_separator?: boolean;  // 可选，默认 true
  };
  markdown: {
    chunk_size: number;           // 默认 1024
    chunk_overlap: number;        // 默认 256
    strip_headers?: boolean;      // 可选，默认 false
  };
  markdown_section: {
    chunk_size: number;     // 默认 1200
    chunk_overlap: number;  // 默认 200
  };
  code: {
    language: 'auto' | 'python' | 'javascript' | 'typescript' | 'java' | 'go' | 'rust';
    max_chunk_size: number;    // 默认 2000
    include_imports?: boolean; // 可选，默认 true
  };
  llama_sentence: {
    max_tokens: number;     // 默认 512
    chunk_overlap: number;  // 默认 50
  };
  llama_token: {
    max_tokens: number;     // 默认 512
    chunk_overlap: number;  // 默认 50
  };
}

// 前端显示配置
const CHUNKER_UI_CONFIG = {
  simple: {
    label: '简单分段',
    description: '按段落切分，适合简单文本',
    params: [
      { key: 'max_chars', label: '最大字符数', type: 'number', default: 800, min: 100, max: 5000 }
    ]
  },
  sliding_window: {
    label: '滑动窗口',
    description: '固定窗口滑动切分，保持片段重叠',
    params: [
      { key: 'window', label: '窗口大小', type: 'number', default: 800, min: 100, max: 5000 },
      { key: 'overlap', label: '重叠大小', type: 'number', default: 200, min: 0, max: 1000 }
    ]
  },
  parent_child: {
    label: '父子分块',
    description: '生成父块和子块，支持多粒度检索',
    params: [
      { key: 'parent_chars', label: '父块大小', type: 'number', default: 1600, min: 500, max: 10000 },
      { key: 'child_chars', label: '子块大小', type: 'number', default: 400, min: 100, max: 2000 },
      { key: 'overlap', label: '子块重叠', type: 'number', default: 100, min: 0, max: 500 }
    ]
  },
  recursive: {
    label: '递归字符分块',
    description: '优先保持语义边界，推荐通用文档',
    params: [
      { key: 'chunk_size', label: '块大小', type: 'number', default: 1024, min: 100, max: 5000 },
      { key: 'chunk_overlap', label: '重叠大小', type: 'number', default: 256, min: 0, max: 1000 }
    ]
  },
  markdown: {
    label: 'Markdown 分块',
    description: '按标题层级切分，适合技术文档',
    params: [
      { key: 'chunk_size', label: '块大小', type: 'number', default: 1024, min: 100, max: 5000 },
      { key: 'chunk_overlap', label: '重叠大小', type: 'number', default: 256, min: 0, max: 1000 },
      { key: 'strip_headers', label: '移除标题', type: 'boolean', default: false }
    ]
  },
  markdown_section: {
    label: 'Markdown 分节',
    description: '基于 LlamaIndex 的 Markdown 分节切分',
    params: [
      { key: 'chunk_size', label: '块大小', type: 'number', default: 1200, min: 100, max: 5000 },
      { key: 'chunk_overlap', label: '重叠大小', type: 'number', default: 200, min: 0, max: 1000 }
    ]
  },
  code: {
    label: '代码分块',
    description: '按语法结构切分，保持函数/类完整',
    params: [
      { key: 'language', label: '语言', type: 'select', default: 'auto', 
        options: ['auto', 'python', 'javascript', 'typescript', 'java', 'go', 'rust'] },
      { key: 'max_chunk_size', label: '最大块大小', type: 'number', default: 2000, min: 500, max: 10000 },
      { key: 'include_imports', label: '包含导入语句', type: 'boolean', default: true }
    ]
  },
  llama_sentence: {
    label: '句子分块',
    description: '保持句子完整，基于 Token 计数',
    params: [
      { key: 'max_tokens', label: '最大 Token', type: 'number', default: 512, min: 50, max: 2000 },
      { key: 'chunk_overlap', label: '重叠 Token', type: 'number', default: 50, min: 0, max: 200 }
    ]
  },
  llama_token: {
    label: 'Token 分块',
    description: '严格按 Token 切分，精确控制长度',
    params: [
      { key: 'max_tokens', label: '最大 Token', type: 'number', default: 512, min: 50, max: 2000 },
      { key: 'chunk_overlap', label: '重叠 Token', type: 'number', default: 50, min: 0, max: 200 }
    ]
  }
};
```

### 5.2 检索器参数配置

```typescript
interface RetrieverParams {
  dense: {};  // 无参数
  bm25: {};   // 无参数
  hybrid: {
    dense_weight: number;   // 默认 0.7，范围 0-1
    sparse_weight: number;  // 默认 0.3，范围 0-1
  };
  fusion: {
    mode: 'rrf' | 'weighted';
    dense_weight?: number;   // weighted 模式
    bm25_weight?: number;    // weighted 模式
    rrf_k?: number;          // rrf 模式，默认 60
    rerank?: boolean;
    rerank_model?: string;
    rerank_top_n?: number;
  };
  hyde: {
    base_retriever: string;
    num_queries?: number;       // 默认 4
    include_original?: boolean; // 默认 true
  };
  multi_query: {
    base_retriever: string;
    num_queries?: number;       // 默认 3
    include_original?: boolean; // 默认 true
    rrf_k?: number;             // 默认 60
  };
  parent_document: {
    base_retriever: string;
    return_parent?: boolean;    // 默认 true
    include_child?: boolean;    // 默认 false
  };
}

const RETRIEVER_UI_CONFIG = {
  dense: {
    label: '向量检索',
    description: '基于语义相似度的稠密向量检索',
    params: []
  },
  bm25: {
    label: 'BM25 检索',
    description: '基于关键词匹配的稀疏检索',
    params: []
  },
  hybrid: {
    label: '混合检索',
    description: '向量 + BM25 加权融合',
    params: [
      { key: 'dense_weight', label: '向量权重', type: 'slider', default: 0.7, min: 0, max: 1, step: 0.1 },
      { key: 'sparse_weight', label: 'BM25 权重', type: 'slider', default: 0.3, min: 0, max: 1, step: 0.1 }
    ]
  },
  fusion: {
    label: '融合检索',
    description: 'RRF/加权融合 + 可选 Rerank',
    params: [
      { key: 'mode', label: '融合模式', type: 'select', default: 'rrf', options: ['rrf', 'weighted'] },
      { key: 'rrf_k', label: 'RRF 常数', type: 'number', default: 60, min: 1, max: 100, showWhen: { mode: 'rrf' } },
      { key: 'dense_weight', label: '向量权重', type: 'slider', default: 0.7, min: 0, max: 1, showWhen: { mode: 'weighted' } },
      { key: 'rerank', label: '启用 Rerank', type: 'boolean', default: false },
      { key: 'rerank_top_n', label: 'Rerank 数量', type: 'number', default: 10, min: 1, max: 50, showWhen: { rerank: true } }
    ]
  },
  hyde: {
    label: 'HyDE 检索',
    description: 'LLM 生成假设答案进行检索',
    params: [
      { key: 'base_retriever', label: '底层检索器', type: 'select', default: 'dense', options: ['dense', 'hybrid'] },
      { key: 'num_queries', label: '假设答案数', type: 'number', default: 4, min: 1, max: 10 },
      { key: 'include_original', label: '保留原始查询', type: 'boolean', default: true }
    ]
  },
  multi_query: {
    label: '多查询检索',
    description: 'LLM 生成查询变体，多路召回',
    params: [
      { key: 'base_retriever', label: '底层检索器', type: 'select', default: 'dense', options: ['dense', 'hybrid'] },
      { key: 'num_queries', label: '查询变体数', type: 'number', default: 3, min: 1, max: 10 },
      { key: 'include_original', label: '保留原始查询', type: 'boolean', default: true }
    ]
  },
  parent_document: {
    label: '父文档检索',
    description: '子块检索返回父块上下文',
    params: [
      { key: 'base_retriever', label: '底层检索器', type: 'select', default: 'dense', options: ['dense', 'hybrid'] },
      { key: 'return_parent', label: '返回父块', type: 'boolean', default: true },
      { key: 'include_child', label: '包含子块信息', type: 'boolean', default: false }
    ]
  }
};
```

---

## 6. 待优化项

### 6.1 切分器增强

| 优先级 | 功能 | 说明 |
|--------|------|------|
| 🔴 高 | 语义分块 | 基于句子嵌入的智能分块边界检测 |
| 🟡 中 | Q&A 模板 | 专门针对问答对的切分策略 |
| 🟡 中 | 文本清洗选项 | URL/邮箱/特殊字符过滤 |
| 🟢 低 | PDF 布局分析 | 识别表格、图片等结构 |

### 6.2 检索器增强

| 优先级 | 功能 | 说明 |
|--------|------|------|
| 🔴 高 | 分数阈值过滤 | 按相似度分数过滤低质量结果 |
| 🔴 高 | 元数据过滤 | 按文档属性过滤检索范围 |
| 🟡 中 | 自查询检索 | LLM 解析查询中的过滤条件 |
| 🟡 中 | 时间衰减 | 新文档权重更高 |

### 6.3 前端开发优先级

1. **P0 - 切分器参数动态配置**
   - 根据选择的切分器动态显示参数表单
   - 实时预览切分效果

2. **P1 - 检索器参数配置**
   - 检索器选择和参数配置
   - 混合检索权重调整滑块

3. **P2 - 高级配置**
   - Rerank 开关和模型选择
   - HyDE/MultiQuery 配置

---

## 附录：切分器输出元数据汇总

| 切分器 | 元数据字段 | 用途 |
|--------|-----------|------|
| `sliding_window` | `offset` | 定位原文位置 |
| `parent_child` | `parent_id`, `child`, `child_index` | 父子关联 |
| `markdown` | `h1`~`h6`, `heading_path` | 标题层级 |
| `markdown_section` | `heading` | 所属标题 |
| `code` | `language`, `function_name`, `class_name`, `imports` | 代码结构 |

---

*文档版本: 1.0.0*
*更新日期: 2024-12-09*
