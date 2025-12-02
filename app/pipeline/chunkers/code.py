"""
代码感知切分器 (Code Chunker)

按代码语法结构（class/function/method）分块，保持代码逻辑完整性。

支持语言：
- Python（使用 AST 解析）
- JavaScript/TypeScript（正则匹配）
- Java/Go/Rust（正则匹配）

特点：
- 保持函数/类的完整性
- 自动检测语言或手动指定
- 超长代码块自动二次分割
- 保留导入语句上下文
"""

import ast
import re
from dataclasses import dataclass
from typing import Literal

from app.pipeline.base import BaseChunkerOperator, ChunkPiece
from app.pipeline.registry import register_operator


# 语言类型
LanguageType = Literal["python", "javascript", "typescript", "java", "go", "rust", "auto"]


@dataclass
class CodeBlock:
    """代码块"""
    text: str
    block_type: str  # "import", "class", "function", "method", "other"
    name: str | None
    line_start: int
    line_end: int
    language: str


# 文件扩展名到语言的映射
EXTENSION_TO_LANGUAGE = {
    ".py": "python",
    ".js": "javascript",
    ".ts": "typescript",
    ".tsx": "typescript",
    ".jsx": "javascript",
    ".java": "java",
    ".go": "go",
    ".rs": "rust",
}


def detect_language(text: str, filename: str | None = None) -> str:
    """检测代码语言"""
    if filename:
        for ext, lang in EXTENSION_TO_LANGUAGE.items():
            if filename.endswith(ext):
                return lang
    
    # 基于内容启发式检测
    if "def " in text and "import " in text:
        return "python"
    if "function " in text or "const " in text or "=>" in text:
        return "javascript"
    if "public class " in text or "private " in text:
        return "java"
    if "func " in text and "package " in text:
        return "go"
    if "fn " in text and "let mut " in text:
        return "rust"
    
    return "python"  # 默认 Python


def parse_python(source: str) -> list[CodeBlock]:
    """解析 Python 代码"""
    blocks: list[CodeBlock] = []
    lines = source.split("\n")
    
    try:
        tree = ast.parse(source)
    except SyntaxError:
        # 解析失败，作为单个代码块返回
        return [CodeBlock(
            text=source,
            block_type="other",
            name=None,
            line_start=1,
            line_end=len(lines),
            language="python",
        )]
    
    # 收集导入语句
    imports: list[ast.stmt] = []
    for node in ast.iter_child_nodes(tree):
        if isinstance(node, (ast.Import, ast.ImportFrom)):
            imports.append(node)
    
    if imports:
        import_start = min(n.lineno for n in imports)
        import_end = max(n.end_lineno or n.lineno for n in imports)
        import_text = "\n".join(lines[import_start - 1:import_end])
        blocks.append(CodeBlock(
            text=import_text,
            block_type="import",
            name=None,
            line_start=import_start,
            line_end=import_end,
            language="python",
        ))
    
    # 收集类和函数定义
    for node in ast.iter_child_nodes(tree):
        if isinstance(node, ast.ClassDef):
            end_line = node.end_lineno or node.lineno
            class_text = "\n".join(lines[node.lineno - 1:end_line])
            blocks.append(CodeBlock(
                text=class_text,
                block_type="class",
                name=node.name,
                line_start=node.lineno,
                line_end=end_line,
                language="python",
            ))
        elif isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            end_line = node.end_lineno or node.lineno
            func_text = "\n".join(lines[node.lineno - 1:end_line])
            blocks.append(CodeBlock(
                text=func_text,
                block_type="function",
                name=node.name,
                line_start=node.lineno,
                line_end=end_line,
                language="python",
            ))
    
    # 如果没有提取到任何块，返回整个代码
    if not blocks:
        blocks.append(CodeBlock(
            text=source,
            block_type="other",
            name=None,
            line_start=1,
            line_end=len(lines),
            language="python",
        ))
    
    return blocks


def parse_javascript(source: str) -> list[CodeBlock]:
    """解析 JavaScript/TypeScript 代码（正则匹配）"""
    blocks: list[CodeBlock] = []
    lines = source.split("\n")
    
    # 匹配函数定义
    # function name(...) { ... }
    # const name = (...) => { ... }
    # const name = function(...) { ... }
    func_pattern = re.compile(
        r'^(?:export\s+)?(?:async\s+)?(?:function\s+(\w+)|(?:const|let|var)\s+(\w+)\s*=\s*(?:async\s+)?(?:function|\([^)]*\)\s*=>))',
        re.MULTILINE
    )
    
    # 匹配类定义
    class_pattern = re.compile(
        r'^(?:export\s+)?class\s+(\w+)',
        re.MULTILINE
    )
    
    # 匹配导入语句
    import_pattern = re.compile(
        r'^(?:import\s+.*?(?:from\s+[\'"].*?[\'"])?;?|const\s+\{[^}]+\}\s*=\s*require\([\'"].*?[\'"]\);?)',
        re.MULTILINE
    )
    
    # 提取导入
    import_matches = list(import_pattern.finditer(source))
    if import_matches:
        import_text = "\n".join(m.group(0) for m in import_matches)
        first_line = source[:import_matches[0].start()].count("\n") + 1
        last_line = source[:import_matches[-1].end()].count("\n") + 1
        blocks.append(CodeBlock(
            text=import_text,
            block_type="import",
            name=None,
            line_start=first_line,
            line_end=last_line,
            language="javascript",
        ))
    
    # 简单按顶级定义分块
    # 这是一个简化实现，实际生产中可能需要更复杂的解析
    current_pos = 0
    for match in re.finditer(r'^(?:export\s+)?(?:async\s+)?(?:function|class|const|let|var)\s+\w+', source, re.MULTILINE):
        # 找到定义的结束位置（简单匹配对应的闭合大括号）
        start_pos = match.start()
        line_start = source[:start_pos].count("\n") + 1
        
        # 简单估算：向后找到足够的闭合
        depth = 0
        end_pos = start_pos
        in_block = False
        for i, char in enumerate(source[start_pos:], start_pos):
            if char == "{":
                depth += 1
                in_block = True
            elif char == "}":
                depth -= 1
                if in_block and depth == 0:
                    end_pos = i + 1
                    break
        
        if end_pos > start_pos:
            block_text = source[start_pos:end_pos]
            line_end = source[:end_pos].count("\n") + 1
            
            # 判断类型
            if "class " in match.group(0):
                block_type = "class"
            else:
                block_type = "function"
            
            # 提取名称
            name_match = re.search(r'(?:function|class|const|let|var)\s+(\w+)', match.group(0))
            name = name_match.group(1) if name_match else None
            
            blocks.append(CodeBlock(
                text=block_text,
                block_type=block_type,
                name=name,
                line_start=line_start,
                line_end=line_end,
                language="javascript",
            ))
    
    if not blocks:
        blocks.append(CodeBlock(
            text=source,
            block_type="other",
            name=None,
            line_start=1,
            line_end=len(lines),
            language="javascript",
        ))
    
    return blocks


def parse_generic(source: str, language: str) -> list[CodeBlock]:
    """通用解析器（基于正则）"""
    lines = source.split("\n")
    
    # 通用函数/类模式
    patterns = {
        "java": {
            "class": r'^(?:public|private|protected)?\s*(?:static\s+)?class\s+(\w+)',
            "function": r'^(?:public|private|protected)?\s*(?:static\s+)?[\w<>\[\]]+\s+(\w+)\s*\(',
        },
        "go": {
            "function": r'^func\s+(?:\([^)]+\)\s+)?(\w+)\s*\(',
            "type": r'^type\s+(\w+)\s+(?:struct|interface)',
        },
        "rust": {
            "function": r'^(?:pub\s+)?(?:async\s+)?fn\s+(\w+)',
            "struct": r'^(?:pub\s+)?struct\s+(\w+)',
            "impl": r'^impl(?:<[^>]+>)?\s+(\w+)',
        },
    }
    
    lang_patterns = patterns.get(language, {})
    blocks: list[CodeBlock] = []
    
    # 简单分块：每个顶级定义作为一个块
    for block_type, pattern in lang_patterns.items():
        for match in re.finditer(pattern, source, re.MULTILINE):
            start_pos = match.start()
            line_start = source[:start_pos].count("\n") + 1
            
            # 找到块结束（简单匹配大括号）
            depth = 0
            end_pos = start_pos
            in_block = False
            for i, char in enumerate(source[start_pos:], start_pos):
                if char == "{":
                    depth += 1
                    in_block = True
                elif char == "}":
                    depth -= 1
                    if in_block and depth == 0:
                        end_pos = i + 1
                        break
            
            if end_pos > start_pos:
                block_text = source[start_pos:end_pos]
                line_end = source[:end_pos].count("\n") + 1
                name = match.group(1) if match.groups() else None
                
                blocks.append(CodeBlock(
                    text=block_text,
                    block_type=block_type,
                    name=name,
                    line_start=line_start,
                    line_end=line_end,
                    language=language,
                ))
    
    if not blocks:
        blocks.append(CodeBlock(
            text=source,
            block_type="other",
            name=None,
            line_start=1,
            line_end=len(lines),
            language=language,
        ))
    
    return blocks


@register_operator("chunker", "code")
class CodeChunker(BaseChunkerOperator):
    """
    代码感知切分器
    
    按代码语法结构分块，保持函数/类的完整性。
    
    使用示例：
    ```python
    chunker = operator_registry.get("chunker", "code")(
        language="python",
        max_chunk_size=2000,
        include_imports=True,
    )
    pieces = chunker.chunk(code_text)
    ```
    """
    
    name = "code"
    kind = "chunker"
    
    def __init__(
        self,
        language: LanguageType = "auto",
        max_chunk_size: int = 2000,
        include_imports: bool = True,
        filename: str | None = None,
    ):
        """
        Args:
            language: 代码语言，"auto" 自动检测
            max_chunk_size: 最大块大小（字符数），超过则二次分割
            include_imports: 是否在每个块前包含导入语句
            filename: 文件名，用于辅助语言检测
        """
        self.language = language
        self.max_chunk_size = max_chunk_size
        self.include_imports = include_imports
        self.filename = filename
    
    def _parse_code(self, text: str) -> list[CodeBlock]:
        """解析代码"""
        lang = self.language
        if lang == "auto":
            lang = detect_language(text, self.filename)
        
        if lang == "python":
            return parse_python(text)
        elif lang in ("javascript", "typescript"):
            return parse_javascript(text)
        else:
            return parse_generic(text, lang)
    
    def _split_large_block(self, block: CodeBlock) -> list[CodeBlock]:
        """分割过大的代码块"""
        if len(block.text) <= self.max_chunk_size:
            return [block]
        
        # 按行分割
        lines = block.text.split("\n")
        chunks: list[CodeBlock] = []
        current_lines: list[str] = []
        current_size = 0
        current_start = block.line_start
        
        for i, line in enumerate(lines):
            line_size = len(line) + 1  # +1 for newline
            
            if current_size + line_size > self.max_chunk_size and current_lines:
                # 保存当前块
                chunks.append(CodeBlock(
                    text="\n".join(current_lines),
                    block_type=block.block_type,
                    name=f"{block.name}_part{len(chunks) + 1}" if block.name else None,
                    line_start=current_start,
                    line_end=current_start + len(current_lines) - 1,
                    language=block.language,
                ))
                current_lines = []
                current_size = 0
                current_start = block.line_start + i
            
            current_lines.append(line)
            current_size += line_size
        
        # 保存最后一块
        if current_lines:
            chunks.append(CodeBlock(
                text="\n".join(current_lines),
                block_type=block.block_type,
                name=f"{block.name}_part{len(chunks) + 1}" if block.name else None,
                line_start=current_start,
                line_end=block.line_end,
                language=block.language,
            ))
        
        return chunks
    
    def chunk(self, text: str, metadata: dict | None = None) -> list[ChunkPiece]:
        """切分代码"""
        metadata = metadata or {}
        blocks = self._parse_code(text)
        
        # 提取导入块
        import_block: CodeBlock | None = None
        other_blocks: list[CodeBlock] = []
        
        for block in blocks:
            if block.block_type == "import":
                import_block = block
            else:
                other_blocks.append(block)
        
        # 分割过大的块
        final_blocks: list[CodeBlock] = []
        for block in other_blocks:
            final_blocks.extend(self._split_large_block(block))
        
        # 生成 ChunkPiece
        pieces: list[ChunkPiece] = []
        
        for block in final_blocks:
            # 构建文本
            if self.include_imports and import_block and block.block_type != "import":
                chunk_text = f"{import_block.text}\n\n{block.text}"
            else:
                chunk_text = block.text
            
            # 构建 metadata
            chunk_metadata = metadata.copy()
            chunk_metadata.update({
                "language": block.language,
                "block_type": block.block_type,
                "line_start": block.line_start,
                "line_end": block.line_end,
            })
            if block.name:
                chunk_metadata["name"] = block.name
            
            pieces.append(ChunkPiece(text=chunk_text, metadata=chunk_metadata))
        
        # 如果没有提取到任何块，返回原始文本
        if not pieces:
            lang = self.language if self.language != "auto" else detect_language(text, self.filename)
            pieces.append(ChunkPiece(
                text=text,
                metadata={
                    **metadata,
                    "language": lang,
                    "block_type": "other",
                    "line_start": 1,
                    "line_end": text.count("\n") + 1,
                },
            ))
        
        return pieces
