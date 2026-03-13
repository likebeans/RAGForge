"""RAGForge 集成服务"""

import httpx
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import get_settings
from app.models import User, APIKeyMapping
from app.auth.encryption import encrypt_api_key, decrypt_api_key

settings = get_settings()


class RagForgeService:
    """RAGForge 集成服务"""
    
    def __init__(self, db: AsyncSession):
        self.db = db
        self.base_url = settings.ragforge_base_url
        self.admin_key = settings.ragforge_admin_key
    
    async def get_or_create_user_api_key(self, user: User) -> str:
        """获取或创建用户的 RAGForge API Key"""
        result = await self.db.execute(
            select(APIKeyMapping).where(
                APIKeyMapping.user_id == user.id,
                APIKeyMapping.is_valid == True
            )
        )
        mapping = result.scalar_one_or_none()

        if mapping:
            current_identity = self._build_identity(user)
            if mapping.identity_snapshot == current_identity:
                try:
                    api_key = decrypt_api_key(mapping.ragforge_api_key)
                    # 快速验证 key 是否仍有效
                    await self._verify_api_key(api_key)
                    return api_key
                except Exception:
                    # 解密失败或 key 已失效 → 作废并重建
                    mapping.is_valid = False
                    await self.db.commit()
            else:
                mapping.is_valid = False
                await self.db.commit()

        return await self._create_api_key(user)

    async def _verify_api_key(self, api_key: str) -> None:
        """向 RAGForge 发起轻量探测，验证 key 是否仍有效（失败则抛异常）"""
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.get(
                f"{self.base_url}/v1/knowledge-bases?page=1&page_size=1",
                headers={"Authorization": f"Bearer {api_key}"},
            )
            if response.status_code in (401, 403):
                raise ValueError("RAGForge API key is no longer valid")
    
    async def _create_api_key(self, user: User) -> str:
        """为用户创建 RAGForge API Key"""
        identity = self._build_identity(user)
        
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(
                f"{self.base_url}/v1/api-keys",
                headers={"Authorization": f"Bearer {self.admin_key}"},
                json={
                    "name": f"yaoyan-{user.username}",
                    "role": "admin" if user.is_admin else "read",
                    "identity": identity
                }
            )
            response.raise_for_status()
            data = response.json()
        
        # 加密存储 API Key
        encrypted_key = encrypt_api_key(data["api_key"])
        
        mapping = APIKeyMapping(
            user_id=user.id,
            ragforge_key_id=data["id"],
            ragforge_api_key=encrypted_key,
            identity_snapshot=identity,
            is_valid=True
        )
        self.db.add(mapping)
        await self.db.commit()
        
        return data["api_key"]
    
    def _build_identity(self, user: User) -> dict:
        """构建用户 identity"""
        return {
            "user_id": user.id,
            "roles": [r.name for r in user.roles],
            "groups": [g.name for g in user.groups],
            "clearance": user.clearance
        }
    
    async def retrieve(self, api_key: str, query: str, knowledge_base_ids: list[str], top_k: int = 5) -> dict:
        """检索"""
        async with httpx.AsyncClient(timeout=60.0) as client:
            response = await client.post(
                f"{self.base_url}/v1/retrieve",
                headers={"Authorization": f"Bearer {api_key}"},
                json={
                    "query": query,
                    "knowledge_base_ids": knowledge_base_ids,
                    "top_k": top_k
                }
            )
            response.raise_for_status()
            return response.json()
    
    async def rag(self, api_key: str, request: dict) -> dict:
        """RAG 问答"""
        async with httpx.AsyncClient(timeout=120.0) as client:
            response = await client.post(
                f"{self.base_url}/v1/rag",
                headers={"Authorization": f"Bearer {api_key}"},
                json=request
            )
            response.raise_for_status()
            return response.json()
    
    async def list_knowledge_bases(self, api_key: str) -> dict:
        """获取知识库列表"""
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.get(
                f"{self.base_url}/v1/knowledge-bases",
                headers={"Authorization": f"Bearer {api_key}"}
            )
            response.raise_for_status()
            return response.json()

    async def create_knowledge_base(self, api_key: str, name: str, description: str = "") -> dict:
        """创建知识库"""
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(
                f"{self.base_url}/v1/knowledge-bases",
                headers={"Authorization": f"Bearer {api_key}"},
                json={"name": name, "description": description}
            )
            response.raise_for_status()
            return response.json()

    async def delete_knowledge_base(self, api_key: str, kb_id: str) -> None:
        """删除知识库"""
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.delete(
                f"{self.base_url}/v1/knowledge-bases/{kb_id}",
                headers={"Authorization": f"Bearer {api_key}"}
            )
            response.raise_for_status()

    async def list_documents(self, api_key: str, kb_id: str) -> dict:
        """获取知识库文档列表"""
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.get(
                f"{self.base_url}/v1/knowledge-bases/{kb_id}/documents",
                headers={"Authorization": f"Bearer {api_key}"}
            )
            response.raise_for_status()
            return response.json()

    async def upload_document(self, api_key: str, kb_id: str, filename: str, file_bytes: bytes) -> dict:
        """上传文档到知识库"""
        async with httpx.AsyncClient(timeout=120.0) as client:
            response = await client.post(
                f"{self.base_url}/v1/knowledge-bases/{kb_id}/documents",
                headers={"Authorization": f"Bearer {api_key}"},
                files={"file": (filename, file_bytes)}
            )
            response.raise_for_status()
            return response.json()

    async def delete_document(self, api_key: str, doc_id: str) -> None:
        """删除文档"""
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.delete(
                f"{self.base_url}/v1/documents/{doc_id}",
                headers={"Authorization": f"Bearer {api_key}"}
            )
            response.raise_for_status()


    async def rag_stream(self, api_key: str, query: str, knowledge_base_ids: list[str], top_k: int = 5):
        """流式 RAG 问答"""
        async with httpx.AsyncClient(timeout=300.0) as client:
            async with client.stream(
                "POST",
                f"{self.base_url}/v1/rag/stream",
                headers={"Authorization": f"Bearer {api_key}"},
                json={
                    "query": query,
                    "knowledge_base_ids": knowledge_base_ids,
                    "top_k": top_k
                }
            ) as response:
                response.raise_for_status()
                async for line in response.aiter_lines():
                    if line:
                        yield line + "\n"

    # ==================== 提取模板 API ====================
    
    async def create_extraction_schema(self, api_key: str, file_bytes: bytes, filename: str, name: str) -> dict:
        """创建提取模板（上传 Excel 定义字段）"""
        async with httpx.AsyncClient(timeout=60.0) as client:
            response = await client.post(
                f"{self.base_url}/v1/extraction-schemas",
                headers={"Authorization": f"Bearer {api_key}"},
                files={"file": (filename, file_bytes, "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")},
                data={"name": name}
            )
            response.raise_for_status()
            return response.json()
    
    async def list_extraction_schemas(self, api_key: str) -> dict:
        """获取提取模板列表"""
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.get(
                f"{self.base_url}/v1/extraction-schemas",
                headers={"Authorization": f"Bearer {api_key}"}
            )
            response.raise_for_status()
            return response.json()
    
    async def get_extraction_schema(self, api_key: str, schema_id: str) -> dict:
        """获取提取模板详情"""
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.get(
                f"{self.base_url}/v1/extraction-schemas/{schema_id}",
                headers={"Authorization": f"Bearer {api_key}"}
            )
            response.raise_for_status()
            return response.json()
    
    async def delete_extraction_schema(self, api_key: str, schema_id: str) -> None:
        """删除提取模板"""
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.delete(
                f"{self.base_url}/v1/extraction-schemas/{schema_id}",
                headers={"Authorization": f"Bearer {api_key}"}
            )
            response.raise_for_status()
    
    async def extract_from_pdfs(self, api_key: str, schema_id: str, files: list[tuple], output_format: str = "json") -> dict | bytes:
        """
        批量提取 PDF 字段
        
        Args:
            api_key: API Key
            schema_id: 提取模板 ID
            files: 文件列表 [(filename, file_bytes), ...]
            output_format: 输出格式 "json" 或 "excel"
        
        Returns:
            JSON 结果或 Excel 文件字节
        """
        async with httpx.AsyncClient(timeout=600.0) as client:
            # 构建 multipart 文件列表
            files_data = [("files", (fname, fbytes, "application/pdf")) for fname, fbytes in files]
            
            response = await client.post(
                f"{self.base_url}/v1/extraction-schemas/{schema_id}/extract",
                headers={"Authorization": f"Bearer {api_key}"},
                files=files_data,
                data={"output_format": output_format}
            )
            response.raise_for_status()
            
            if output_format == "excel":
                return response.content
            return response.json()
