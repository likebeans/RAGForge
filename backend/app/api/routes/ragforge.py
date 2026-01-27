"""RAGForge 代理路由"""

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db
from app.services.ragforge_service import RagForgeService
from app.api.deps import get_current_user
from app.models import User

router = APIRouter()


class RetrieveRequest(BaseModel):
    """检索请求"""
    query: str
    knowledge_base_ids: list[str]
    top_k: int = 5


class RagRequest(BaseModel):
    """RAG 问答请求"""
    query: str
    knowledge_base_ids: list[str]
    top_k: int = 5
    stream: bool = False


@router.post("/retrieve")
async def retrieve(
    request: RetrieveRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """检索（自动注入用户权限）"""
    service = RagForgeService(db)
    
    try:
        api_key = await service.get_or_create_user_api_key(current_user)
        result = await service.retrieve(
            api_key=api_key,
            query=request.query,
            knowledge_base_ids=request.knowledge_base_ids,
            top_k=request.top_k
        )
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/rag")
async def rag(
    request: RagRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """RAG 问答（自动注入用户权限）"""
    service = RagForgeService(db)
    
    try:
        api_key = await service.get_or_create_user_api_key(current_user)
        result = await service.rag(
            api_key=api_key,
            request={
                "query": request.query,
                "knowledge_base_ids": request.knowledge_base_ids,
                "top_k": request.top_k,
                "stream": request.stream
            }
        )
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/rag/stream")
async def rag_stream(
    request: RagRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """流式 RAG 问答（自动注入用户权限）"""
    service = RagForgeService(db)
    
    try:
        api_key = await service.get_or_create_user_api_key(current_user)
        
        async def generate():
            async for chunk in service.rag_stream(
                api_key=api_key,
                query=request.query,
                knowledge_base_ids=request.knowledge_base_ids,
                top_k=request.top_k
            ):
                yield chunk
        
        return StreamingResponse(
            generate(),
            media_type="text/event-stream",
            headers={
                "Cache-Control": "no-cache",
                "Connection": "keep-alive",
                "X-Accel-Buffering": "no"
            }
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/knowledge-bases")
async def list_knowledge_bases(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """获取知识库列表"""
    service = RagForgeService(db)
    
    try:
        api_key = await service.get_or_create_user_api_key(current_user)
        result = await service.list_knowledge_bases(api_key)
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
