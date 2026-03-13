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
    retriever: str = "hybrid"  # dense / bm25 / hybrid / hyde / fusion


@router.post("/retrieve")
async def retrieve(
    request: RetrieveRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """检索（自动注入用户权限）"""
    service = RagForgeService(db)

    try:
        api_key = await service.get_or_create_user_api_key(current_user)
        result = await service.retrieve(
            api_key=api_key,
            query=request.query,
            knowledge_base_ids=request.knowledge_base_ids,
            top_k=request.top_k,
        )
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/rag")
async def rag(
    request: RagRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
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
                "stream": request.stream,
                "retriever": request.retriever,
            },
        )
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/rag/stream")
async def rag_stream(
    request: RagRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
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
                top_k=request.top_k,
            ):
                yield chunk

        return StreamingResponse(
            generate(),
            media_type="text/event-stream",
            headers={
                "Cache-Control": "no-cache",
                "Connection": "keep-alive",
                "X-Accel-Buffering": "no",
            },
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/knowledge-bases")
async def list_knowledge_bases(
    db: AsyncSession = Depends(get_db), current_user: User = Depends(get_current_user)
):
    """获取知识库列表"""
    service = RagForgeService(db)
    try:
        api_key = await service.get_or_create_user_api_key(current_user)
        result = await service.list_knowledge_bases(api_key)
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


class CreateKnowledgeBaseRequest(BaseModel):
    name: str
    description: Optional[str] = None


@router.post("/knowledge-bases")
async def create_knowledge_base(
    request: CreateKnowledgeBaseRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """创建知识库"""
    service = RagForgeService(db)
    try:
        api_key = await service.get_or_create_user_api_key(current_user)
        result = await service.create_knowledge_base(
            api_key, request.name, request.description or ""
        )
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/knowledge-bases/{kb_id}")
async def delete_knowledge_base(
    kb_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """删除知识库"""
    service = RagForgeService(db)
    try:
        api_key = await service.get_or_create_user_api_key(current_user)
        await service.delete_knowledge_base(api_key, kb_id)
        return {"message": "删除成功"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/knowledge-bases/{kb_id}/documents")
async def list_documents(
    kb_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """获取知识库文档列表"""
    service = RagForgeService(db)
    try:
        api_key = await service.get_or_create_user_api_key(current_user)
        result = await service.list_documents(api_key, kb_id)
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/knowledge-bases/{kb_id}/documents")
async def upload_document(
    kb_id: str,
    file: UploadFile = File(...),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """上传文档到知识库"""
    service = RagForgeService(db)
    try:
        api_key = await service.get_or_create_user_api_key(current_user)
        file_bytes = await file.read()
        result = await service.upload_document(
            api_key, kb_id, file.filename, file_bytes
        )
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/documents/{doc_id}")
async def delete_document(
    doc_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """删除文档"""
    service = RagForgeService(db)
    try:
        api_key = await service.get_or_create_user_api_key(current_user)
        await service.delete_document(api_key, doc_id)
        return {"message": "删除成功"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ==================== 提取模板 API ====================


@router.post("/extraction-schemas")
async def create_extraction_schema(
    file: UploadFile = File(...),
    name: str = Form(...),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """创建提取模板（上传 Excel 定义字段）"""
    service = RagForgeService(db)

    try:
        api_key = await service.get_or_create_user_api_key(current_user)
        file_bytes = await file.read()
        result = await service.create_extraction_schema(
            api_key=api_key, file_bytes=file_bytes, filename=file.filename, name=name
        )
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/extraction-schemas")
async def list_extraction_schemas(
    db: AsyncSession = Depends(get_db), current_user: User = Depends(get_current_user)
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
    current_user: User = Depends(get_current_user),
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
    current_user: User = Depends(get_current_user),
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
    current_user: User = Depends(get_current_user),
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
            output_format=output_format,
        )

        if output_format == "excel":
            return Response(
                content=result,
                media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                headers={
                    "Content-Disposition": "attachment; filename=extraction_result.xlsx"
                },
            )
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ==================== 保存并入库接口 ====================


@router.post("/extraction-schemas/save-and-ingest")
async def save_and_ingest_projects(
    kb_id: str = Form(default="71dd8415-8a4b-4543-b6f0-8f11e3b88176"),
    extracted_fields: str = Form(...),
    file: UploadFile = File(...),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    保存提取的项目并入库到向量库

    1. 解析 extracted_fields JSON
    2. 保存/更新到 yaoyan 数据库 (project_master 等表)
    3. 调用 ragforge 上传接口进行向量库入库
    """
    import json

    service = RagForgeService(db)

    try:
        api_key = await service.get_or_create_user_api_key(current_user)

        # 解析 extracted_fields
        try:
            fields_list = json.loads(extracted_fields)
        except json.JSONDecodeError as e:
            raise HTTPException(status_code=400, detail=f"Invalid JSON: {str(e)}")

        if not isinstance(fields_list, list):
            raise HTTPException(
                status_code=400, detail="extracted_fields must be an array"
            )

        # 读取 PDF 文件
        file_bytes = await file.read()

        result = await service.save_and_ingest_projects(
            api_key=api_key,
            kb_id=kb_id,
            extracted_fields=fields_list,
            pdf_file=(file.filename, file_bytes),
            db=db,
        )

        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ==================== Qwen-Plus 提取接口 ====================


@router.post("/extraction-schemas/extract/qwen-plus")
async def extract_with_qwen_plus(
    file: UploadFile = File(...),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    使用 Qwen-PLUS 模型提取 PDF 字段（无需模板）

    使用 ragforge 的 qwen-plus 接口进行提取。
    """
    import httpx

    service = RagForgeService(db)

    try:
        api_key = await service.get_or_create_user_api_key(current_user)
        file_bytes = await file.read()

        # 调用 ragforge 的 qwen-plus 接口
        async with httpx.AsyncClient(timeout=600.0) as client:
            response = await client.post(
                f"{service.base_url}/v1/extraction-schemas/extract/qwen-plus",
                headers={"Authorization": f"Bearer {api_key}"},
                files={"file": (file.filename, file_bytes, "application/pdf")},
            )
            response.raise_for_status()
            return response.json()
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
