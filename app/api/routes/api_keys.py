"""
API Key 管理接口

提供 API Key 的创建、列表、撤销、轮转等操作。
API Key 是服务间调用的认证凭证，类似 OpenAI 的 API Key。

安全说明：
- 创建时返回完整 Key，之后只能看到前缀
- 支持过期时间和独立限流配置
- 支持撤销和轮转（更换新 Key）
"""

from fastapi import APIRouter, Depends, HTTPException, Path, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_api_key, get_db_session, get_tenant
from app.auth.api_key import APIKeyContext, generate_api_key, hash_api_key
from app.config import get_settings
from app.models import APIKey
from app.schemas import APIKeyCreate, APIKeyInfo, APIKeySecret, APIKeyUpdate

router = APIRouter()
settings = get_settings()


@router.post("/v1/api-keys", response_model=APIKeySecret, status_code=status.HTTP_201_CREATED)
async def create_api_key(
    payload: APIKeyCreate,
    tenant=Depends(get_tenant),
    _: APIKeyContext = Depends(get_current_api_key),
    db: AsyncSession = Depends(get_db_session),
):
    """创建新的 API Key（仅此时返回完整 Key）"""
    display, hashed, prefix = generate_api_key(settings.api_key_prefix)

    api_key = APIKey(
        tenant_id=tenant.id,
        name=payload.name,
        prefix=prefix,
        hashed_key=hashed,
        expires_at=payload.expires_at,
        rate_limit_per_minute=payload.rate_limit_per_minute,
    )
    db.add(api_key)
    await db.commit()
    await db.refresh(api_key)

    return APIKeySecret(
        api_key=display,
        **APIKeyInfo.model_validate(api_key).model_dump(),
    )


@router.get("/v1/api-keys", response_model=list[APIKeyInfo])
async def list_api_keys(
    tenant=Depends(get_tenant),
    _: APIKeyContext = Depends(get_current_api_key),
    db: AsyncSession = Depends(get_db_session),
):
    result = await db.execute(
        select(APIKey).where(
            APIKey.tenant_id == tenant.id,
        )
    )
    keys = result.scalars().all()
    return keys


@router.post("/v1/api-keys/{key_id}/revoke", response_model=APIKeyInfo)
async def revoke_api_key(
    key_id: str = Path(...),
    tenant=Depends(get_tenant),
    _: APIKeyContext = Depends(get_current_api_key),
    db: AsyncSession = Depends(get_db_session),
):
    result = await db.execute(
        select(APIKey).where(
            APIKey.id == key_id,
            APIKey.tenant_id == tenant.id,
        )
    )
    api_key = result.scalar_one_or_none()
    if not api_key:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"code": "API_KEY_NOT_FOUND", "detail": "API key not found"},
        )

    api_key.revoked = True
    db.add(api_key)
    await db.commit()
    await db.refresh(api_key)
    return api_key


@router.post("/v1/api-keys/{key_id}/rotate", response_model=APIKeySecret)
async def rotate_api_key(
    key_id: str = Path(...),
    tenant=Depends(get_tenant),
    _: APIKeyContext = Depends(get_current_api_key),
    db: AsyncSession = Depends(get_db_session),
):
    result = await db.execute(
        select(APIKey).where(
            APIKey.id == key_id,
            APIKey.tenant_id == tenant.id,
        )
    )
    api_key = result.scalar_one_or_none()
    if not api_key:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"code": "API_KEY_NOT_FOUND", "detail": "API key not found"},
        )

    display, hashed, prefix = generate_api_key(settings.api_key_prefix)
    api_key.hashed_key = hashed
    api_key.prefix = prefix
    api_key.revoked = False

    db.add(api_key)
    await db.commit()
    await db.refresh(api_key)

    return APIKeySecret(
        api_key=display,
        **APIKeyInfo.model_validate(api_key).model_dump(),
    )


@router.patch("/v1/api-keys/{key_id}", response_model=APIKeyInfo)
async def update_api_key(
    payload: APIKeyUpdate,
    key_id: str = Path(...),
    tenant=Depends(get_tenant),
    _: APIKeyContext = Depends(get_current_api_key),
    db: AsyncSession = Depends(get_db_session),
):
    result = await db.execute(
        select(APIKey).where(
            APIKey.id == key_id,
            APIKey.tenant_id == tenant.id,
        )
    )
    api_key = result.scalar_one_or_none()
    if not api_key:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"code": "API_KEY_NOT_FOUND", "detail": "API key not found"},
        )

    if payload.name is not None:
        api_key.name = payload.name
    if payload.expires_at is not None:
        api_key.expires_at = payload.expires_at
    if payload.rate_limit_per_minute is not None:
        api_key.rate_limit_per_minute = payload.rate_limit_per_minute

    db.add(api_key)
    await db.commit()
    await db.refresh(api_key)
    return api_key


@router.delete("/v1/api-keys/{key_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_api_key(
    key_id: str = Path(...),
    tenant=Depends(get_tenant),
    _: APIKeyContext = Depends(get_current_api_key),
    db: AsyncSession = Depends(get_db_session),
):
    """删除 API Key"""
    result = await db.execute(
        select(APIKey).where(
            APIKey.id == key_id,
            APIKey.tenant_id == tenant.id,
        )
    )
    api_key = result.scalar_one_or_none()
    if not api_key:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"code": "API_KEY_NOT_FOUND", "detail": "API key not found"},
        )

    await db.delete(api_key)
    await db.commit()
