# 文件解析器注册表

import logging
from .base import FileParser, ParseResult

logger = logging.getLogger(__name__)


class ParserRegistry:
    """文件解析器注册表（工厂模式）"""
    
    def __init__(self):
        self._parsers: dict[str, FileParser] = {}
        self._initialized = False
    
    def _ensure_initialized(self):
        """延迟初始化，避免循环导入"""
        if self._initialized:
            return
        
        self._initialized = True
        self._register_default_parsers()
    
    def _register_default_parsers(self):
        """注册默认解析器"""
        from .text_parser import TextParser
        from .excel_parser import ExcelParser
        from .word_parser import WordParser
        from .pdf_parser import PDFParser
        
        self.register(TextParser())
        self.register(ExcelParser())
        self.register(WordParser())
        self.register(PDFParser())
        
        logger.info(f"已注册 {len(self._parsers)} 个文件解析器: {list(self._parsers.keys())}")
    
    def register(self, parser: FileParser):
        """注册解析器"""
        for ext in parser.supported_extensions:
            self._parsers[ext] = parser
            logger.debug(f"注册解析器: {ext} -> {parser.__class__.__name__}")
    
    def get_parser(self, filename: str) -> FileParser | None:
        """根据文件名获取解析器"""
        self._ensure_initialized()
        ext = self._get_extension(filename)
        return self._parsers.get(ext)
    
    def can_parse(self, filename: str) -> bool:
        """判断是否支持解析该文件"""
        self._ensure_initialized()
        ext = self._get_extension(filename)
        return ext in self._parsers
    
    def supported_extensions(self) -> set[str]:
        """获取所有支持的扩展名"""
        self._ensure_initialized()
        return set(self._parsers.keys())
    
    def _get_extension(self, filename: str) -> str:
        """获取文件扩展名（小写，带点号）"""
        if "." not in filename:
            return ""
        return "." + filename.rsplit(".", 1)[-1].lower()
    
    async def parse(
        self,
        file_bytes: bytes,
        filename: str,
        extraction_schema=None,
    ) -> ParseResult:
        """
        解析文件（便捷方法）
        
        Args:
            file_bytes: 文件二进制内容
            filename: 文件名
            extraction_schema: 提取模板（可选）
        
        Returns:
            ParseResult: 解析结果
        
        Raises:
            ValueError: 不支持的文件类型
        """
        parser = self.get_parser(filename)
        if not parser:
            ext = self._get_extension(filename)
            supported = ", ".join(sorted(self.supported_extensions()))
            raise ValueError(f"不支持的文件类型: {ext}，支持的类型: {supported}")
        
        return await parser.parse(file_bytes, filename, extraction_schema)


# 全局单例
parser_registry = ParserRegistry()
