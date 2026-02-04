"""RAGForge 代理路由"""

from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form
from fastapi.responses import StreamingResponse, Response
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Optional

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


# ==================== 提取模板 API ====================

@router.post("/extraction-schemas")
async def create_extraction_schema(
    file: UploadFile = File(...),
    name: str = Form(...),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """创建提取模板（上传 Excel 定义字段）"""
    service = RagForgeService(db)
    
    try:
        api_key = await service.get_or_create_user_api_key(current_user)
        file_bytes = await file.read()
        result = await service.create_extraction_schema(
            api_key=api_key,
            file_bytes=file_bytes,
            filename=file.filename,
            name=name
        )
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/extraction-schemas")
async def list_extraction_schemas(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """获取提取模板列表"""
    service = RagForgeService(db)
    
    try:
        api_key = await service.get_or_create_user_api_key(current_user)
        result = await service.list_extraction_schemas(api_key)
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/extraction-schemas/{schema_id}")
async def get_extraction_schema(
    schema_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """获取提取模板详情"""
    service = RagForgeService(db)
    
    try:
        api_key = await service.get_or_create_user_api_key(current_user)
        result = await service.get_extraction_schema(api_key, schema_id)
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/extraction-schemas/{schema_id}")
async def delete_extraction_schema(
    schema_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """删除提取模板"""
    service = RagForgeService(db)
    
    try:
        api_key = await service.get_or_create_user_api_key(current_user)
        await service.delete_extraction_schema(api_key, schema_id)
        return {"message": "删除成功"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/extraction-schemas/{schema_id}/extract")
async def extract_from_pdfs(
    schema_id: str,
    files: list[UploadFile] = File(...),
    output_format: str = Form(default="json"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """批量提取 PDF 字段"""
    service = RagForgeService(db)
    
    try:
        api_key = await service.get_or_create_user_api_key(current_user)
        
        # 读取所有文件
        file_list = []
        for f in files:
            content = await f.read()
            file_list.append((f.filename, content))
        
        result = await service.extract_from_pdfs(
            api_key=api_key,
            schema_id=schema_id,
            files=file_list,
            output_format=output_format
        )
        
        if output_format == "excel":
            return Response(
                content=result,
                media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                headers={"Content-Disposition": "attachment; filename=extraction_result.xlsx"}
            )
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
