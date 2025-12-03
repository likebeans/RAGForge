# Enrichers 文档增强模块

文档和 Chunk 的 LLM 增强处理，用于提升检索质量。

## 模块职责

- 文档摘要生成（摄取时）
- Chunk 上下文增强（摄取时）
- 提升检索召回率和准确性

## 可用组件

| 名称 | 类 | 说明 | 默认状态 |
|------|-----|------|----------|
| 文档摘要 | `DocumentSummarizer` | LLM 生成文档摘要 | 关闭 |
| Chunk 增强 | `ChunkEnricher` | LLM 增强 Chunk 上下文 | 关闭 |

## 配置说明

### 环境变量

```bash
# Document Summary 配置
DOC_SUMMARY_ENABLED=false       # 是否启用文档摘要
DOC_SUMMARY_MIN_TOKENS=500      # 触发摘要的最小 token 数
DOC_SUMMARY_MAX_TOKENS=500      # 摘要最大 token 数
DOC_SUMMARY_MODEL=              # 使用的模型，空则使用默认 LLM

# Chunk Enrichment 配置
CHUNK_ENRICHMENT_ENABLED=false  # 是否启用 Chunk 增强（默认关闭）
CHUNK_ENRICHMENT_MAX_TOKENS=800 # 增强文本最大 token 数
CHUNK_ENRICHMENT_CONTEXT_CHUNKS=1  # 上下文 chunk 数量（前后各 N 个）
CHUNK_ENRICHMENT_MODEL=         # 使用的模型，空则使用默认 LLM
```

### 注意事项

- **成本警告**: 这两个功能都会调用 LLM，会显著增加 API 调用成本
- **qwen3 兼容**: 如果使用 qwen3 thinking 模式，需要较大的 max_tokens（建议 500+）
- **默认关闭**: 生产环境建议按需启用

## DocumentSummarizer 文档摘要

### 功能说明

在文档摄取时自动生成摘要，存储在文档元数据中，可用于：
- 检索结果展示
- Chunk 增强的上下文
- 文档预览

### 参数说明

| 参数 | 类型 | 默认值 | 说明 |
|------|------|--------|------|
| `min_tokens` | int | 500 | 触发摘要生成的最小 token 数 |
| `max_tokens` | int | 500 | 摘要最大 token 数 |
| `model` | str | None | 使用的模型，None 使用默认 |
| `prompt_template` | str | 内置 | 摘要生成提示词 |

### 使用示例

```python
from app.pipeline.enrichers.summarizer import DocumentSummarizer, generate_summary

# 方式一：直接使用类
summarizer = DocumentSummarizer(min_tokens=100, max_tokens=500)
summary = summarizer.generate(content="长文档内容...")

# 方式二：使用便捷函数（自动读取配置）
summary = await generate_summary(content="长文档内容...")
```

### 输出示例

```
输入: 复方南五加口服液是一种中药制剂，主要由五加皮、黄芪、当归等...（500字）

输出: 复方南五加口服液为中药制剂，主要成分包括五加皮、黄芪、当归等。
该药具有温阳益气、养心安神功效，适用于气血亏虚、阳气不足引起的症状。
用法为口服，每次10毫升，每日2次，早晚空腹服用。
```

## ChunkEnricher Chunk 增强

### 功能说明

使用 LLM 对 Chunk 进行上下文增强，生成更丰富的语义描述：
- 添加来源信息（文档名、章节）
- 生成上下文摘要
- 提取关键实体
- 添加消歧描述

### 参数说明

| 参数 | 类型 | 默认值 | 说明 |
|------|------|--------|------|
| `max_tokens` | int | 800 | 增强文本最大 token 数 |
| `context_chunks` | int | 1 | 上下文 chunk 数量（前后各 N 个） |
| `model` | str | None | 使用的模型，None 使用默认 |
| `prompt_template` | str | 内置 | 增强提示词 |

### 使用示例

```python
from app.pipeline.enrichers.chunk_enricher import ChunkEnricher

enricher = ChunkEnricher(max_tokens=800, context_chunks=1)

# 增强单个 chunk
enriched = enricher.enrich(
    chunk_text="## 【用法用量】\n\n口服，一次10毫升...",
    doc_title="复方南五加口服液说明书",
    doc_summary="复方南五加口服液为中药制剂...",
    preceding_chunks=["## 【功能主治】\n\n温阳益气..."],
    succeeding_chunks=["## 【注意事项】\n\n1. 忌辛辣..."],
)

# 批量增强
chunks = [{"text": "...", "chunk_index": 0}, ...]
enriched_chunks = await enricher.enrich_chunks(
    chunks=chunks,
    doc_title="文档标题",
    doc_summary="文档摘要",
)
```

### 输出示例

```
原始 Chunk:
## 【用法用量】
口服，一次10毫升，一日2次，早晚空腹时服。

增强后:
本段内容位于说明书"功能主治"与"注意事项"之间，属于药品使用说明的核心部分，
明确具体服用方法。关键实体包括药品名称"复方南五加口服液"、剂量"10毫升"、
频次"一日2次"及服用条件"早晚空腹时服"。需注意"空腹时服"指每次服药前应保持
空腹状态。原文核心信息为口服剂量及服用时间要求。
```

## 集成到摄取流程

这两个功能目前作为独立模块使用，可以在自定义摄取流程中调用：

```python
from app.pipeline.enrichers.summarizer import generate_summary
from app.pipeline.enrichers.chunk_enricher import get_chunk_enricher

async def custom_ingest(content: str, chunks: list):
    # 1. 生成文档摘要
    summary = await generate_summary(content)
    
    # 2. 增强 chunks
    enricher = get_chunk_enricher()
    if enricher:
        chunks = await enricher.enrich_chunks(
            chunks=chunks,
            doc_title="文档标题",
            doc_summary=summary,
        )
    
    return summary, chunks
```

## 测试记录

**测试日期**: 2024-12-03

| 功能 | 状态 | 说明 |
|------|------|------|
| DocumentSummarizer | ✅ 通过 | LLM 正确生成文档摘要 |
| ChunkEnricher | ✅ 通过 | LLM 正确增强 Chunk 上下文 |

**测试环境**:
- LLM: ollama/qwen3:14b
- max_tokens: 800（适配 qwen3 thinking 模式）
