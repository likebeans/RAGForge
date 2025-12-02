# Chunkers 切分器模块

文本切分器实现，将长文本切分为适合向量化和检索的片段。

## 模块职责

- 提供多种文本切分策略
- 保持片段语义完整性
- 控制片段大小以适配向量模型和 LLM 上下文

## 可用切分器

| 名称 | 类 | 说明 |
|------|-----|------|
| `simple` | `SimpleChunker` | 按段落切分（双换行符） |
| `sliding_window` | `SlidingWindowChunker` | 滑动窗口切分，支持重叠 |
| `recursive` | `RecursiveChunker` | 递归字符切分，优先保持语义边界 |
| `markdown` | `MarkdownChunker` | Markdown 感知切分，按标题层级分块 |
| `code` | `CodeChunker` | 代码感知切分，按语法结构分块 |
| `parent_child` | `ParentChildChunker` | 父子分块，大块索引+小块检索 |
| `llama_sentence` | `LlamaSentenceChunker` | LlamaIndex 句子级切分 |
| `llama_token` | `LlamaTokenChunker` | LlamaIndex Token 级切分 |

## 切分器选型建议

| 场景 | 推荐切分器 | 原因 |
|------|-----------|------|
| 通用文档 | `recursive` | 优先保持语义边界（推荐） |
| 技术文档 | `markdown` | 按标题层级分块 |
| 代码库 | `code` | 保持函数/类完整性 |
| 长篇文章 | `parent_child` | 保留上下文，提升召回质量 |
| 精确问答 | `llama_sentence` | 保持句子完整，避免截断 |
| Token 敏感 | `llama_token` | 精确控制上下文长度 |
| 简单场景 | `simple` | 快速、无依赖 |

## 参数说明

### SimpleChunker
- 无参数，按 `\n\n` 切分

### SlidingWindowChunker
- `window`: 窗口大小（字符数），默认 512
- `overlap`: 重叠大小（字符数），默认 50

### ParentChildChunker
- `parent_size`: 父块大小，默认 2048
- `child_size`: 子块大小，默认 512
- `overlap`: 子块重叠，默认 50

### LlamaSentenceChunker
- `max_tokens`: 最大 Token 数，默认 512
- `chunk_overlap`: 重叠 Token 数，默认 50
- `tokenizer`: 分词器类型，默认 "tiktoken"

### LlamaTokenChunker
- `max_tokens`: 最大 Token 数，默认 512
- `chunk_overlap`: 重叠 Token 数，默认 50

### RecursiveChunker
- `chunk_size`: 目标块大小，默认 512
- `chunk_overlap`: 重叠大小，默认 50
- `separators`: 分隔符列表，默认 `["\n\n", "\n", "。", ".", " "]`

### MarkdownChunker
- `chunk_size`: 目标块大小，默认 512
- `chunk_overlap`: 重叠大小，默认 50
- `headers_to_split_on`: 要切分的标题级别，默认 `["#", "##", "###"]`

### CodeChunker
- `language`: 代码语言（"python"/"javascript"/"auto"），默认 "auto"
- `max_chunk_size`: 最大块大小，默认 2000
- `include_imports`: 是否在每块包含导入语句，默认 True
- 支持语言：Python（AST）、JavaScript/TypeScript、Java、Go、Rust（正则）

## 使用示例

```python
from app.pipeline import operator_registry

# 滑动窗口切分
chunker = operator_registry.get("chunker", "sliding_window")(window=1024, overlap=100)
pieces = chunker.chunk(long_text, metadata={"source": "doc1"})

# 父子分块
chunker = operator_registry.get("chunker", "parent_child")(parent_size=4096, child_size=512)
pieces = chunker.chunk(long_text)
# 返回的每个 piece 包含 parent_id，可用于检索后扩展上下文
```

## 输出格式

所有切分器返回 `list[ChunkPiece]`：

```python
@dataclass
class ChunkPiece:
    text: str       # 片段文本
    metadata: dict  # 元数据（可包含 parent_id、offset 等）
```

## 添加新切分器

1. 创建新文件 `my_chunker.py`
2. 实现 `BaseChunkerOperator` 协议
3. 使用装饰器注册：`@register_operator("chunker", "my_chunker")`
4. 在 `__init__.py` 中导入
