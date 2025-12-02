"""
API 路由汇总

将所有子路由注册到主路由器，统一对外暴露。

路由模块说明：
- health.py    : 健康检查接口
- kb.py        : 知识库管理（创建、列表、删除）
- documents.py : 文档管理（上传、删除）
- query.py     : 检索接口（向量检索）
- api_keys.py  : API Key 管理
"""

from fastapi import APIRouter

from app.api.routes import api_keys, documents, health, kb, query

# 主路由器，包含所有 API 端点
api_router = APIRouter()

# 注册各子路由，tags 用于 API 文档分组
api_router.include_router(health.router, tags=["health"])
api_router.include_router(kb.router, tags=["knowledge-bases"])
api_router.include_router(documents.router, tags=["documents"])
api_router.include_router(query.router, tags=["retrieve"])
api_router.include_router(api_keys.router, tags=["api-keys"])
