"""
HyDE (Hypothetical Document Embeddings) 查询变换

原理：用 LLM 生成用户问题的「假设答案」，用假设答案的嵌入去检索，
而非原始问题。假设答案与文档风格更接近，可解决「问题 vs 答案」语义鸿沟。

特性：
- 可配置生成的假设答案数量
- 可选是否保留原始查询
- 支持条件触发（召回不足时）
- LLM 调用失败时优雅回退到原始查询
"""

import logging
from dataclasses import dataclass, field
from typing import Any

from openai import OpenAI

from app.config import get_settings

logger = logging.getLogger(__name__)


@dataclass
class HyDEConfig:
    """HyDE 配置"""
    enabled: bool = True
    num_queries: int = 4           # 生成的假设答案数量
    include_original: bool = True  # 是否保留原始查询
    max_tokens: int = 2000         # 假设答案最大 token 数（qwen3 thinking 需要较多 token）
    model: str | None = None       # 使用的模型，None 使用默认配置


# 默认 HyDE 提示词（/no_think 放在开头禁用 qwen3 的 thinking 模式）
DEFAULT_HYDE_PROMPT = """/no_think
请根据以下问题，写一段可能包含答案的文档内容。
不要直接回答问题，而是假设你在写一篇包含该问题答案的文档片段。
保持内容简洁、专业，像是从技术文档或知识库中摘录的。

问题：{query}

文档片段："""


class HyDEQueryTransform:
    """
    HyDE 查询变换器
    
    将用户问题转换为假设性答案，用于改善检索效果。
    
    使用示例：
    ```python
    transform = HyDEQueryTransform()
    hypothetical_docs = transform.generate(query="什么是RAG？")
    # 返回 ["RAG是一种结合检索和生成的技术...", ...]
    ```
    """
    
    def __init__(
        self,
        num_queries: int = 4,
        include_original: bool = True,
        max_tokens: int = 256,
        model: str | None = None,
        prompt_template: str | None = None,
    ):
        self.num_queries = num_queries
        self.include_original = include_original
        self.max_tokens = max_tokens
        self.prompt_template = prompt_template or DEFAULT_HYDE_PROMPT
        
        settings = get_settings()
        self.model = model or settings.openai_model
        self._client: OpenAI | None = None
    
    def _get_client(self) -> OpenAI:
        """延迟初始化 OpenAI 客户端"""
        if self._client is None:
            settings = get_settings()
            if not settings.openai_api_key:
                raise ValueError("OPENAI_API_KEY 未配置，无法使用 HyDE")
            
            self._client = OpenAI(
                api_key=settings.openai_api_key,
                base_url=settings.openai_api_base,
            )
        return self._client
    
    def generate(self, query: str) -> list[str]:
        """
        生成假设性文档
        
        Args:
            query: 原始查询
            
        Returns:
            假设性文档列表（可能包含原始查询）
        """
        results = []
        
        # 可选保留原始查询
        if self.include_original:
            results.append(query)
        
        try:
            client = self._get_client()
            prompt = self.prompt_template.format(query=query)
            
            # 批量生成假设答案
            for _ in range(self.num_queries):
                response = client.chat.completions.create(
                    model=self.model,
                    messages=[
                        {"role": "user", "content": prompt}
                    ],
                    max_tokens=self.max_tokens,
                    temperature=0.7,  # 适度随机以生成多样化答案
                )
                
                if response.choices:
                    hypothetical_doc = response.choices[0].message.content
                    if hypothetical_doc:
                        results.append(hypothetical_doc.strip())
            
            logger.info(f"HyDE 生成了 {len(results) - (1 if self.include_original else 0)} 个假设答案")
            
        except Exception as e:
            logger.warning(f"HyDE 生成失败，回退到原始查询: {e}")
            # 确保至少返回原始查询
            if query not in results:
                results.append(query)
        
        return results
    
    async def agenerate(self, query: str) -> list[str]:
        """
        异步生成假设性文档
        
        使用 asyncio.to_thread 包装同步调用，避免阻塞事件循环
        """
        import asyncio
        return await asyncio.to_thread(self.generate, query)
    
    @classmethod
    def from_config(cls, config: HyDEConfig) -> "HyDEQueryTransform":
        """从配置创建实例"""
        return cls(
            num_queries=config.num_queries,
            include_original=config.include_original,
            max_tokens=config.max_tokens,
            model=config.model,
        )


def get_hyde_transform(config: HyDEConfig | None = None) -> HyDEQueryTransform | None:
    """
    获取 HyDE 变换器
    
    如果未配置 API Key 或未启用，返回 None
    """
    settings = get_settings()
    
    if config is None:
        config = HyDEConfig(
            enabled=settings.hyde_enabled,
            num_queries=settings.hyde_num_queries,
            include_original=settings.hyde_include_original,
            max_tokens=settings.hyde_max_tokens,
        )
    
    if not config.enabled:
        return None
    
    if not settings.openai_api_key:
        logger.warning("HyDE 已启用但 OPENAI_API_KEY 未配置")
        return None
    
    return HyDEQueryTransform.from_config(config)
