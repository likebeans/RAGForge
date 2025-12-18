"""
Indexers 模块

提供高级索引策略，如 RAPTOR（递归摘要树）。
"""

from app.pipeline.indexers.raptor import (
    RaptorNativeIndexer,
    RaptorNode,
    RaptorBuildResult,
    create_raptor_native_indexer_from_config,
    RAPTOR_NATIVE_AVAILABLE,
)

# 别名，保持向后兼容
RaptorIndexer = RaptorNativeIndexer

__all__ = [
    "RaptorIndexer",
    "RaptorNativeIndexer",
    "RaptorNode",
    "RaptorBuildResult",
    "create_raptor_native_indexer_from_config",
    "RAPTOR_NATIVE_AVAILABLE",
]
