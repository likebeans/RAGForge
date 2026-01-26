"""
模型配置管理 API

提供租户级模型配置的 CRUD 操作。
用户可以配置自己的 Embedding/LLM/Rerank 模型 API Key。
"""

import logging

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_api_key, get_db_session, get_tenant, require_role
from app.auth.api_key import APIKeyContext
from app.models import Tenant, TenantModelConfig
from app.schemas import (
    ModelConfigCreate,
    ModelConfigListResponse,
    ModelConfigResponse,
    ModelConfigResponseWithKey,
    ModelConfigUpdate,
    TenantModelConfigCheck,
)

logger = logging.getLogger(__name__)

router = APIRouter()


@router.get("/v1/model-configs", response_model=ModelConfigListResponse)
async def list_model_configs(
    config_type: str | None = None,
    tenant: Tenant = Depends(get_tenant),
    _: APIKeyContext = Depends(get_current_api_key),
    db: AsyncSession = Depends(get_db_session),
):
    """
    列出当前租户的所有模型配置

    - 如果指定 config_type，则只返回该类型的配置
    - 返回的配置不包含 api_key（安全考虑）
    """
    query = select(TenantModelConfig).where(
        TenantModelConfig.tenant_id == tenant.id,
        TenantModelConfig.is_active == True,
    )

    if config_type:
        query = query.where(TenantModelConfig.config_type == config_type)

    query = query.order_by(TenantModelConfig.config_type, TenantModelConfig.provider)

    result = await db.execute(query)
    configs = result.scalars().all()

    items = [
        ModelConfigResponse(
            id=c.id,
            tenant_id=c.tenant_id,
            config_type=c.config_type,
            provider=c.provider,
            model=c.model,
            base_url=c.base_url,
            is_active=c.is_active,
            created_at=c.created_at,
            updated_at=c.updated_at,
        )
        for c in configs
    ]

    return ModelConfigListResponse(items=items, total=len(items))


@router.get("/v1/model-configs/check", response_model=TenantModelConfigCheck)
async def check_model_configs(
    tenant: Tenant = Depends(get_tenant),
    _: APIKeyContext = Depends(get_current_api_key),
    db: AsyncSession = Depends(get_db_session),
):
    """
    检查租户的模型配置是否完整
    """
    query = select(TenantModelConfig).where(
        TenantModelConfig.tenant_id == tenant.id,
        TenantModelConfig.is_active == True,
    )

    result = await db.execute(query)
    configs = result.scalars().all()

    config_types = {c.config_type for c in configs}

    missing = []
    if "embedding" not in config_types:
        missing.append("embedding")
    if "llm" not in config_types:
        missing.append("llm")
    if "rerank" not in config_types:
        missing.append("rerank")

    return TenantModelConfigCheck(
        embedding_configured="embedding" in config_types,
        llm_configured="llm" in config_types,
        rerank_configured="rerank" in config_types,
        missing_configs=missing,
    )


@router.post("/v1/model-configs", response_model=ModelConfigResponseWithKey)
async def create_model_config(
    payload: ModelConfigCreate,
    tenant: Tenant = Depends(get_tenant),
    context: APIKeyContext = Depends(require_role("admin", "write")),
    db: AsyncSession = Depends(get_db_session),
):
    """
    创建模型配置

    - 每个租户每种配置类型（embedding/llm/rerank）只能有一个激活的配置
    - 如果已存在同类型的配置，会返回错误
    - 创建后立即返回 api_key，请妥善保管
    """
    # 检查是否已存在同类型的配置
    existing_query = select(TenantModelConfig).where(
        TenantModelConfig.tenant_id == tenant.id,
        TenantModelConfig.config_type == payload.config_type,
        TenantModelConfig.is_active == True,
    )
    existing_result = await db.execute(existing_query)
    existing = existing_result.scalar_one_or_none()

    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={
                "code": "CONFIG_EXISTS",
                "detail": f"已存在类型为 {payload.config_type} 的配置，请先删除或更新现有配置",
            },
        )

    # 创建新配置
    config = TenantModelConfig(
        tenant_id=tenant.id,
        config_type=payload.config_type,
        provider=payload.provider,
        model=payload.model,
        api_key=payload.api_key,  # 后续会加密存储
        base_url=payload.base_url,
        is_active=payload.is_active,
    )

    db.add(config)
    await db.commit()
    await db.refresh(config)

    logger.info(f"Created model config {config.id} for tenant {tenant.id}")

    return ModelConfigResponseWithKey(
        id=config.id,
        tenant_id=config.tenant_id,
        config_type=config.config_type,
        provider=config.provider,
        model=config.model,
        api_key=config.api_key,  # 返回明文，仅此一次
        base_url=config.base_url,
        is_active=config.is_active,
        created_at=config.created_at,
        updated_at=config.updated_at,
    )


@router.patch("/v1/model-configs/{config_id}", response_model=ModelConfigResponse)
async def update_model_config(
    payload: ModelConfigUpdate,
    config_id: str,
    tenant: Tenant = Depends(get_tenant),
    context: APIKeyContext = Depends(require_role("admin", "write")),
    db: AsyncSession = Depends(get_db_session),
):
    """
    更新模型配置

    - 只更新提供的字段
    - api_key 不会被返回（安全考虑）
    """
    query = select(TenantModelConfig).where(
        TenantModelConfig.id == config_id,
        TenantModelConfig.tenant_id == tenant.id,
    )

    result = await db.execute(query)
    config = result.scalar_one_or_none()

    if not config:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"code": "CONFIG_NOT_FOUND", "detail": "配置不存在"},
        )

    # 更新字段
    if payload.provider is not None:
        config.provider = payload.provider
    if payload.model is not None:
        config.model = payload.model
    if payload.api_key is not None:
        config.api_key = payload.api_key
    if payload.base_url is not None:
        config.base_url = payload.base_url
    if payload.is_active is not None:
        config.is_active = payload.is_active

    await db.commit()
    await db.refresh(config)

    logger.info(f"Updated model config {config_id}")

    return ModelConfigResponse(
        id=config.id,
        tenant_id=config.tenant_id,
        config_type=config.config_type,
        provider=config.provider,
        model=config.model,
        base_url=config.base_url,
        is_active=config.is_active,
        created_at=config.created_at,
        updated_at=config.updated_at,
    )


@router.delete("/v1/model-configs/{config_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_model_config(
    config_id: str,
    tenant: Tenant = Depends(get_tenant),
    context: APIKeyContext = Depends(require_role("admin", "write")),
    db: AsyncSession = Depends(get_db_session),
):
    """
    删除模型配置
    """
    query = select(TenantModelConfig).where(
        TenantModelConfig.id == config_id,
        TenantModelConfig.tenant_id == tenant.id,
    )

    result = await db.execute(query)
    config = result.scalar_one_or_none()

    if not config:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"code": "CONFIG_NOT_FOUND", "detail": "配置不存在"},
        )

    await db.delete(config)
    await db.commit()

    logger.info(f"Deleted model config {config_id}")


@router.delete("/v1/model-configs/by-type/{config_type}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_model_config_by_type(
    config_type: str,
    tenant: Tenant = Depends(get_tenant),
    context: APIKeyContext = Depends(require_role("admin", "write")),
    db: AsyncSession = Depends(get_db_session),
):
    """
    根据类型删除模型配置

    删除该租户下指定类型的所有配置
    """
    query = delete(TenantModelConfig).where(
        TenantModelConfig.tenant_id == tenant.id,
        TenantModelConfig.config_type == config_type,
    )

    await db.execute(query)
    await db.commit()

    logger.info(f"Deleted all model configs of type {config_type} for tenant {tenant.id}")