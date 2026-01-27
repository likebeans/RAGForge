# 文件解析器基类和数据结构

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any
from enum import Enum


class ContentType(str, Enum):
    """内容类型"""
    TEXT = "text"
    TABLE = "table"
    IMAGE = "image"
    FORMULA = "formula"


@dataclass
class ContentBlock:
    """内容块（文本/表格/图片/公式）"""
    type: ContentType
    content: str                      # 文本内容或 Markdown 格式
    raw_data: Any = None              # 原始数据（表格为 list[list]，图片为 bytes）
    page: int | None = None           # PDF 页码
    position: dict | None = None      # 位置信息（bbox）


@dataclass
class ParseResult:
    """解析结果"""
    content: str                      # 合并后的全文（Markdown 格式）
    blocks: list[ContentBlock] = field(default_factory=list)  # 分块内容
    metadata: dict[str, Any] = field(default_factory=dict)    # 元数据
    tables: list[dict] | None = None  # 提取的表格（结构化 JSON）
    images: list[bytes] | None = None # 提取的图片
    extracted_fields: dict | None = None  # 按 Schema 提取的字段


@dataclass 
class ExtractionSchema:
    """提取模板（从 xlsx 解析）"""
    id: str
    name: str
    fields: list[dict]                # [{"name": "产品名称", "type": "string", "required": True}]
    source_file: str = ""             # 来源 xlsx 文件名


class FileParser(ABC):
    """文件解析器基类"""
    
    @property
    @abstractmethod
    def supported_extensions(self) -> set[str]:
        """支持的文件扩展名（小写，带点号）"""
        pass
    
    @abstractmethod
    async def parse(
        self,
        file_bytes: bytes,
        filename: str,
        extraction_schema: ExtractionSchema | None = None,
    ) -> ParseResult:
        """
        解析文件
        
        Args:
            file_bytes: 文件二进制内容
            filename: 文件名
            extraction_schema: 提取模板（可选，用于结构化提取）
        
        Returns:
            ParseResult: 解析结果
        """
        pass
    
    def can_parse(self, filename: str) -> bool:
        """判断是否支持解析该文件"""
        ext = self._get_extension(filename)
        return ext in self.supported_extensions
    
    def _get_extension(self, filename: str) -> str:
        """获取文件扩展名（小写）"""
        if "." not in filename:
            return ""
        return "." + filename.rsplit(".", 1)[-1].lower()
