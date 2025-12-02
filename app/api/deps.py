"""
API 依赖注入函数

这个模块定义了所有 API 路由共用的依赖项。
FastAPI 的依赖注入系统会自动调用这些函数，并将结果注入到路由处理函数中。

使用示例：
    @router.get("/example")
    async def example_endpoint(
        tenant=Depends(get_tenant),         # 自动获取当前租户
        db=Depends(get_db_session),         # 自动获取数据库会话
    ):
        pass
"""

from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.api_key import APIKeyContext, get_api_key_context
from app.db.session import get_db
from app.models import Tenant


async def get_tenant(context: APIKeyContext = Depends(get_api_key_context)) -> Tenant:
    """
    获取当前请求的租户
    
    通过 API Key 认证后，从上下文中提取租户信息。
    用于实现多租户数据隔离。
    """
    return context.tenant


async def get_current_api_key(
    context: APIKeyContext = Depends(get_api_key_context),
) -> APIKeyContext:
    """获取当前 API Key 的完整上下文信息"""
    return context


# 重新导出数据库会话获取函数，方便路由模块导入
get_db_session = get_db
