"""
查询变换模块

提供查询增强功能：
- HyDEQueryTransform: 假设文档嵌入查询变换
- QueryRouter: 查询路由，自动选择最佳检索策略
- RAGFusionTransform: 多查询扩展
"""

from app.pipeline.query_transforms.hyde import (
    HyDEQueryTransform,
    HyDEConfig,
)
from app.pipeline.query_transforms.router import (
    QueryRouter,
    QueryType,
    RouteResult,
    RouterConfig,
    route_query,
    get_query_router,
)
from app.pipeline.query_transforms.rag_fusion import (
    RAGFusionTransform,
    FusionConfig,
    get_rag_fusion_transform,
    expand_query,
)

__all__ = [
    "HyDEQueryTransform",
    "HyDEConfig",
    "QueryRouter",
    "QueryType",
    "RouteResult",
    "RouterConfig",
    "route_query",
    "get_query_router",
    "RAGFusionTransform",
    "FusionConfig",
    "get_rag_fusion_transform",
    "expand_query",
]
