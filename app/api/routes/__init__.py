"""
API 路由汇总

将所有子路由注册到主路由器，统一对外暴露。

路由模块说明：
- health.py    : 健康检查接口
- kb.py        : 知识库管理（创建、列表、删除）
- documents.py : 文档管理（上传、删除）
- query.py     : 检索接口（向量检索）
- rag.py       : RAG 生成接口（检索 + LLM 生成）
- api_keys.py  : API Key 管理
- admin.py     : 管理员接口（租户管理）
"""

from fastapi import APIRouter

from app.api.routes import (
    admin,
    api_keys,
    conversations,
    documents,
    enrichment,
    health,
    kb,
    model_providers,
    openai_compat,
    ground,
    pipeline_playground,
    query,
    rag,
    rag_stream,
    raptor,
)

# 主路由器，包含所有 API 端点
api_router = APIRouter()

# 注册各子路由，tags 用于 API 文档分组
api_router.include_router(health.router, tags=["health"])
api_router.include_router(kb.router, tags=["knowledge-bases"])
api_router.include_router(documents.router, tags=["documents"])
api_router.include_router(query.router, tags=["retrieve"])
api_router.include_router(rag.router, tags=["rag"])
api_router.include_router(rag_stream.router)  # SSE 流式 RAG
api_router.include_router(conversations.router)  # 对话管理
api_router.include_router(api_keys.router, tags=["api-keys"])
api_router.include_router(admin.router)  # admin 路由自带 tags
api_router.include_router(openai_compat.router)  # OpenAI 兼容接口
api_router.include_router(model_providers.router)  # 模型提供商管理
api_router.include_router(ground.router)  # Ground (playground)
api_router.include_router(pipeline_playground.router)  # Pipeline playground
api_router.include_router(enrichment.router, tags=["enrichment"])  # 增强预览
api_router.include_router(raptor.router)  # RAPTOR 索引管理
