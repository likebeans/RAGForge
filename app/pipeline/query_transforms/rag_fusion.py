"""
RAG Fusion 多查询扩展

生成多个查询变体，提高召回覆盖率。

策略：
- 同义词改写：使用不同的词汇表达相同意思
- 问题分解：将复杂问题拆成子问题
- 视角变换：从不同角度提问

融合：多路召回后 RRF 融合。
"""

import logging
from dataclasses import dataclass

from openai import OpenAI

from app.config import get_settings

logger = logging.getLogger(__name__)


@dataclass 
class FusionConfig:
    """RAG Fusion 配置"""
    enabled: bool = True
    num_queries: int = 3        # 生成的查询变体数量
    include_original: bool = True  # 是否保留原始查询
    max_tokens: int = 100       # 每个查询变体的最大 token 数
    model: str | None = None    # 使用的模型


# 查询扩展提示词
QUERY_EXPANSION_PROMPT = """你是一个查询扩展助手。给定一个用户查询，生成 {num_queries} 个不同的查询变体，用于提高信息检索的覆盖率。

原始查询：{query}

生成策略：
1. 同义词改写：使用不同的词汇表达相同意思
2. 视角变换：从不同角度提问
3. 具体化/抽象化：使查询更具体或更抽象

要求：
- 每个变体一行
- 保持与原始查询相同的语言
- 变体之间要有差异
- 不要编号，直接输出查询

生成的查询变体："""


class RAGFusionTransform:
    """
    RAG Fusion 查询扩展器
    
    使用示例：
    ```python
    transform = RAGFusionTransform(num_queries=3)
    queries = transform.generate("什么是 RAG？")
    # 返回 ["什么是 RAG？", "RAG 技术是什么意思？", "检索增强生成的原理是什么？", ...]
    ```
    """
    
    def __init__(
        self,
        num_queries: int = 3,
        include_original: bool = True,
        max_tokens: int = 100,
        model: str | None = None,
    ):
        """
        Args:
            num_queries: 生成的查询变体数量
            include_original: 是否保留原始查询
            max_tokens: 每个查询变体的最大 token 数
            model: 使用的模型
        """
        self.num_queries = num_queries
        self.include_original = include_original
        self.max_tokens = max_tokens
        
        settings = get_settings()
        self.model = model or settings.openai_model
        self._client: OpenAI | None = None
    
    def _get_client(self) -> OpenAI:
        """延迟初始化 OpenAI 客户端"""
        if self._client is None:
            settings = get_settings()
            if not settings.openai_api_key:
                raise ValueError("OPENAI_API_KEY 未配置，无法进行查询扩展")
            
            self._client = OpenAI(
                api_key=settings.openai_api_key,
                base_url=settings.openai_api_base,
            )
        return self._client
    
    def generate(self, query: str) -> list[str]:
        """
        生成查询变体（同步）
        
        Args:
            query: 原始查询
            
        Returns:
            查询变体列表（包含原始查询如果 include_original=True）
        """
        results: list[str] = []
        
        # 添加原始查询
        if self.include_original:
            results.append(query)
        
        try:
            client = self._get_client()
            
            prompt = QUERY_EXPANSION_PROMPT.format(
                num_queries=self.num_queries,
                query=query,
            )
            
            response = client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "user", "content": prompt}
                ],
                max_tokens=self.max_tokens * self.num_queries,
                temperature=0.7,
            )
            
            if response.choices:
                content = response.choices[0].message.content
                if content:
                    # 解析生成的查询变体
                    variants = [
                        line.strip() 
                        for line in content.strip().split("\n")
                        if line.strip() and line.strip() != query
                    ]
                    
                    # 限制数量
                    results.extend(variants[:self.num_queries])
                    logger.debug(f"生成 {len(variants)} 个查询变体")
            
        except Exception as e:
            logger.warning(f"查询扩展失败: {e}")
            # 失败时仅返回原始查询
        
        return results if results else [query]
    
    async def agenerate(self, query: str) -> list[str]:
        """异步生成查询变体"""
        import asyncio
        return await asyncio.to_thread(self.generate, query)
    
    @classmethod
    def from_config(cls, config: FusionConfig) -> "RAGFusionTransform":
        """从配置创建实例"""
        return cls(
            num_queries=config.num_queries,
            include_original=config.include_original,
            max_tokens=config.max_tokens,
            model=config.model,
        )


def get_rag_fusion_transform(config: FusionConfig | None = None) -> RAGFusionTransform | None:
    """
    获取 RAG Fusion 变换器
    
    Args:
        config: 配置
        
    Returns:
        RAGFusionTransform 实例，未启用时返回 None
    """
    if config is None:
        config = FusionConfig()
    
    if not config.enabled:
        return None
    
    settings = get_settings()
    if not settings.openai_api_key:
        logger.warning("RAG Fusion 已启用但 OPENAI_API_KEY 未配置")
        return None
    
    return RAGFusionTransform.from_config(config)


# 便捷函数
def expand_query(query: str, num_queries: int = 3) -> list[str]:
    """
    扩展查询
    
    Args:
        query: 原始查询
        num_queries: 生成的变体数量
        
    Returns:
        查询变体列表
    """
    transform = RAGFusionTransform(num_queries=num_queries)
    return transform.generate(query)
