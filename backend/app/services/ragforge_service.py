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
                APIKeyMapping.user_id == user.id, APIKeyMapping.is_valid == True
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
                    "identity": identity,
                },
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
            is_valid=True,
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
            "clearance": user.clearance,
        }

    async def retrieve(
        self, api_key: str, query: str, knowledge_base_ids: list[str], top_k: int = 5
    ) -> dict:
        """检索"""
        async with httpx.AsyncClient(timeout=60.0) as client:
            response = await client.post(
                f"{self.base_url}/v1/retrieve",
                headers={"Authorization": f"Bearer {api_key}"},
                json={
                    "query": query,
                    "knowledge_base_ids": knowledge_base_ids,
                    "top_k": top_k,
                },
            )
            response.raise_for_status()
            return response.json()

    async def rag(self, api_key: str, request: dict) -> dict:
        """RAG 问答"""
        async with httpx.AsyncClient(timeout=120.0) as client:
            response = await client.post(
                f"{self.base_url}/v1/rag",
                headers={"Authorization": f"Bearer {api_key}"},
                json=request,
            )
            response.raise_for_status()
            return response.json()

    async def list_knowledge_bases(self, api_key: str) -> dict:
        """获取知识库列表"""
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.get(
                f"{self.base_url}/v1/knowledge-bases",
                headers={"Authorization": f"Bearer {api_key}"},
            )
            response.raise_for_status()
            return response.json()

    async def create_knowledge_base(
        self, api_key: str, name: str, description: str = ""
    ) -> dict:
        """创建知识库"""
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(
                f"{self.base_url}/v1/knowledge-bases",
                headers={"Authorization": f"Bearer {api_key}"},
                json={"name": name, "description": description},
            )
            response.raise_for_status()
            return response.json()

    async def delete_knowledge_base(self, api_key: str, kb_id: str) -> None:
        """删除知识库"""
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.delete(
                f"{self.base_url}/v1/knowledge-bases/{kb_id}",
                headers={"Authorization": f"Bearer {api_key}"},
            )
            response.raise_for_status()

    async def list_documents(self, api_key: str, kb_id: str) -> dict:
        """获取知识库文档列表"""
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.get(
                f"{self.base_url}/v1/knowledge-bases/{kb_id}/documents",
                headers={"Authorization": f"Bearer {api_key}"},
            )
            response.raise_for_status()
            return response.json()

    async def upload_document(
        self, api_key: str, kb_id: str, filename: str, file_bytes: bytes
    ) -> dict:
        """上传文档到知识库"""
        async with httpx.AsyncClient(timeout=120.0) as client:
            response = await client.post(
                f"{self.base_url}/v1/knowledge-bases/{kb_id}/documents",
                headers={"Authorization": f"Bearer {api_key}"},
                files={"file": (filename, file_bytes)},
            )
            response.raise_for_status()
            return response.json()

    async def delete_document(self, api_key: str, doc_id: str) -> None:
        """删除文档"""
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.delete(
                f"{self.base_url}/v1/documents/{doc_id}",
                headers={"Authorization": f"Bearer {api_key}"},
            )
            response.raise_for_status()

    async def rag_stream(
        self, api_key: str, query: str, knowledge_base_ids: list[str], top_k: int = 5
    ):
        """流式 RAG 问答"""
        async with httpx.AsyncClient(timeout=300.0) as client:
            async with client.stream(
                "POST",
                f"{self.base_url}/v1/rag/stream",
                headers={"Authorization": f"Bearer {api_key}"},
                json={
                    "query": query,
                    "knowledge_base_ids": knowledge_base_ids,
                    "top_k": top_k,
                },
            ) as response:
                response.raise_for_status()
                async for line in response.aiter_lines():
                    if line:
                        yield line + "\n"

    # ==================== 提取模板 API ====================

    async def create_extraction_schema(
        self, api_key: str, file_bytes: bytes, filename: str, name: str
    ) -> dict:
        """创建提取模板（上传 Excel 定义字段）"""
        async with httpx.AsyncClient(timeout=60.0) as client:
            response = await client.post(
                f"{self.base_url}/v1/extraction-schemas",
                headers={"Authorization": f"Bearer {api_key}"},
                files={
                    "file": (
                        filename,
                        file_bytes,
                        "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                    )
                },
                data={"name": name},
            )
            response.raise_for_status()
            return response.json()

    async def list_extraction_schemas(self, api_key: str) -> dict:
        """获取提取模板列表"""
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.get(
                f"{self.base_url}/v1/extraction-schemas",
                headers={"Authorization": f"Bearer {api_key}"},
            )
            response.raise_for_status()
            return response.json()

    async def get_extraction_schema(self, api_key: str, schema_id: str) -> dict:
        """获取提取模板详情"""
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.get(
                f"{self.base_url}/v1/extraction-schemas/{schema_id}",
                headers={"Authorization": f"Bearer {api_key}"},
            )
            response.raise_for_status()
            return response.json()

    async def delete_extraction_schema(self, api_key: str, schema_id: str) -> None:
        """删除提取模板"""
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.delete(
                f"{self.base_url}/v1/extraction-schemas/{schema_id}",
                headers={"Authorization": f"Bearer {api_key}"},
            )
            response.raise_for_status()

    async def extract_from_pdfs(
        self,
        api_key: str,
        schema_id: str,
        files: list[tuple],
        output_format: str = "json",
    ) -> dict | bytes:
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
            files_data = [
                ("files", (fname, fbytes, "application/pdf")) for fname, fbytes in files
            ]

            response = await client.post(
                f"{self.base_url}/v1/extraction-schemas/{schema_id}/extract",
                headers={"Authorization": f"Bearer {api_key}"},
                files=files_data,
                data={"output_format": output_format},
            )
            response.raise_for_status()

            if output_format == "excel":
                return response.content
            return response.json()

    async def save_and_ingest_projects(
        self,
        api_key: str,
        kb_id: str,
        extracted_fields: list[dict],
        pdf_file: tuple[str, bytes],
        db: "AsyncSession",
    ) -> dict:
        """
        保存项目到 yaoyan 数据库并调用 ragforge 上传接口

        Args:
            api_key: RAGForge API Key
            kb_id: 知识库 ID
            extracted_fields: 提取的字段数组（30个字段）
            pdf_file: (filename, file_bytes)
            db: yaoyan 数据库会话

        Returns:
            保存结果
        """
        import json
        from sqlalchemy import select
        from app.models.project import (
            ProjectMaster,
            ProjectDetail,
            ProjectManagementInfo,
        )
        from app.services.project_service import ProjectService

        saved_projects = []
        project_service = ProjectService(db)

        # 字段映射：extracted_fields -> ProjectCreate
        phase_map = {
            "临床前": "PRE_CLINICAL",
            "临床一期": "PHASE_I",
            "临床二期": "PHASE_II",
            "临床三期": "PHASE_III",
            "NDA": "NDA",
            "已上市": "APPROVED",
        }

        for fields in extracted_fields:
            project_name = fields.get("项目", "")
            if not project_name or project_name == "未提及":
                continue

            # 检查项目是否已存在
            result = await db.execute(
                select(ProjectMaster).where(
                    ProjectMaster.project_name == project_name,
                    ProjectMaster.is_deleted == False,
                )
            )
            existing_project = result.scalar_one_or_none()

            if existing_project:
                # 更新项目
                existing_project.indication = (
                    fields.get("适应症") if fields.get("适应症") != "未提及" else None
                )

                # 更新详情
                if existing_project.detail:
                    existing_project.detail.drug_type = (
                        fields.get("药物类型")
                        if fields.get("药物类型") != "未提及"
                        else None
                    )
                    existing_project.detail.dosage_form = (
                        fields.get("药物剂型")
                        if fields.get("药物剂型") != "未提及"
                        else None
                    )
                    existing_project.detail.mechanism = (
                        fields.get("作用机制")
                        if fields.get("作用机制") != "未提及"
                        else None
                    )
                    existing_project.detail.project_highlights = (
                        fields.get("项目亮点")
                        if fields.get("项目亮点") != "未提及"
                        else None
                    )
                    existing_project.detail.differentiation = (
                        fields.get("差异化创新点")
                        if fields.get("差异化创新点") != "未提及"
                        else None
                    )
                else:
                    new_detail = ProjectDetail(
                        project_id=existing_project.id,
                        drug_type=fields.get("药物类型")
                        if fields.get("药物类型") != "未提及"
                        else None,
                        dosage_form=fields.get("药物剂型")
                        if fields.get("药物剂型") != "未提及"
                        else None,
                        mechanism=fields.get("作用机制")
                        if fields.get("作用机制") != "未提及"
                        else None,
                        project_highlights=fields.get("项目亮点")
                        if fields.get("项目亮点") != "未提及"
                        else None,
                        differentiation=fields.get("差异化创新点")
                        if fields.get("差异化创新点") != "未提及"
                        else None,
                    )
                    db.add(new_detail)

                saved_projects.append(
                    {"project_name": project_name, "status": "updated"}
                )
            else:
                # 创建新项目
                from app.schemas.project import ProjectCreate
                from app.models.project import DevPhaseEnum, OverallStatusEnum

                dev_phase_str = fields.get("研究阶段", "")
                dev_phase = phase_map.get(dev_phase_str, None)

                # 构建 follow_up_records
                follow_up_records = [
                    {"type": "extracted", "data": fields, "timestamp": "now"}
                ]

                # 药效指标和安全指标
                efficacy_indicators = None
                safety_indicators = None
                if (
                    fields.get("主要药效指标（临床）")
                    and fields.get("主要药效指标（临床）") != "未提及"
                ):
                    efficacy_indicators = {"临床": fields.get("主要药效指标（临床）")}
                if (
                    fields.get("主要安全性指标（临床）")
                    and fields.get("主要安全性指标（临床）") != "未提及"
                ):
                    safety_indicators = {"临床": fields.get("主要安全性指标（临床）")}

                project_create = ProjectCreate(
                    project_name=project_name,
                    indication=fields.get("适应症")
                    if fields.get("适应症") != "未提及"
                    else None,
                    dev_phase=DevPhaseEnum(dev_phase) if dev_phase else None,
                    overall_status=OverallStatusEnum.SCREENING,
                    drug_type=fields.get("药物类型")
                    if fields.get("药物类型") != "未提及"
                    else None,
                    dosage_form=fields.get("药物剂型")
                    if fields.get("药物剂型") != "未提及"
                    else None,
                    mechanism=fields.get("作用机制")
                    if fields.get("作用机制") != "未提及"
                    else None,
                    project_highlights=fields.get("项目亮点")
                    if fields.get("项目亮点") != "未提及"
                    else None,
                    differentiation=fields.get("差异化创新点")
                    if fields.get("差异化创新点") != "未提及"
                    else None,
                    efficacy_indicators=efficacy_indicators,
                    safety_indicators=safety_indicators,
                    risk_notes=fields.get("风险提示")
                    if fields.get("风险提示") != "未提及"
                    else None,
                    follow_up_records=follow_up_records,
                )

                await project_service.create(project_create)
                saved_projects.append(
                    {"project_name": project_name, "status": "created"}
                )

        await db.commit()

        # 调用 ragforge 上传接口
        filename, file_bytes = pdf_file
        async with httpx.AsyncClient(timeout=300.0) as client:
            response = await client.post(
                f"{self.base_url}/v1/knowledge-bases/{kb_id}/documents",
                headers={"Authorization": f"Bearer {api_key}"},
                files={"file": (filename, file_bytes)},
            )
            response.raise_for_status()
            ragforge_result = response.json()

        return {
            "saved_projects": saved_projects,
            "ragforge_document_id": ragforge_result.get("document_id"),
        }
