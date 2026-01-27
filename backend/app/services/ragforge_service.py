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
                # 解密存储的 API Key
                return decrypt_api_key(mapping.ragforge_api_key)
            else:
                mapping.is_valid = False
                await self.db.commit()
        
        return await self._create_api_key(user)
    
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
