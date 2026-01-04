"""
管理员 API 路由

提供租户生命周期管理功能，需要 Admin Token 认证。
所有接口通过 X-Admin-Token 请求头认证。
"""

import json
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_db_session, verify_admin_token
from app.auth.api_key import generate_api_key
from app.config import get_settings
from app.models import APIKey, KnowledgeBase, SystemConfig, Tenant
from app.models.system_config import DEFAULT_SYSTEM_CONFIGS
from app.schemas.api_key import APIKeyCreate, APIKeyInfo, APIKeySecret
from app.schemas.system_config import (
    SystemConfigItem,
    SystemConfigListResponse,
    SystemConfigResetResponse,
    SystemConfigUpdate,
)
from app.schemas.tenant import (
    TenantCreate,
    TenantCreateResponse,
    TenantDisableRequest,
    TenantListResponse,
    TenantResponse,
    TenantUpdate,
)

router = APIRouter(
    prefix="/admin",
    tags=["admin"],
    dependencies=[Depends(verify_admin_token)],  # 所有接口需要管理员认证
)


def _err(code: str, detail: str) -> dict:
    """统一错误响应结构"""
    return {"code": code, "detail": detail}


# ==================== 租户管理 ====================

@router.post("/tenants", response_model=TenantCreateResponse, status_code=status.HTTP_201_CREATED)
async def create_tenant(
    data: TenantCreate,
    db: AsyncSession = Depends(get_db_session),
) -> TenantCreateResponse:
    """
    创建租户
    
    创建新租户并自动生成一个初始管理员 API Key。
    初始 API Key 仅在此响应中返回一次，请妥善保管。
    """
    # 检查名称唯一性
    existing = await db.execute(select(Tenant).where(Tenant.name == data.name))
    if existing.scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Tenant with name '{data.name}' already exists",
        )
    
    # 创建租户
    tenant = Tenant(
        name=data.name,
        plan=data.plan,
        quota_kb_count=data.quota_kb_count,
        quota_doc_count=data.quota_doc_count,
        quota_storage_mb=data.quota_storage_mb,
    )
    db.add(tenant)
    await db.flush()  # 获取 tenant.id
    
    # 创建初始管理员 API Key
    settings = get_settings()
    raw_key, hashed, prefix = generate_api_key(settings.api_key_prefix)
    
    api_key = APIKey(
        tenant_id=tenant.id,
        name="Initial Admin Key",
        prefix=prefix,
        hashed_key=hashed,
        role="admin",
        is_initial=True,
        description="Auto-generated admin key on tenant creation",
    )
    db.add(api_key)
    await db.commit()
    await db.refresh(tenant)
    
    return TenantCreateResponse(
        id=tenant.id,
        name=tenant.name,
        plan=tenant.plan,
        status=tenant.status,
        quota_kb_count=tenant.quota_kb_count,
        quota_doc_count=tenant.quota_doc_count,
        quota_storage_mb=tenant.quota_storage_mb,
        created_at=tenant.created_at,
        updated_at=tenant.updated_at,
        initial_api_key=raw_key,
    )


@router.get("/tenants", response_model=TenantListResponse)
async def list_tenants(
    skip: int = Query(0, ge=0),
    limit: int = Query(20, ge=1, le=100),
    status_filter: str | None = Query(None, alias="status"),
    db: AsyncSession = Depends(get_db_session),
) -> TenantListResponse:
    """
    列出所有租户
    
    支持分页和状态过滤。
    """
    query = select(Tenant)
    count_query = select(func.count(Tenant.id))
    
    if status_filter:
        query = query.where(Tenant.status == status_filter)
        count_query = count_query.where(Tenant.status == status_filter)
    
    # 总数
    total = (await db.execute(count_query)).scalar() or 0
    
    # 分页查询
    query = query.order_by(Tenant.created_at.desc()).offset(skip).limit(limit)
    result = await db.execute(query)
    tenants = result.scalars().all()
    
    return TenantListResponse(
        items=[TenantResponse.model_validate(t) for t in tenants],
        total=total,
        skip=skip,
        limit=limit,
    )


@router.get("/tenants/{tenant_id}", response_model=TenantResponse)
async def get_tenant(
    tenant_id: str,
    db: AsyncSession = Depends(get_db_session),
) -> TenantResponse:
    """获取租户详情"""
    tenant = await db.get(Tenant, tenant_id)
    if not tenant:
        raise HTTPException(status_code=404, detail=_err("TENANT_NOT_FOUND", "Tenant not found"))
    
    # 统计 KB 和文档数
    kb_count = (await db.execute(
        select(func.count(KnowledgeBase.id)).where(KnowledgeBase.tenant_id == tenant_id)
    )).scalar() or 0
    
    response = TenantResponse.model_validate(tenant)
    response.kb_count = kb_count
    return response


@router.patch("/tenants/{tenant_id}", response_model=TenantResponse)
async def update_tenant(
    tenant_id: str,
    data: TenantUpdate,
    db: AsyncSession = Depends(get_db_session),
) -> TenantResponse:
    """更新租户信息"""
    tenant = await db.get(Tenant, tenant_id)
    if not tenant:
        raise HTTPException(status_code=404, detail=_err("TENANT_NOT_FOUND", "Tenant not found"))
    
    # 检查名称唯一性（如果要更新名称）
    if data.name and data.name != tenant.name:
        existing = await db.execute(select(Tenant).where(Tenant.name == data.name))
        if existing.scalar_one_or_none():
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=_err("TENANT_NAME_EXISTS", f"Tenant with name '{data.name}' already exists"),
            )
    
    # 更新字段
    update_data = data.model_dump(exclude_unset=True)
    for key, value in update_data.items():
        setattr(tenant, key, value)
    
    await db.commit()
    await db.refresh(tenant)
    return TenantResponse.model_validate(tenant)


@router.post("/tenants/{tenant_id}/disable", response_model=TenantResponse)
async def disable_tenant(
    tenant_id: str,
    data: TenantDisableRequest | None = None,
    db: AsyncSession = Depends(get_db_session),
) -> TenantResponse:
    """
    禁用租户
    
    禁用后，该租户的所有 API Key 将无法访问 API。
    """
    tenant = await db.get(Tenant, tenant_id)
    if not tenant:
        raise HTTPException(status_code=404, detail=_err("TENANT_NOT_FOUND", "Tenant not found"))
    
    if tenant.status == "disabled":
        raise HTTPException(status_code=400, detail=_err("TENANT_ALREADY_DISABLED", "Tenant is already disabled"))
    
    tenant.status = "disabled"
    tenant.disabled_at = datetime.now(timezone.utc)
    tenant.disabled_reason = data.reason if data else None
    
    await db.commit()
    await db.refresh(tenant)
    return TenantResponse.model_validate(tenant)


@router.post("/tenants/{tenant_id}/enable", response_model=TenantResponse)
async def enable_tenant(
    tenant_id: str,
    db: AsyncSession = Depends(get_db_session),
) -> TenantResponse:
    """启用租户"""
    tenant = await db.get(Tenant, tenant_id)
    if not tenant:
        raise HTTPException(status_code=404, detail=_err("TENANT_NOT_FOUND", "Tenant not found"))
    
    if tenant.status == "active":
        raise HTTPException(status_code=400, detail=_err("TENANT_ALREADY_ACTIVE", "Tenant is already active"))
    
    tenant.status = "active"
    tenant.disabled_at = None
    tenant.disabled_reason = None
    
    await db.commit()
    await db.refresh(tenant)
    return TenantResponse.model_validate(tenant)


@router.delete("/tenants/{tenant_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_tenant(
    tenant_id: str,
    db: AsyncSession = Depends(get_db_session),
) -> None:
    """
    删除租户
    
    警告：此操作将级联删除租户的所有数据（API Key、知识库、文档等）。
    """
    tenant = await db.get(Tenant, tenant_id)
    if not tenant:
        raise HTTPException(status_code=404, detail=_err("TENANT_NOT_FOUND", "Tenant not found"))
    
    await db.delete(tenant)
    await db.commit()


# ==================== 租户 API Key 管理 ====================

@router.get("/tenants/{tenant_id}/api-keys", response_model=list[APIKeyInfo])
async def list_tenant_api_keys(
    tenant_id: str,
    db: AsyncSession = Depends(get_db_session),
) -> list[APIKeyInfo]:
    """列出租户的所有 API Key"""
    tenant = await db.get(Tenant, tenant_id)
    if not tenant:
        raise HTTPException(status_code=404, detail=_err("TENANT_NOT_FOUND", "Tenant not found"))
    
    result = await db.execute(
        select(APIKey)
        .where(APIKey.tenant_id == tenant_id)
        .order_by(APIKey.created_at.desc())
    )
    keys = result.scalars().all()
    return [APIKeyInfo.model_validate(k) for k in keys]


@router.post("/tenants/{tenant_id}/api-keys", response_model=APIKeySecret, status_code=status.HTTP_201_CREATED)
async def create_tenant_api_key(
    tenant_id: str,
    data: APIKeyCreate,
    db: AsyncSession = Depends(get_db_session),
) -> APIKeySecret:
    """为租户创建新的 API Key"""
    tenant = await db.get(Tenant, tenant_id)
    if not tenant:
        raise HTTPException(status_code=404, detail=_err("TENANT_NOT_FOUND", "Tenant not found"))
    
    settings = get_settings()
    raw_key, hashed, prefix = generate_api_key(settings.api_key_prefix)
    
    api_key = APIKey(
        tenant_id=tenant_id,
        name=data.name,
        prefix=prefix,
        hashed_key=hashed,
        role=data.role,
        expires_at=data.expires_at,
        rate_limit_per_minute=data.rate_limit_per_minute,
        scope_kb_ids=data.scope_kb_ids,
        description=data.description,
        identity=data.identity,
    )
    db.add(api_key)
    await db.commit()
    await db.refresh(api_key)
    
    return APIKeySecret(
        id=api_key.id,
        name=api_key.name,
        prefix=api_key.prefix,
        role=api_key.role,
        revoked=api_key.revoked,
        expires_at=api_key.expires_at,
        last_used_at=api_key.last_used_at,
        created_at=api_key.created_at,
        is_initial=api_key.is_initial,
        scope_kb_ids=api_key.scope_kb_ids,
        description=api_key.description,
        identity=api_key.identity,
        api_key=raw_key,
    )


@router.delete("/tenants/{tenant_id}/api-keys/{key_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_tenant_api_key(
    tenant_id: str,
    key_id: str,
    db: AsyncSession = Depends(get_db_session),
) -> None:
    """删除租户的 API Key"""
    api_key = await db.get(APIKey, key_id)
    if not api_key or api_key.tenant_id != tenant_id:
        raise HTTPException(status_code=404, detail=_err("API_KEY_NOT_FOUND", "API Key not found"))
    
    await db.delete(api_key)
    await db.commit()


# ==================== 系统配置管理 ====================

def _parse_config_value(value: str) -> any:
    """解析配置值，尝试 JSON 解码"""
    try:
        return json.loads(value)
    except (json.JSONDecodeError, TypeError):
        return value


@router.get("/system-config", response_model=SystemConfigListResponse)
async def list_system_configs(
    db: AsyncSession = Depends(get_db_session),
) -> SystemConfigListResponse:
    """
    获取所有系统配置
    
    返回数据库中的所有系统配置项。
    如果配置项未设置，将从环境变量获取默认值。
    """
    result = await db.execute(select(SystemConfig))
    configs = result.scalars().all()
    
    items = [
        SystemConfigItem(
            key=c.key,
            value=_parse_config_value(c.value),
            description=c.description,
            updated_at=c.updated_at,
        )
        for c in configs
    ]
    
    return SystemConfigListResponse(items=items, total=len(items))


@router.get("/system-config/{key}", response_model=SystemConfigItem)
async def get_system_config(
    key: str,
    db: AsyncSession = Depends(get_db_session),
) -> SystemConfigItem:
    """
    获取单个系统配置
    
    如果配置项不存在，返回 404。
    """
    config = await db.get(SystemConfig, key)
    if not config:
        raise HTTPException(
            status_code=404,
            detail=_err("CONFIG_NOT_FOUND", f"System config '{key}' not found"),
        )
    
    return SystemConfigItem(
        key=config.key,
        value=_parse_config_value(config.value),
        description=config.description,
        updated_at=config.updated_at,
    )


@router.put("/system-config/{key}", response_model=SystemConfigItem)
async def update_system_config(
    key: str,
    data: SystemConfigUpdate,
    db: AsyncSession = Depends(get_db_session),
) -> SystemConfigItem:
    """
    更新系统配置（立即生效，无需重启）
    
    如果配置项不存在，则创建新配置。
    配置值将被 JSON 序列化存储。
    """
    # 验证配置键是否有效
    if key not in DEFAULT_SYSTEM_CONFIGS:
        raise HTTPException(
            status_code=400,
            detail=_err("CONFIG_KEY_INVALID", f"Unknown config key: {key}. Valid keys: {list(DEFAULT_SYSTEM_CONFIGS.keys())}"),
        )
    
    # 序列化值
    value_str = json.dumps(data.value) if not isinstance(data.value, str) else json.dumps(data.value)
    
    # 获取描述
    description = data.description
    if description is None:
        description = DEFAULT_SYSTEM_CONFIGS[key].get("description")
    
    config = await db.get(SystemConfig, key)
    if config:
        # 更新现有配置
        config.value = value_str
        config.description = description
    else:
        # 创建新配置
        config = SystemConfig(
            key=key,
            value=value_str,
            description=description,
        )
        db.add(config)
    
    await db.commit()
    await db.refresh(config)
    
    return SystemConfigItem(
        key=config.key,
        value=_parse_config_value(config.value),
        description=config.description,
        updated_at=config.updated_at,
    )


@router.post("/system-config/reset", response_model=SystemConfigResetResponse)
async def reset_system_configs(
    db: AsyncSession = Depends(get_db_session),
) -> SystemConfigResetResponse:
    """
    重置所有系统配置为环境变量默认值
    
    删除数据库中的所有系统配置项，使系统回退到使用环境变量。
    """
    result = await db.execute(select(SystemConfig))
    configs = result.scalars().all()
    
    reset_keys = [c.key for c in configs]
    
    for config in configs:
        await db.delete(config)
    
    await db.commit()
    
    return SystemConfigResetResponse(
        message="All system configs have been reset to environment variable defaults",
        reset_keys=reset_keys,
    )
