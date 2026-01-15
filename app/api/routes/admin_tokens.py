"""
管理员 Token 管理接口

提供管理员 Token 的 CRUD 操作，需要 Admin Token 认证。
"""

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_db_session, verify_admin_token
from app.auth.admin_token import generate_admin_token
from app.models import AdminToken
from app.schemas.admin_token import (
    AdminTokenCreate,
    AdminTokenCreateResponse,
    AdminTokenListResponse,
    AdminTokenResponse,
)

router = APIRouter(
    prefix="/admin/tokens",
    tags=["admin"],
    dependencies=[Depends(verify_admin_token)],
)


@router.post("", response_model=AdminTokenCreateResponse, status_code=status.HTTP_201_CREATED)
async def create_admin_token(
    data: AdminTokenCreate,
    db: AsyncSession = Depends(get_db_session),
) -> AdminTokenCreateResponse:
    """
    创建管理员 Token
    
    生成新的管理员 Token，返回的明文 Token 仅显示一次，请妥善保管。
    """
    # 生成 Token
    raw_token, hashed, prefix = generate_admin_token()
    
    # 创建记录
    token = AdminToken(
        name=data.name,
        prefix=prefix,
        hashed_token=hashed,
        expires_at=data.expires_at,
        description=data.description,
        created_by=data.created_by,
    )
    db.add(token)
    await db.commit()
    await db.refresh(token)
    
    return AdminTokenCreateResponse(
        id=token.id,
        name=token.name,
        prefix=token.prefix,
        expires_at=token.expires_at,
        description=token.description,
        created_at=token.created_at,
        token=raw_token,  # 明文 Token 仅返回一次
    )


@router.get("", response_model=AdminTokenListResponse)
async def list_admin_tokens(
    skip: int = Query(0, ge=0),
    limit: int = Query(20, ge=1, le=100),
    show_revoked: bool = Query(False, description="是否显示已撤销的 Token"),
    db: AsyncSession = Depends(get_db_session),
) -> AdminTokenListResponse:
    """列出所有管理员 Token"""
    query = select(AdminToken)
    count_query = select(func.count(AdminToken.id))
    
    if not show_revoked:
        query = query.where(AdminToken.revoked.is_(False))
        count_query = count_query.where(AdminToken.revoked.is_(False))
    
    # 总数
    total = (await db.execute(count_query)).scalar() or 0
    
    # 分页查询
    query = query.order_by(AdminToken.created_at.desc()).offset(skip).limit(limit)
    result = await db.execute(query)
    tokens = result.scalars().all()
    
    return AdminTokenListResponse(
        items=[AdminTokenResponse.model_validate(t) for t in tokens],
        total=total,
        skip=skip,
        limit=limit,
    )


@router.get("/{token_id}", response_model=AdminTokenResponse)
async def get_admin_token(
    token_id: str,
    db: AsyncSession = Depends(get_db_session),
) -> AdminTokenResponse:
    """获取管理员 Token 详情"""
    token = await db.get(AdminToken, token_id)
    if not token:
        raise HTTPException(
            status_code=404,
            detail={"code": "ADMIN_TOKEN_NOT_FOUND", "detail": "Admin token not found"},
        )
    
    return AdminTokenResponse.model_validate(token)


@router.post("/{token_id}/revoke", response_model=AdminTokenResponse)
async def revoke_admin_token(
    token_id: str,
    db: AsyncSession = Depends(get_db_session),
) -> AdminTokenResponse:
    """撤销管理员 Token"""
    token = await db.get(AdminToken, token_id)
    if not token:
        raise HTTPException(
            status_code=404,
            detail={"code": "ADMIN_TOKEN_NOT_FOUND", "detail": "Admin token not found"},
        )
    
    token.revoked = True
    await db.commit()
    await db.refresh(token)
    
    return AdminTokenResponse.model_validate(token)


@router.delete("/{token_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_admin_token(
    token_id: str,
    db: AsyncSession = Depends(get_db_session),
):
    """删除管理员 Token"""
    token = await db.get(AdminToken, token_id)
    if not token:
        raise HTTPException(
            status_code=404,
            detail={"code": "ADMIN_TOKEN_NOT_FOUND", "detail": "Admin token not found"},
        )
    
    await db.delete(token)
    await db.commit()
