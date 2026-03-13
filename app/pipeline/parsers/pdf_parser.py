# PDF 文件解析器（使用 MinerU 服务）

import logging
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from sqlalchemy.ext.asyncio import AsyncSession

from .base import FileParser, ParseResult, ContentBlock, ContentType, ExtractionSchema

logger = logging.getLogger(__name__)


DEFAULT_EXTRACTION_FIELDS = [
    {"name": "项目", "type": "string"},
    {"name": "靶点", "type": "string"},
    {"name": "靶点类型", "type": "string"},
    {"name": "作用机制", "type": "string"},
    {"name": "研发机构", "type": "string"},
    {"name": "项目负责人/创始人", "type": "string"},
    {"name": "药物类型", "type": "string"},
    {"name": "药物剂型", "type": "string"},
    {"name": "研究阶段", "type": "string"},
    {"name": "药效数据", "type": "string"},
    {"name": "安全性数据", "type": "string"},
    {"name": "药代动力学数据", "type": "string"},
    {"name": "适应症", "type": "string"},
    {"name": "适应症类型", "type": "string"},
    {"name": "项目亮点", "type": "string"},
    {"name": "差异化创新点", "type": "string"},
    {"name": "主要药效指标（临床）", "type": "string"},
    {"name": "主要安全性指标（临床）", "type": "string"},
    {"name": "当前标准疗法及疗效", "type": "string"},
    {"name": "赛道竞争情况", "type": "string"},
    {"name": "专利情况", "type": "string"},
    {"name": "专利布局", "type": "string"},
    {"name": "报价与估值", "type": "string"},
    {"name": "项目估值", "type": "string"},
    {"name": "公司估值", "type": "string"},
    {"name": "综合评分", "type": "string"},
    {"name": "战略匹配度", "type": "string"},
    {"name": "风险提示", "type": "string"},
    {"name": "更新时间", "type": "string"},
    {"name": "跟进人", "type": "string"},
]


class PDFParser(FileParser):
    """PDF 文件解析器（使用 MinerU 服务）"""

    def __init__(self, mineru_base_url: str | None = None):
        """
        Args:
            mineru_base_url: MinerU 服务地址，如 http://localhost:8010
        """
        self._mineru_base_url = mineru_base_url

    @property
    def _settings(self):
        """获取配置"""
        from app.config import get_settings

        return get_settings()

    @property
    def mineru_enabled(self) -> bool:
        """是否启用 MinerU"""
        return getattr(self._settings, "mineru_enabled", True)

    @property
    def mineru_base_url(self) -> str:
        """获取 MinerU 服务地址"""
        if self._mineru_base_url:
            return self._mineru_base_url
        return getattr(self._settings, "mineru_base_url", "http://localhost:8010")

    @property
    def mineru_api_key(self) -> str | None:
        """获取 MinerU API Key"""
        return getattr(self._settings, "mineru_api_key", None)

    @property
    def mineru_timeout(self) -> int:
        """获取 MinerU 超时时间"""
        return getattr(self._settings, "mineru_timeout", 300)

    @property
    def supported_extensions(self) -> set[str]:
        return {".pdf"}

    async def parse(
        self,
        file_bytes: bytes,
        filename: str,
        extraction_schema: ExtractionSchema | None = None,
        tenant_id: str | None = None,
        db_session: "AsyncSession | None" = None,
    ) -> ParseResult:
        """
        解析 PDF 文件

        1. 调用 MinerU 服务提取全文（含公式、图表）
        2. 如果有 extraction_schema，调用 LLM 进行结构化提取
        """
        # 检查是否启用 MinerU
        if not self.mineru_enabled:
            logger.info("MinerU 未启用，使用本地解析")
            return await self._parse_local_fallback(
                file_bytes, filename, extraction_schema, tenant_id, db_session
            )

        from app.infra.mineru_client import MinerUClient

        # Step 1: MinerU 全文提取
        client = MinerUClient(
            base_url=self.mineru_base_url,
            timeout=self.mineru_timeout,
            api_key=self.mineru_api_key,
        )

        try:
            # 使用优化的参数调用MinerU
            mineru_result = await client.parse_pdf(
                file_bytes=file_bytes,
                filename=filename,
                backend="hybrid-auto-engine",  # 使用高精度混合引擎
                parse_method="auto",  # 自动选择解析方法
                lang_list=["ch", "en"],  # 支持中英文
                return_md=True,  # 返回markdown格式
                table_enable=True,  # 启用表格解析
                formula_enable=True,  # 启用公式解析
            )
        except Exception as e:
            logger.error(f"MinerU 解析失败，尝试本地回退: {e}")
            return await self._parse_local_fallback(
                file_bytes, filename, extraction_schema, tenant_id, db_session
            )

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
                full_content, extraction_schema, tenant_id, db_session
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
                blocks.append(
                    ContentBlock(
                        type=ContentType.TABLE,
                        content=content,
                        raw_data=item.get("table_data"),
                        page=item.get("page"),
                        position=item.get("bbox"),
                    )
                )
            elif block_type == "formula":
                blocks.append(
                    ContentBlock(
                        type=ContentType.FORMULA,
                        content=content,
                        page=item.get("page"),
                        position=item.get("bbox"),
                    )
                )
            elif block_type == "image":
                blocks.append(
                    ContentBlock(
                        type=ContentType.IMAGE,
                        content=item.get("caption", "[图片]"),
                        raw_data=item.get("image_data"),
                        page=item.get("page"),
                        position=item.get("bbox"),
                    )
                )
            else:
                blocks.append(
                    ContentBlock(
                        type=ContentType.TEXT,
                        content=content,
                        page=item.get("page"),
                        position=item.get("bbox"),
                    )
                )

        return blocks

    async def _extract_with_schema(
        self,
        content: str,
        schema: ExtractionSchema,
        tenant_id: str | None = None,
        db_session: "AsyncSession | None" = None,
    ) -> dict:
        """
        使用 LLM 按 Schema 提取结构化字段

        LLM 配置优先级：租户级 > 系统级 > 环境变量
        如果没有配置 LLM，返回警告信息

        如果未传入 schema 或 schema.fields 为空，使用默认字段模板
        """
        from app.services.model_config import model_config_resolver
        from app.models import Tenant
        from sqlalchemy import select

        # 使用默认字段模板（如果未传入 schema 或 fields 为空）
        fields = (
            schema.fields if schema and schema.fields else DEFAULT_EXTRACTION_FIELDS
        )

        # 构建字段列表
        field_list = "\n".join(
            [f"- {f['name']} ({f.get('type', 'string')})" for f in fields]
        )

        # 增加内容长度限制（此模板字段较多，需要更多内容）
        max_content_len = 15000
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
5. 所有字段都必须返回，不能遗漏

请直接返回 JSON，不要包含其他文字："""

        import json

        try:
            # 获取租户对象
            tenant = None
            if db_session and tenant_id:
                tenant_result = await db_session.execute(
                    select(Tenant).where(Tenant.id == tenant_id)
                )
                tenant = tenant_result.scalar_one_or_none()

            # 使用 model_config_resolver 获取 LLM 配置
            if db_session:
                llm_merged = await model_config_resolver.get_llm_config(
                    session=db_session,
                    tenant=tenant,
                )
                # 构建完整配置（含 API Key）
                llm_config = model_config_resolver.build_provider_config(
                    config=llm_merged,
                    config_type="llm",
                    tenant=tenant,
                )
            else:
                # 无数据库会话，使用环境变量配置
                from app.config import get_settings

                settings = get_settings()
                llm_config = settings.get_llm_config()

            provider = llm_config.get("provider")
            if not provider:
                logger.warning(f"未配置 LLM，无法提取字段 (tenant_id={tenant_id})")
                return {
                    "_warning": "未配置 LLM，请在租户设置或环境变量中配置 LLM 提供商",
                    "_tenant_id": tenant_id,
                }

            # 创建 LLM 客户端
            from app.infra.llm import create_llm_client

            llm = create_llm_client(
                provider=provider,
                model=llm_config.get("model", ""),
                api_key=llm_config.get("api_key"),
                base_url=llm_config.get("base_url"),
            )

            response = await llm.complete(prompt, temperature=0.1)

            # 解析 JSON
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
        extraction_schema: ExtractionSchema | None = None,
        tenant_id: str | None = None,
        db_session: "AsyncSession | None" = None,
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
        page_count = len(doc)

        for page_num, page in enumerate(doc, start=1):
            # 提取文本
            text = page.get_text("text")
            if text.strip():
                content_parts.append(f"## 第 {page_num} 页\n\n{text}")
                blocks.append(
                    ContentBlock(
                        type=ContentType.TEXT,
                        content=text,
                        page=page_num,
                    )
                )

        doc.close()

        full_content = "\n\n".join(content_parts)

        # 如果有 Schema，进行结构化提取
        extracted_fields = None
        if extraction_schema and extraction_schema.fields:
            extracted_fields = await self._extract_with_schema(
                full_content, extraction_schema, tenant_id, db_session
            )

        return ParseResult(
            content=full_content,
            blocks=blocks,
            metadata={
                "format": "pdf",
                "page_count": page_count,
                "filename": filename,
                "parser": "pymupdf_fallback",
            },
            extracted_fields=extracted_fields,
        )
