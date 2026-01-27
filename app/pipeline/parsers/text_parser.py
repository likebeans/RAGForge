# 文本文件解析器（txt/md/json）

import json
import logging
from .base import FileParser, ParseResult, ContentBlock, ContentType, ExtractionSchema

logger = logging.getLogger(__name__)


class TextParser(FileParser):
    """文本文件解析器（txt/md/markdown/json）"""
    
    @property
    def supported_extensions(self) -> set[str]:
        return {".txt", ".md", ".markdown", ".json"}
    
    async def parse(
        self,
        file_bytes: bytes,
        filename: str,
        extraction_schema: ExtractionSchema | None = None,
    ) -> ParseResult:
        """解析文本文件"""
        ext = self._get_extension(filename)
        
        # 解码文本
        try:
            content = file_bytes.decode("utf-8")
        except UnicodeDecodeError:
            # 尝试其他编码
            try:
                content = file_bytes.decode("gbk")
            except UnicodeDecodeError:
                content = file_bytes.decode("utf-8", errors="replace")
                logger.warning(f"文件 {filename} 编码异常，使用替换模式解码")
        
        # JSON 特殊处理
        if ext == ".json":
            try:
                data = json.loads(content)
                # 格式化为可读文本
                if isinstance(data, dict):
                    content = self._dict_to_markdown(data)
                elif isinstance(data, list):
                    content = self._list_to_markdown(data)
            except json.JSONDecodeError:
                logger.warning(f"JSON 解析失败，按纯文本处理: {filename}")
        
        return ParseResult(
            content=content,
            blocks=[ContentBlock(type=ContentType.TEXT, content=content)],
            metadata={
                "format": ext.lstrip("."),
                "filename": filename,
                "char_count": len(content),
            },
        )
    
    def _dict_to_markdown(self, data: dict, level: int = 0) -> str:
        """将字典转换为 Markdown 格式"""
        lines = []
        indent = "  " * level
        
        for key, value in data.items():
            if isinstance(value, dict):
                lines.append(f"{indent}- **{key}**:")
                lines.append(self._dict_to_markdown(value, level + 1))
            elif isinstance(value, list):
                lines.append(f"{indent}- **{key}**:")
                lines.append(self._list_to_markdown(value, level + 1))
            else:
                lines.append(f"{indent}- **{key}**: {value}")
        
        return "\n".join(lines)
    
    def _list_to_markdown(self, data: list, level: int = 0) -> str:
        """将列表转换为 Markdown 格式"""
        lines = []
        indent = "  " * level
        
        for i, item in enumerate(data):
            if isinstance(item, dict):
                lines.append(f"{indent}{i + 1}.")
                lines.append(self._dict_to_markdown(item, level + 1))
            elif isinstance(item, list):
                lines.append(f"{indent}{i + 1}.")
                lines.append(self._list_to_markdown(item, level + 1))
            else:
                lines.append(f"{indent}- {item}")
        
        return "\n".join(lines)
