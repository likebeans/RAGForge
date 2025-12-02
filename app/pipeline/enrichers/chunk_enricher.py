"""
Chunk Enrichment 增强器

用 LLM 对 chunk 进行上下文增强，生成更丰富的语义描述。
参考 R2R 和智谱的 Contextual 方案。

增强内容包括：
- 来源信息（文档名、章节）
- 上下文摘要
- 关键实体
- 消歧描述

注意：此功能默认关闭，因为会显著增加 LLM 调用成本。
"""

import logging
from dataclasses import dataclass
from typing import Any

from openai import OpenAI

from app.config import get_settings

logger = logging.getLogger(__name__)


@dataclass
class EnrichmentConfig:
    """Chunk Enrichment 配置"""
    enabled: bool = False           # 默认关闭
    max_tokens: int = 512           # 增强文本最大 token 数
    context_chunks: int = 1         # 上下文 chunk 数量（前后各 N 个）
    model: str | None = None        # 使用的模型


# 默认增强提示词（参考智谱方案）
DEFAULT_ENRICHMENT_PROMPT = """你是一个文档增强助手。请为以下文本片段添加上下文信息，使其更容易被检索到。

文档标题：{doc_title}
{context_info}

当前片段：
{chunk_text}

请生成一段增强描述，包含：
1. 简要说明这段内容在文档中的位置和作用
2. 提取关键实体和概念
3. 如有歧义，添加消歧说明
4. 保持原文的核心信息

要求：
- 使用与原文相同的语言
- 长度控制在 200 字以内
- 直接输出增强后的文本，不要添加标签

增强后的文本："""


class ChunkEnricher:
    """
    Chunk 增强器
    
    使用示例：
    ```python
    enricher = ChunkEnricher()
    enriched = enricher.enrich(
        chunk_text="某段文本...",
        doc_title="文档标题",
        preceding_chunks=["前文1", "前文2"],
        succeeding_chunks=["后文1"],
    )
    ```
    """
    
    def __init__(
        self,
        max_tokens: int = 512,
        context_chunks: int = 1,
        model: str | None = None,
        prompt_template: str | None = None,
    ):
        self.max_tokens = max_tokens
        self.context_chunks = context_chunks
        self.prompt_template = prompt_template or DEFAULT_ENRICHMENT_PROMPT
        
        settings = get_settings()
        self.model = model or settings.chunk_enrichment_model or settings.openai_model
        self._client: OpenAI | None = None
    
    def _get_client(self) -> OpenAI:
        """延迟初始化 OpenAI 客户端"""
        if self._client is None:
            settings = get_settings()
            if not settings.openai_api_key:
                raise ValueError("OPENAI_API_KEY 未配置，无法进行 Chunk Enrichment")
            
            self._client = OpenAI(
                api_key=settings.openai_api_key,
                base_url=settings.openai_api_base,
            )
        return self._client
    
    def _build_context_info(
        self,
        preceding_chunks: list[str] | None,
        succeeding_chunks: list[str] | None,
    ) -> str:
        """构建上下文信息"""
        parts = []
        
        if preceding_chunks:
            parts.append("前文内容：")
            for i, chunk in enumerate(preceding_chunks):
                parts.append(f"  [{i+1}] {chunk[:200]}...")
        
        if succeeding_chunks:
            parts.append("后文内容：")
            for i, chunk in enumerate(succeeding_chunks):
                parts.append(f"  [{i+1}] {chunk[:200]}...")
        
        return "\n".join(parts) if parts else "（无上下文）"
    
    def enrich(
        self,
        chunk_text: str,
        doc_title: str = "",
        preceding_chunks: list[str] | None = None,
        succeeding_chunks: list[str] | None = None,
        doc_summary: str | None = None,
    ) -> str | None:
        """
        增强单个 chunk
        
        Args:
            chunk_text: 原始 chunk 文本
            doc_title: 文档标题
            preceding_chunks: 前置 chunk 文本列表
            succeeding_chunks: 后置 chunk 文本列表
            doc_summary: 文档摘要（可选）
            
        Returns:
            增强后的文本，失败返回 None
        """
        try:
            client = self._get_client()
            
            context_info = self._build_context_info(preceding_chunks, succeeding_chunks)
            if doc_summary:
                context_info = f"文档摘要：{doc_summary}\n\n{context_info}"
            
            prompt = self.prompt_template.format(
                doc_title=doc_title or "未知",
                context_info=context_info,
                chunk_text=chunk_text,
            )
            
            response = client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "user", "content": prompt}
                ],
                max_tokens=self.max_tokens,
                temperature=0.3,
            )
            
            if response.choices:
                enriched = response.choices[0].message.content
                if enriched:
                    enriched = enriched.strip()
                    logger.debug(f"Chunk 增强成功，长度: {len(enriched)} 字")
                    return enriched
            
            return None
            
        except Exception as e:
            logger.warning(f"Chunk 增强失败: {e}")
            return None
    
    async def aenrich(
        self,
        chunk_text: str,
        doc_title: str = "",
        preceding_chunks: list[str] | None = None,
        succeeding_chunks: list[str] | None = None,
        doc_summary: str | None = None,
    ) -> str | None:
        """异步增强"""
        import asyncio
        return await asyncio.to_thread(
            self.enrich,
            chunk_text,
            doc_title,
            preceding_chunks,
            succeeding_chunks,
            doc_summary,
        )
    
    async def enrich_chunks(
        self,
        chunks: list[dict[str, Any]],
        doc_title: str = "",
        doc_summary: str | None = None,
    ) -> list[dict[str, Any]]:
        """
        批量增强 chunks
        
        Args:
            chunks: chunk 列表，每个 chunk 需包含 "text" 和 "chunk_index"
            doc_title: 文档标题
            doc_summary: 文档摘要
            
        Returns:
            增强后的 chunks，新增 "enriched_text" 字段
        """
        # 按 chunk_index 排序
        sorted_chunks = sorted(chunks, key=lambda x: x.get("chunk_index", 0))
        texts = [c["text"] for c in sorted_chunks]
        
        results = []
        for i, chunk in enumerate(sorted_chunks):
            # 获取前后上下文
            start = max(0, i - self.context_chunks)
            end = min(len(texts), i + self.context_chunks + 1)
            
            preceding = texts[start:i] if i > 0 else None
            succeeding = texts[i+1:end] if i < len(texts) - 1 else None
            
            # 增强
            enriched = await self.aenrich(
                chunk_text=chunk["text"],
                doc_title=doc_title,
                preceding_chunks=preceding,
                succeeding_chunks=succeeding,
                doc_summary=doc_summary,
            )
            
            result = chunk.copy()
            result["enriched_text"] = enriched
            result["enrichment_status"] = "completed" if enriched else "failed"
            results.append(result)
        
        return results
    
    @classmethod
    def from_config(cls, config: EnrichmentConfig) -> "ChunkEnricher":
        """从配置创建实例"""
        return cls(
            max_tokens=config.max_tokens,
            context_chunks=config.context_chunks,
            model=config.model,
        )


def get_chunk_enricher(config: EnrichmentConfig | None = None) -> ChunkEnricher | None:
    """
    获取 Chunk 增强器
    
    如果未配置 API Key 或未启用，返回 None
    """
    settings = get_settings()
    
    if config is None:
        config = EnrichmentConfig(
            enabled=settings.chunk_enrichment_enabled,
            max_tokens=settings.chunk_enrichment_max_tokens,
            context_chunks=settings.chunk_enrichment_context_chunks,
            model=settings.chunk_enrichment_model,
        )
    
    if not config.enabled:
        return None
    
    if not settings.openai_api_key:
        logger.warning("Chunk Enrichment 已启用但 OPENAI_API_KEY 未配置")
        return None
    
    return ChunkEnricher.from_config(config)
