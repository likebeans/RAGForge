"""
对话管理路由

提供聊天历史的 CRUD 操作，用于前端对话持久化。

端点：
- POST   /v1/conversations              创建对话
- GET    /v1/conversations              对话列表
- GET    /v1/conversations/{id}         对话详情（含消息）
- PATCH  /v1/conversations/{id}         更新对话
- DELETE /v1/conversations/{id}         删除对话
- POST   /v1/conversations/{id}/messages 添加消息
"""

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.api.deps import get_current_api_key, get_db_session, get_tenant, APIKeyContext
from app.models import Conversation, Message
from app.models.tenant import Tenant
from app.schemas.conversation import (
    ConversationCreate,
    ConversationDetailResponse,
    ConversationListResponse,
    ConversationResponse,
    ConversationUpdate,
    MessageCreate,
    MessageResponse,
)

router = APIRouter(prefix="/v1/conversations", tags=["conversations"])


# ==================== 对话 CRUD ====================

@router.post("", response_model=ConversationResponse, status_code=status.HTTP_201_CREATED)
async def create_conversation(
    payload: ConversationCreate,
    tenant: Tenant = Depends(get_tenant),
    _: APIKeyContext = Depends(get_current_api_key),
    db: AsyncSession = Depends(get_db_session),
):
    """
    创建新对话
    
    可选指定标题和关联的知识库 ID 列表。
    """
    conversation = Conversation(
        tenant_id=tenant.id,
        title=payload.title,
        knowledge_base_ids=payload.knowledge_base_ids or [],
    )
    db.add(conversation)
    await db.commit()
    await db.refresh(conversation)
    
    return ConversationResponse(
        id=conversation.id,
        title=conversation.title,
        knowledge_base_ids=conversation.knowledge_base_ids,
        created_at=conversation.created_at,
        updated_at=conversation.updated_at,
        message_count=0,
    )


@router.get("", response_model=ConversationListResponse)
async def list_conversations(
    page: int = Query(1, ge=1, description="页码"),
    page_size: int = Query(20, ge=1, le=100, description="每页数量"),
    tenant: Tenant = Depends(get_tenant),
    _: APIKeyContext = Depends(get_current_api_key),
    db: AsyncSession = Depends(get_db_session),
):
    """
    获取对话列表
    
    按更新时间倒序排列，支持分页。
    """
    # 总数
    count_stmt = select(func.count()).select_from(Conversation).where(
        Conversation.tenant_id == tenant.id
    )
    total = (await db.execute(count_stmt)).scalar() or 0
    
    # 分页查询（带消息数量）
    offset = (page - 1) * page_size
    stmt = (
        select(Conversation)
        .where(Conversation.tenant_id == tenant.id)
        .order_by(Conversation.updated_at.desc())
        .offset(offset)
        .limit(page_size)
    )
    result = await db.execute(stmt)
    conversations = result.scalars().all()
    
    # 获取每个对话的消息数量
    items = []
    for conv in conversations:
        msg_count_stmt = select(func.count()).select_from(Message).where(
            Message.conversation_id == conv.id
        )
        msg_count = (await db.execute(msg_count_stmt)).scalar() or 0
        items.append(ConversationResponse(
            id=conv.id,
            title=conv.title,
            knowledge_base_ids=conv.knowledge_base_ids,
            created_at=conv.created_at,
            updated_at=conv.updated_at,
            message_count=msg_count,
        ))
    
    return ConversationListResponse(
        items=items,
        total=total,
        page=page,
        page_size=page_size,
    )


@router.get("/{conversation_id}", response_model=ConversationDetailResponse)
async def get_conversation(
    conversation_id: str,
    tenant: Tenant = Depends(get_tenant),
    _: APIKeyContext = Depends(get_current_api_key),
    db: AsyncSession = Depends(get_db_session),
):
    """
    获取对话详情
    
    返回对话信息和所有消息列表。
    """
    stmt = (
        select(Conversation)
        .options(selectinload(Conversation.messages))
        .where(
            Conversation.id == conversation_id,
            Conversation.tenant_id == tenant.id,
        )
    )
    result = await db.execute(stmt)
    conversation = result.scalar_one_or_none()
    
    if not conversation:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"code": "CONVERSATION_NOT_FOUND", "detail": "对话不存在"},
        )
    
    return ConversationDetailResponse(
        id=conversation.id,
        title=conversation.title,
        knowledge_base_ids=conversation.knowledge_base_ids,
        created_at=conversation.created_at,
        updated_at=conversation.updated_at,
        messages=[
            MessageResponse(
                id=msg.id,
                role=msg.role,
                content=msg.content,
                retriever=msg.retriever,
                sources=msg.sources,
                metadata=msg.extra_metadata,
                created_at=msg.created_at,
            )
            for msg in conversation.messages
        ],
    )


@router.patch("/{conversation_id}", response_model=ConversationResponse)
async def update_conversation(
    conversation_id: str,
    payload: ConversationUpdate,
    tenant: Tenant = Depends(get_tenant),
    _: APIKeyContext = Depends(get_current_api_key),
    db: AsyncSession = Depends(get_db_session),
):
    """
    更新对话
    
    可更新标题和关联的知识库 ID 列表。
    """
    stmt = select(Conversation).where(
        Conversation.id == conversation_id,
        Conversation.tenant_id == tenant.id,
    )
    result = await db.execute(stmt)
    conversation = result.scalar_one_or_none()
    
    if not conversation:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"code": "CONVERSATION_NOT_FOUND", "detail": "对话不存在"},
        )
    
    # 更新字段
    if payload.title is not None:
        conversation.title = payload.title
    if payload.knowledge_base_ids is not None:
        conversation.knowledge_base_ids = payload.knowledge_base_ids
    
    await db.commit()
    await db.refresh(conversation)
    
    # 获取消息数量
    msg_count_stmt = select(func.count()).select_from(Message).where(
        Message.conversation_id == conversation.id
    )
    msg_count = (await db.execute(msg_count_stmt)).scalar() or 0
    
    return ConversationResponse(
        id=conversation.id,
        title=conversation.title,
        knowledge_base_ids=conversation.knowledge_base_ids,
        created_at=conversation.created_at,
        updated_at=conversation.updated_at,
        message_count=msg_count,
    )


@router.delete("/{conversation_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_conversation(
    conversation_id: str,
    tenant: Tenant = Depends(get_tenant),
    _: APIKeyContext = Depends(get_current_api_key),
    db: AsyncSession = Depends(get_db_session),
):
    """
    删除对话
    
    同时删除所有关联的消息。
    """
    stmt = select(Conversation).where(
        Conversation.id == conversation_id,
        Conversation.tenant_id == tenant.id,
    )
    result = await db.execute(stmt)
    conversation = result.scalar_one_or_none()
    
    if not conversation:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"code": "CONVERSATION_NOT_FOUND", "detail": "对话不存在"},
        )
    
    await db.delete(conversation)
    await db.commit()


# ==================== 消息管理 ====================

@router.post(
    "/{conversation_id}/messages",
    response_model=MessageResponse,
    status_code=status.HTTP_201_CREATED,
)
async def add_message(
    conversation_id: str,
    payload: MessageCreate,
    tenant: Tenant = Depends(get_tenant),
    _: APIKeyContext = Depends(get_current_api_key),
    db: AsyncSession = Depends(get_db_session),
):
    """
    添加消息到对话
    
    支持添加用户消息或 AI 回复，AI 回复可包含引用来源。
    """
    # 验证对话存在
    stmt = select(Conversation).where(
        Conversation.id == conversation_id,
        Conversation.tenant_id == tenant.id,
    )
    result = await db.execute(stmt)
    conversation = result.scalar_one_or_none()
    
    if not conversation:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"code": "CONVERSATION_NOT_FOUND", "detail": "对话不存在"},
        )
    
    # 创建消息
    message = Message(
        conversation_id=conversation_id,
        role=payload.role,
        content=payload.content,
        retriever=payload.retriever,
        sources=[s.model_dump() for s in payload.sources] if payload.sources else None,
        extra_metadata=payload.metadata,
    )
    db.add(message)
    
    # 如果是第一条用户消息且对话没有标题，自动生成标题
    if payload.role == "user" and not conversation.title:
        # 取前 50 个字符作为标题
        conversation.title = payload.content[:50] + ("..." if len(payload.content) > 50 else "")
    
    await db.commit()
    await db.refresh(message)
    
    return MessageResponse(
        id=message.id,
        role=message.role,
        content=message.content,
        retriever=message.retriever,
        sources=message.sources,
        metadata=message.extra_metadata,
        created_at=message.created_at,
    )
