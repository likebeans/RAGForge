# Chunkers 切分器模块

文本切分器实现，将长文本切分为适合向量化和检索的片段。

## 模块职责

- 提供多种文本切分策略
- 保持片段语义完整性
- 控制片段大小以适配向量模型和 LLM 上下文

## 可用切分器

| 名称 | 类 | 说明 |
|------|-----|------|
| `simple` | `SimpleChunker` | 按自定义分隔符切分 |
| `sliding_window` | `SlidingWindowChunker` | 滑动窗口切分，支持重叠 |
| `recursive` | `RecursiveChunker` | 递归字符切分，优先保持语义边界 |
| `markdown` | `MarkdownChunker` | Markdown 感知切分，按标题层级分块 |
| `code` | `CodeChunker` | 代码感知切分，按语法结构分块 |
| `parent_child` | `ParentChildChunker` | 父子分块，子块检索+父块上下文 |
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

## 分隔符格式

所有支持分隔符参数的切分器都支持以下转义序列：

| 输入 | 实际分隔符 | 说明 |
|------|-----------|------|
| `\n\n` | 双换行 | 段落分隔 |
| `\n` | 单换行 | 行分隔 |
| `\t` | 制表符 | Tab 分隔 |
| `。` `.` `;` | 原样使用 | 句号/分号 |
| 其他字符 | 原样使用 | 自定义分隔符 |

## 参数说明

### SimpleChunker
- `separator`: 分隔符，默认 `\n\n`，支持自定义（如 `\n`、`。`、`|||`）
- `max_chars`: 分段最大长度，默认 1024

### SlidingWindowChunker
- `window`: 窗口大小（字符数），默认 512
- `overlap`: 重叠大小（字符数），默认 50

### ParentChildChunker

子块用于检索，父块用作上下文。支持两种父块模式：

**父块配置：**
- `parent_mode`: 父块模式，默认 `paragraph`
  - `paragraph`: 按分隔符和最大长度分段
  - `full_doc`: 整个文档作为父块（超过 40000 字符自动截断）
- `parent_separator`: 父块分隔符（仅 paragraph 模式），默认 `\n\n`
- `parent_max_chars`: 父块最大长度（仅 paragraph 模式），默认 1024

**子块配置：**
- `child_separator`: 子块分隔符，默认 `\n`
- `child_max_chars`: 子块最大长度，默认 512

**输出元数据：**
- 父块：`chunk_id`, `child=false`, `parent_mode`
- 子块：`parent_id`, `child=true`, `child_index`

### RecursiveChunker
- `chunk_size`: 目标块大小，默认 1024
- `chunk_overlap`: 重叠大小，默认 256
- `separators`: 分隔符优先级列表，默认 `["\n\n", "\n", " ", ""]`
  - 支持逗号分隔的字符串格式：`"\n\n,\n,。,."`
- `keep_separator`: 是否保留分隔符在片段中，默认 `true`

### MarkdownChunker
- `chunk_size`: 目标块大小，默认 1024
- `chunk_overlap`: 重叠大小，默认 256
- `headers_to_split_on`: 要切分的标题级别
  - 默认 `[("#", "h1"), ("##", "h2"), ("###", "h3"), ("####", "h4")]`
  - 支持逗号分隔的字符串格式：`"#,##,###"`
- `strip_headers`: 是否从片段内容中移除标题行，默认 `false`

### CodeChunker
- `language`: 代码语言（`python`/`javascript`/`auto`），默认 `auto`
- `max_chunk_size`: 最大块大小，默认 2000
- `include_imports`: 是否在每块包含导入语句，默认 `true`
- 支持语言：Python（AST）、JavaScript/TypeScript、Java、Go、Rust（正则）

### LlamaSentenceChunker
- `max_tokens`: 最大 Token 数，默认 512
- `chunk_overlap`: 重叠 Token 数，默认 50
- `tokenizer`: 分词器类型，默认 `tiktoken`

### LlamaTokenChunker
- `max_tokens`: 最大 Token 数，默认 512
- `chunk_overlap`: 重叠 Token 数，默认 50

## 使用示例

```python
from app.pipeline import operator_registry

# 简单分段（自定义分隔符）
chunker = operator_registry.get("chunker", "simple")(separator="。", max_chars=500)
pieces = chunker.chunk(long_text)

# 递归切分（字符串格式分隔符）
chunker = operator_registry.get("chunker", "recursive")(
    chunk_size=1024,
    separators="\\n\\n,\\n,。,.",
    keep_separator=True
)
pieces = chunker.chunk(long_text)

# 父子分块（段落模式）
chunker = operator_registry.get("chunker", "parent_child")(
    parent_mode="paragraph",
    parent_separator="\\n\\n",
    parent_max_chars=2000,
    child_separator="\\n",
    child_max_chars=500
)
pieces = chunker.chunk(long_text)
# 父块: metadata={"chunk_id": "p_0", "child": false, "parent_mode": "paragraph"}
# 子块: metadata={"parent_id": "p_0", "child": true, "child_index": 1}

# 父子分块（全文模式）
chunker = operator_registry.get("chunker", "parent_child")(
    parent_mode="full_doc",
    child_separator="。",
    child_max_chars=300
)
pieces = chunker.chunk(long_text)

# Markdown 切分（字符串格式标题）
chunker = operator_registry.get("chunker", "markdown")(
    headers_to_split_on="#,##,###",
    strip_headers=True
)
pieces = chunker.chunk(markdown_text)
```

## 输出格式

所有切分器返回 `list[ChunkPiece]`：

```python
@dataclass
class ChunkPiece:
    text: str       # 片段文本
    metadata: dict  # 元数据
```

**常见元数据字段：**
- `parent_id`: 父块 ID（父子分块的子块）
- `child`: 是否为子块（父子分块）
- `child_index`: 子块序号（父子分块）
- `chunk_id`: 块 ID（父子分块的父块）
- `parent_mode`: 父块模式（父子分块）
- `h1`, `h2`, `h3`...: 标题层级信息（Markdown 切分）

## 添加新切分器

1. 创建新文件 `my_chunker.py`
2. 实现 `BaseChunkerOperator` 协议
3. 使用装饰器注册：`@register_operator("chunker", "my_chunker")`
4. 在 `__init__.py` 中导入

```python
from app.pipeline.base import BaseChunkerOperator, ChunkPiece
from app.pipeline.registry import register_operator

@register_operator("chunker", "my_chunker")
class MyChunker(BaseChunkerOperator):
    name = "my_chunker"
    kind = "chunker"
    
    def __init__(self, param1: str = "default"):
        self.param1 = param1
    
    def chunk(self, text: str, metadata: dict | None = None) -> list[ChunkPiece]:
        # 实现切分逻辑
        return [ChunkPiece(text=text, metadata=metadata or {})]
```
