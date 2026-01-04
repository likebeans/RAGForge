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

from typing import Literal

from fastapi import Depends, Header, HTTPException, Request, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.api_key import APIKeyContext, get_api_key_context
from app.config import get_settings
from app.db.session import get_db
from app.models import Tenant
from app.infra.logging import set_tenant_id


async def get_tenant(
    request: Request,
    context: APIKeyContext = Depends(get_api_key_context),
) -> Tenant:
    """
    获取当前请求的租户
    
    通过 API Key 认证后，从上下文中提取租户信息。
    用于实现多租户数据隔离。
    同时设置 request.state 供审计日志中间件使用。
    """
    # 设置 request.state 供审计日志中间件使用
    request.state.tenant_id = context.tenant.id
    request.state.api_key_id = context.api_key.id
    set_tenant_id(context.tenant.id)
    return context.tenant


async def get_current_api_key(
    context: APIKeyContext = Depends(get_api_key_context),
) -> APIKeyContext:
    """获取当前 API Key 的完整上下文信息"""
    return context


# ==================== 管理员认证 ====================

async def verify_admin_token(
    x_admin_token: str | None = Header(None, alias="X-Admin-Token"),
) -> str:
    """
    验证管理员 Token
    
    管理员接口使用独立的 Token 认证，通过 X-Admin-Token 请求头传递。
    Token 值从环境变量 ADMIN_TOKEN 读取。
    """
    settings = get_settings()
    
    if not settings.admin_token:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail={"code": "ADMIN_API_NOT_CONFIGURED", "detail": "Admin API is not configured. Set ADMIN_TOKEN environment variable."},
        )
    
    if not x_admin_token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={"code": "MISSING_ADMIN_TOKEN", "detail": "Missing X-Admin-Token header"},
        )
    
    if x_admin_token != settings.admin_token:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail={"code": "INVALID_ADMIN_TOKEN", "detail": "Invalid admin token"},
        )
    
    return x_admin_token


# ==================== 角色权限检查 ====================

def require_role(*allowed_roles: Literal["admin", "write", "read"]):
    """
    创建角色权限检查依赖
    
    用法：
        @router.post("/create")
        async def create_item(
            context: APIKeyContext = Depends(require_role("admin", "write")),
        ):
            pass
    """
    async def check_role(
        context: APIKeyContext = Depends(get_api_key_context),
    ) -> APIKeyContext:
        # 检查租户状态
        if context.tenant.status != "active":
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Tenant is {context.tenant.status}",
            )
        
        # 检查角色权限
        if context.api_key.role not in allowed_roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Role '{context.api_key.role}' not allowed. Required: {allowed_roles}",
            )
        
        return context
    
    return check_role


# 重新导出数据库会话获取函数，方便路由模块导入
get_db_session = get_db
