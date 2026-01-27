# PDF 文件解析器（使用 MinerU 服务）

import logging
from .base import FileParser, ParseResult, ContentBlock, ContentType, ExtractionSchema

logger = logging.getLogger(__name__)


class PDFParser(FileParser):
    """PDF 文件解析器（使用 MinerU 服务）"""
    
    def __init__(self, mineru_base_url: str | None = None):
        """
        Args:
            mineru_base_url: MinerU 服务地址，如 http://localhost:8010
        """
        self._mineru_base_url = mineru_base_url
    
    @property
    def mineru_base_url(self) -> str:
        """获取 MinerU 服务地址"""
        if self._mineru_base_url:
            return self._mineru_base_url
        
        from app.config import get_settings
        settings = get_settings()
        return getattr(settings, "MINERU_BASE_URL", "http://localhost:8010")
    
    @property
    def supported_extensions(self) -> set[str]:
        return {".pdf"}
    
    async def parse(
        self,
        file_bytes: bytes,
        filename: str,
        extraction_schema: ExtractionSchema | None = None,
    ) -> ParseResult:
        """
        解析 PDF 文件
        
        1. 调用 MinerU 服务提取全文（含公式、图表）
        2. 如果有 extraction_schema，调用 LLM 进行结构化提取
        """
        from app.infra.mineru_client import MinerUClient
        
        # Step 1: MinerU 全文提取
        client = MinerUClient(base_url=self.mineru_base_url)
        
        try:
            mineru_result = await client.parse_pdf(file_bytes, filename)
        except Exception as e:
            logger.error(f"MinerU 解析失败，尝试本地回退: {e}")
            return await self._parse_local_fallback(file_bytes, filename)
        
        # 构建内容块
        blocks = self._build_blocks(mineru_result)
        
        # 合并全文
        full_content = mineru_result.get("markdown", "")
        if not full_content:
            full_content = "\n\n".join(b.content for b in blocks if b.content)
        
        # Step 2: 如果有 Schema，进行结构化提取
        extracted_fields = None
        if extraction_schema and extraction_schema.fields:
            extracted_fields = await self._extract_with_schema(
                full_content, extraction_schema
            )
        
        return ParseResult(
            content=full_content,
            blocks=blocks,
            metadata={
                "format": "pdf",
                "page_count": mineru_result.get("page_count", 0),
                "filename": filename,
                "parser": "mineru",
            },
            tables=mineru_result.get("tables"),
            extracted_fields=extracted_fields,
        )
    
    def _build_blocks(self, mineru_result: dict) -> list[ContentBlock]:
        """从 MinerU 结果构建内容块"""
        blocks = []
        
        for item in mineru_result.get("blocks", []):
            block_type = item.get("type", "text")
            content = item.get("content", "")
            
            if not content:
                continue
            
            if block_type == "table":
                blocks.append(ContentBlock(
                    type=ContentType.TABLE,
                    content=content,
                    raw_data=item.get("table_data"),
                    page=item.get("page"),
                    position=item.get("bbox"),
                ))
            elif block_type == "formula":
                blocks.append(ContentBlock(
                    type=ContentType.FORMULA,
                    content=content,
                    page=item.get("page"),
                    position=item.get("bbox"),
                ))
            elif block_type == "image":
                blocks.append(ContentBlock(
                    type=ContentType.IMAGE,
                    content=item.get("caption", "[图片]"),
                    raw_data=item.get("image_data"),
                    page=item.get("page"),
                    position=item.get("bbox"),
                ))
            else:
                blocks.append(ContentBlock(
                    type=ContentType.TEXT,
                    content=content,
                    page=item.get("page"),
                    position=item.get("bbox"),
                ))
        
        return blocks
    
    async def _extract_with_schema(
        self,
        content: str,
        schema: ExtractionSchema,
    ) -> dict:
        """使用 LLM 按 Schema 提取结构化字段"""
        from app.infra.llm import get_llm_client
        
        # 构建字段列表
        field_list = "\n".join([
            f"- {f['name']} ({f.get('type', 'string')})"
            for f in schema.fields
        ])
        
        # 限制内容长度避免 token 超限
        max_content_len = 8000
        truncated_content = content[:max_content_len]
        if len(content) > max_content_len:
            truncated_content += "\n\n[内容已截断...]"
        
        prompt = f"""请从以下文档内容中提取指定字段的信息。

## 需要提取的字段
{field_list}

## 文档内容
{truncated_content}

## 输出要求
1. 严格按照 JSON 格式返回
2. 如果某字段未找到，设为 null
3. 如果同一字段有多个值，返回数组
4. 保持字段名称与要求完全一致

请直接返回 JSON，不要包含其他文字："""
        
        try:
            llm = get_llm_client()
            response = await llm.complete(prompt, temperature=0.1)
            
            # 解析 JSON
            import json
            json_str = response
            
            # 尝试提取 JSON 部分
            if "```json" in response:
                json_str = response.split("```json")[1].split("```")[0]
            elif "```" in response:
                json_str = response.split("```")[1].split("```")[0]
            
            return json.loads(json_str.strip())
            
        except json.JSONDecodeError as e:
            logger.warning(f"LLM 返回的 JSON 解析失败: {e}")
            return {"_raw_response": response[:500], "_parse_error": True}
        except Exception as e:
            logger.error(f"Schema 提取失败: {e}")
            return {"_error": str(e)}
    
    async def _parse_local_fallback(
        self,
        file_bytes: bytes,
        filename: str,
    ) -> ParseResult:
        """本地回退方案（使用 PyMuPDF）"""
        try:
            import fitz  # PyMuPDF
        except ImportError:
            logger.error("PyMuPDF 未安装，无法使用本地回退方案")
            raise ValueError(
                "MinerU 服务不可用，且未安装 PyMuPDF 回退方案。"
                "请启动 MinerU 服务或安装 PyMuPDF: uv add pymupdf"
            )
        
        doc = fitz.open(stream=file_bytes, filetype="pdf")
        
        blocks = []
        content_parts = []
        
        for page_num, page in enumerate(doc, start=1):
            # 提取文本
            text = page.get_text("text")
            if text.strip():
                content_parts.append(f"## 第 {page_num} 页\n\n{text}")
                blocks.append(ContentBlock(
                    type=ContentType.TEXT,
                    content=text,
                    page=page_num,
                ))
        
        doc.close()
        
        return ParseResult(
            content="\n\n".join(content_parts),
            blocks=blocks,
            metadata={
                "format": "pdf",
                "page_count": len(doc),
                "filename": filename,
                "parser": "pymupdf_fallback",
            },
        )
