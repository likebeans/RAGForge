"""
文档摘要生成器 (Document Summarizer)

用于在文档摄取时生成摘要，支持：
- 条件触发（文档长度超过阈值）
- LLM 调用失败时优雅回退
- 可配置摘要长度
"""

import logging
from dataclasses import dataclass

from openai import OpenAI

from app.config import get_settings

logger = logging.getLogger(__name__)


@dataclass
class SummaryConfig:
    """摘要生成配置"""
    enabled: bool = True
    min_tokens: int = 500        # 触发摘要生成的最小 token 数
    max_tokens: int = 300        # 摘要最大 token 数
    model: str | None = None     # 使用的模型，None 使用默认配置


# 默认摘要提示词
DEFAULT_SUMMARY_PROMPT = """请为以下文档内容生成一段简洁的摘要。

要求：
1. 摘要应概括文档的主要内容和关键信息
2. 保持客观，不添加原文没有的信息
3. 长度控制在 100-200 字
4. 使用与原文相同的语言

文档内容：
{content}

摘要："""


class DocumentSummarizer:
    """
    文档摘要生成器
    
    使用示例：
    ```python
    summarizer = DocumentSummarizer()
    summary = summarizer.generate(content="长文档内容...")
    # 返回 "这是一份关于..."
    ```
    """
    
    def __init__(
        self,
        min_tokens: int = 500,
        max_tokens: int = 300,
        model: str | None = None,
        prompt_template: str | None = None,
    ):
        self.min_tokens = min_tokens
        self.max_tokens = max_tokens
        self.prompt_template = prompt_template or DEFAULT_SUMMARY_PROMPT
        
        settings = get_settings()
        self.model = model or settings.doc_summary_model or settings.openai_model
        self._client: OpenAI | None = None
    
    def _get_client(self) -> OpenAI:
        """延迟初始化 OpenAI 客户端"""
        if self._client is None:
            settings = get_settings()
            if not settings.openai_api_key:
                raise ValueError("OPENAI_API_KEY 未配置，无法生成摘要")
            
            self._client = OpenAI(
                api_key=settings.openai_api_key,
                base_url=settings.openai_api_base,
            )
        return self._client
    
    def _estimate_tokens(self, text: str) -> int:
        """
        估算文本 token 数（简单实现）
        
        中文约 1.5 字/token，英文约 4 字符/token
        """
        # 简单估算：中英文混合，取平均
        return len(text) // 2
    
    def should_generate(self, content: str) -> bool:
        """判断是否需要生成摘要"""
        estimated_tokens = self._estimate_tokens(content)
        return estimated_tokens >= self.min_tokens
    
    def generate(self, content: str) -> str | None:
        """
        生成文档摘要
        
        Args:
            content: 文档内容
            
        Returns:
            摘要文本，失败返回 None
        """
        if not self.should_generate(content):
            logger.info(f"文档长度不足 {self.min_tokens} tokens，跳过摘要生成")
            return None
        
        try:
            client = self._get_client()
            
            # 如果内容太长，截取前面部分
            max_content_chars = 8000  # 约 4000 tokens
            truncated_content = content[:max_content_chars]
            if len(content) > max_content_chars:
                truncated_content += "\n...(内容已截断)"
            
            prompt = self.prompt_template.format(content=truncated_content)
            
            response = client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "user", "content": prompt}
                ],
                max_tokens=self.max_tokens,
                temperature=0.3,  # 低温度，保持一致性
            )
            
            if response.choices:
                summary = response.choices[0].message.content
                if summary:
                    summary = summary.strip()
                    logger.info(f"摘要生成成功，长度: {len(summary)} 字")
                    return summary
            
            return None
            
        except Exception as e:
            logger.warning(f"摘要生成失败: {e}")
            return None
    
    async def agenerate(self, content: str) -> str | None:
        """异步生成摘要"""
        import asyncio
        return await asyncio.to_thread(self.generate, content)
    
    @classmethod
    def from_config(cls, config: SummaryConfig) -> "DocumentSummarizer":
        """从配置创建实例"""
        return cls(
            min_tokens=config.min_tokens,
            max_tokens=config.max_tokens,
            model=config.model,
        )


def get_summarizer(config: SummaryConfig | None = None) -> DocumentSummarizer | None:
    """
    获取摘要生成器
    
    如果未配置 API Key 或未启用，返回 None
    """
    settings = get_settings()
    
    if config is None:
        config = SummaryConfig(
            enabled=settings.doc_summary_enabled,
            min_tokens=settings.doc_summary_min_tokens,
            max_tokens=settings.doc_summary_max_tokens,
            model=settings.doc_summary_model,
        )
    
    if not config.enabled:
        return None
    
    if not settings.openai_api_key:
        logger.warning("Document Summary 已启用但 OPENAI_API_KEY 未配置")
        return None
    
    return DocumentSummarizer.from_config(config)


async def generate_summary(content: str, config: SummaryConfig | None = None) -> str | None:
    """
    便捷函数：生成文档摘要
    
    Args:
        content: 文档内容
        config: 可选配置
        
    Returns:
        摘要文本，失败或跳过返回 None
    """
    summarizer = get_summarizer(config)
    if summarizer is None:
        return None
    
    return await summarizer.agenerate(content)
