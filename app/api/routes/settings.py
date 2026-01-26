"""
设置管理 API

提供租户模型配置的读取和更新接口。
支持 Provider API Keys 和默认模型的持久化配置。
"""

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
import logging

logger = logging.getLogger(__name__)

from app.api.deps import get_current_api_key, get_db_session, get_tenant
from app.auth.api_key import APIKeyContext
from app.models import Tenant

router = APIRouter(prefix="/v1/settings", tags=["settings"])


# ==================== Pydantic Schemas ====================


class ProviderConfig(BaseModel):
    """Provider 配置"""
    api_key: str | None = Field(default=None, description="API Key（返回时脱敏）")
    base_url: str | None = Field(default=None, description="自定义 Base URL")


class ModelChoice(BaseModel):
    """模型选择"""
    provider: str = Field(..., description="提供商 ID")
    model: str = Field(..., description="模型名称")


class DefaultModels(BaseModel):
    """默认模型配置"""
    llm: ModelChoice | None = Field(default=None, description="默认 LLM 模型")
    embedding: ModelChoice | None = Field(default=None, description="默认 Embedding 模型")
    rerank: ModelChoice | None = Field(default=None, description="默认 Rerank 模型")


class ModelSettingsResponse(BaseModel):
    """模型配置响应（API Key 脱敏）"""
    providers: dict[str, ProviderConfig] = Field(
        default_factory=dict,
        description="Provider 配置（API Key 脱敏显示）"
    )
    defaults: DefaultModels | None = Field(
        default=None, 
        description="默认模型配置"
    )


class ModelSettingsUpdate(BaseModel):
    """模型配置更新请求"""
    providers: dict[str, ProviderConfig] | None = Field(
        default=None,
        description="Provider 配置（含 API Key）"
    )
    defaults: DefaultModels | None = Field(
        default=None,
        description="默认模型配置"
    )


# ==================== API Endpoints ====================


def _mask_api_key(api_key: str | None) -> str | None:
    """脱敏 API Key，只显示前后几位"""
    if not api_key:
        return None
    if len(api_key) <= 8:
        return "*" * len(api_key)
    return api_key[:4] + "*" * (len(api_key) - 8) + api_key[-4:]


def _mask_providers(providers: dict) -> dict:
    """脱敏所有 Provider 的 API Key"""
    result = {}
    for provider_id, config in providers.items():
        if isinstance(config, dict):
            result[provider_id] = {
                "api_key": _mask_api_key(config.get("api_key")),
                "base_url": config.get("base_url"),
            }
        else:
            result[provider_id] = config
    return result


@router.get("/models", response_model=ModelSettingsResponse)
async def get_model_settings(
    tenant=Depends(get_tenant),
    api_key_ctx: APIKeyContext = Depends(get_current_api_key),
    db: AsyncSession = Depends(get_db_session),
):
    """
    获取当前租户的模型配置
    
    返回 Provider 配置和默认模型配置。
    API Key 会脱敏显示，只显示前后 4 位。
    """
    settings = tenant.model_settings or {}
    
    # 提取并脱敏 Provider 配置
    providers = settings.get("providers", {})
    masked_providers = _mask_providers(providers)
    
    # 提取默认模型配置
    defaults_raw = settings.get("defaults", {})
    defaults = None
    if defaults_raw:
        defaults = DefaultModels(
            llm=ModelChoice(**defaults_raw["llm"]) if defaults_raw.get("llm") else None,
            embedding=ModelChoice(**defaults_raw["embedding"]) if defaults_raw.get("embedding") else None,
            rerank=ModelChoice(**defaults_raw["rerank"]) if defaults_raw.get("rerank") else None,
        )
    
    return ModelSettingsResponse(
        providers={k: ProviderConfig(**v) for k, v in masked_providers.items()},
        defaults=defaults,
    )


@router.put("/models", response_model=ModelSettingsResponse)
async def update_model_settings(
    payload: ModelSettingsUpdate,
    tenant=Depends(get_tenant),
    api_key_ctx: APIKeyContext = Depends(get_current_api_key),
    db: AsyncSession = Depends(get_db_session),
):
    """
    更新当前租户的模型配置
    
    支持部分更新：
    - 只传 providers 则只更新 Provider 配置
    - 只传 defaults 则只更新默认模型配置
    - 两者都传则全部更新
    
    注意：API Key 在请求中需要传完整值，响应中会脱敏显示。
    """
    # 检查权限：只有 admin 角色可以更新设置
    if api_key_ctx.api_key.role != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail={"code": "PERMISSION_DENIED", "detail": "只有 admin 角色可以更新模型配置"},
        )
    
    # 显式查询租户以确保在当前会话中
    tenant_id = tenant.id
    result = await db.execute(
        select(Tenant).where(Tenant.id == tenant_id).with_for_update()
    )
    db_tenant = result.scalar_one_or_none()
    
    if not db_tenant:
        raise HTTPException(status_code=404, detail="Tenant not found")
    
    # 获取现有配置
    current_settings = db_tenant.model_settings or {}
    
    # 合并更新
    if payload.providers is not None:
        # 更新 Provider 配置
        current_providers = current_settings.get("providers", {})
        for provider_id, config in payload.providers.items():
            if config.api_key or config.base_url:
                current_providers[provider_id] = {
                    "api_key": config.api_key,
                    "base_url": config.base_url,
                }
            else:
                # 如果都是 None，删除该 Provider
                current_providers.pop(provider_id, None)
        current_settings["providers"] = current_providers
    
    if payload.defaults is not None:
        # 更新默认模型配置
        defaults_dict = {}
        if payload.defaults.llm:
            defaults_dict["llm"] = {
                "provider": payload.defaults.llm.provider,
                "model": payload.defaults.llm.model,
            }
        if payload.defaults.embedding:
            defaults_dict["embedding"] = {
                "provider": payload.defaults.embedding.provider,
                "model": payload.defaults.embedding.model,
            }
        if payload.defaults.rerank:
            defaults_dict["rerank"] = {
                "provider": payload.defaults.rerank.provider,
                "model": payload.defaults.rerank.model,
            }
        current_settings["defaults"] = defaults_dict
    
    # 直接更新数据库
    db_tenant.model_settings = current_settings
    
    # 使用 UPDATE 语句直接更新
    from sqlalchemy import update
    stmt = update(Tenant).where(Tenant.id == tenant_id).values(model_settings=current_settings)
    await db.execute(stmt)
    await db.commit()
    
    # 返回更新后的配置（脱敏）
    providers = db_tenant.model_settings.get("providers", {})
    masked_providers = _mask_providers(providers)
    
    defaults_raw = db_tenant.model_settings.get("defaults", {})
    defaults = None
    if defaults_raw:
        defaults = DefaultModels(
            llm=ModelChoice(**defaults_raw["llm"]) if defaults_raw.get("llm") else None,
            embedding=ModelChoice(**defaults_raw["embedding"]) if defaults_raw.get("embedding") else None,
            rerank=ModelChoice(**defaults_raw["rerank"]) if defaults_raw.get("rerank") else None,
        )
    
    return ModelSettingsResponse(
        providers={k: ProviderConfig(**v) for k, v in masked_providers.items()},
        defaults=defaults,
    )
    
    # 返回更新后的配置（脱敏）
    providers = current_settings.get("providers", {})
    masked_providers = _mask_providers(providers)
    
    defaults_raw = current_settings.get("defaults", {})
    defaults = None
    if defaults_raw:
        defaults = DefaultModels(
            llm=ModelChoice(**defaults_raw["llm"]) if defaults_raw.get("llm") else None,
            embedding=ModelChoice(**defaults_raw["embedding"]) if defaults_raw.get("embedding") else None,
            rerank=ModelChoice(**defaults_raw["rerank"]) if defaults_raw.get("rerank") else None,
        )
    
    return ModelSettingsResponse(
        providers={k: ProviderConfig(**v) for k, v in masked_providers.items()},
        defaults=defaults,
    )
