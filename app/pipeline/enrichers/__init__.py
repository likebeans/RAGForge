"""
文档增强模块

提供文档和 Chunk 级别的增强功能：
- DocumentSummarizer: 文档摘要生成
- ChunkEnricher: Chunk 上下文增强
"""

from app.pipeline.enrichers.summarizer import (
    DocumentSummarizer,
    SummaryConfig,
    generate_summary,
)
from app.pipeline.enrichers.chunk_enricher import (
    ChunkEnricher,
    EnrichmentConfig,
    get_chunk_enricher,
)

__all__ = [
    "DocumentSummarizer",
    "SummaryConfig",
    "generate_summary",
    "ChunkEnricher",
    "EnrichmentConfig",
    "get_chunk_enricher",
]
