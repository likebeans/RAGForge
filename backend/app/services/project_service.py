"""项目服务"""

from sqlalchemy import func, or_, select
from sqlalchemy.orm import selectinload
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.project import ProjectMaster, ProjectDetail, ResearchDetail, ProjectValuation, ProjectManagementInfo, TargetDict
from app.schemas.project import ProjectCreate, ProjectUpdate

class ProjectService:
    """项目服务"""

    def __init__(self, db: AsyncSession):
        self.db = db

    async def get_by_id(self, project_id: str) -> ProjectMaster | None:
        result = await self.db.execute(
            select(ProjectMaster).where(
                ProjectMaster.id == project_id,
                ProjectMaster.is_deleted == False,
            )
        )
        return result.scalar_one_or_none()

    async def get_by_id_with_joins(self, project_id: str) -> ProjectMaster | None:
        result = await self.db.execute(
            select(ProjectMaster)
            .options(
                selectinload(ProjectMaster.target_info),
                selectinload(ProjectMaster.detail),
                selectinload(ProjectMaster.valuations),
                selectinload(ProjectMaster.research_detail),
                selectinload(ProjectMaster.management_info),
            )
            .where(ProjectMaster.id == project_id, ProjectMaster.is_deleted == False)
        )
        return result.scalar_one_or_none()

    async def _resolve_target_id(self, target_name: str) -> str | None:
        """根据靶点名称查找或创建 target_dict 记录，返回 target_id"""
        if not target_name:
            return None
        result = await self.db.execute(
            select(TargetDict).where(TargetDict.standard_name == target_name)
        )
        target = result.scalar_one_or_none()
        if target:
            return target.id
        # 不存在则自动创建
        import re
        new_id = "TGT-" + re.sub(r"[^A-Z0-9]", "", target_name.upper())[:20]
        target = TargetDict(id=new_id, standard_name=target_name)
        self.db.add(target)
        await self.db.flush()
        return new_id

    async def create(self, project_in: ProjectCreate, created_by: str | None = None) -> ProjectMaster:
        import uuid
        from datetime import datetime

        project_id = str(uuid.uuid4())

        # 1. 解析 target_id（按名称自动匹配/创建）
        target_id = await self._resolve_target_id(project_in.target_name)

        # 2. 写入主表
        project = ProjectMaster(
            id=project_id,
            drug_name=project_in.drug_name,
            target_id=target_id,
            indication=project_in.indication,
            dev_phase=project_in.dev_phase,
            overall_status=project_in.overall_status,
            overall_score=project_in.overall_score,
            created_by=created_by,
        )

        # 3. 写入 project_details（有任意一个字段则创建）
        detail_fields = ["drug_type", "dosage_form", "mechanism", "project_highlights",
                         "differentiation", "current_therapy", "efficacy_indicators", "safety_indicators"]
        detail_data = {f: getattr(project_in, f) for f in detail_fields if getattr(project_in, f) is not None}
        if detail_data:
            project.detail = ProjectDetail(project_id=project_id, **detail_data)

        # 4. 写入 project_management_info（有任意一个字段则创建）
        mgmt_fields = ["risk_notes", "follow_up_records"]
        mgmt_data = {f: getattr(project_in, f) for f in mgmt_fields if getattr(project_in, f) is not None}
        if mgmt_data:
            project.management_info = ProjectManagementInfo(project_id=project_id, **mgmt_data)

        # 5. 写入 research_details
        research_fields = ["market_json", "competitor_data", "patent_json", "policy_impact"]
        research_data = {f: getattr(project_in, f) for f in research_fields if getattr(project_in, f) is not None}
        if research_data:
            project.research_detail = ResearchDetail(project_id=project_id, **research_data)

        self.db.add(project)

        # 6. 写入初始估值记录（有 asking_price 或 project_valuation 则创建）
        valuation_fields = ["asking_price", "project_valuation", "company_valuation", "strategic_fit_score"]
        valuation_data = {f: getattr(project_in, f) for f in valuation_fields if getattr(project_in, f) is not None}
        if valuation_data:
            val_date = datetime.fromisoformat(project_in.valuation_date) if project_in.valuation_date else datetime.utcnow()
            self.db.add(ProjectValuation(project_id=project_id, valuation_date=val_date, **valuation_data))

        await self.db.commit()
        await self.db.refresh(project)
        return project

    async def update(self, project: ProjectMaster, update_data: ProjectUpdate) -> ProjectMaster:
        # 1. 更新主表字段
        update_dict = update_data.model_dump(exclude_unset=True)
        
        for key in ["drug_name", "target_id", "indication", "dev_phase", "overall_status", "overall_score"]:
            if key in update_dict:
                setattr(project, key, update_dict[key])

        # 2. 更新 1:1 映射关系 (如果不存在则创建，存在则更新)
        if "detail" in update_dict and update_dict["detail"]:
            if project.detail:
                for k, v in update_dict["detail"].items():
                    setattr(project.detail, k, v)
            else:
                project.detail = ProjectDetail(project_id=project.id, **update_dict["detail"])

        if "research_detail" in update_dict and update_dict["research_detail"]:
            if project.research_detail:
                for k, v in update_dict["research_detail"].items():
                    setattr(project.research_detail, k, v)
            else:
                project.research_detail = ResearchDetail(project_id=project.id, **update_dict["research_detail"])

        if "management_info" in update_dict and update_dict["management_info"]:
            if project.management_info:
                for k, v in update_dict["management_info"].items():
                    setattr(project.management_info, k, v)
            else:
                project.management_info = ProjectManagementInfo(project_id=project.id, **update_dict["management_info"])

        await self.db.commit()
        await self.db.refresh(project)
        return project

    async def soft_delete(self, project: ProjectMaster) -> None:
        project.is_deleted = True
        await self.db.commit()

    async def query_projects(
        self,
        page: int,
        page_size: int,
        keyword: str | None = None,
        drug_type: str | None = None,
        dev_phase: str | None = None,
        score_min: float | None = None,
        score_max: float | None = None,
        sort_by: str | None = None,
        sort_order: str = "desc",
    ) -> tuple[list[ProjectMaster], int]:
        filters = [ProjectMaster.is_deleted == False]

        if keyword:
            like = f"%{keyword}%"
            filters.append(
                or_(
                    ProjectMaster.drug_name.ilike(like),
                    ProjectMaster.indication.ilike(like),
                )
            )

        if dev_phase:
            filters.append(ProjectMaster.dev_phase == dev_phase)

        if score_min is not None:
            filters.append(ProjectMaster.overall_score >= score_min)

        if score_max is not None:
            filters.append(ProjectMaster.overall_score <= score_max)

        sort_map = {
            "created_at": ProjectMaster.created_at,
            "overall_score": ProjectMaster.overall_score,
            "drug_name": ProjectMaster.drug_name,
        }
        sort_col = sort_map.get(sort_by or "created_at", ProjectMaster.created_at)
        order_clause = sort_col.desc() if sort_order.lower() == "desc" else sort_col.asc()
        offset = (page - 1) * page_size

        from app.models.project import ProjectDetail as _PD

        if drug_type:
            # drug_type 在 project_details 子表，需要 join
            detail_filter = _PD.drug_type == drug_type
            count_q = (
                select(func.count())
                .select_from(ProjectMaster)
                .join(_PD, _PD.project_id == ProjectMaster.id)
                .where(*filters, detail_filter)
            )
            total_result = await self.db.execute(count_q)
            total = int(total_result.scalar() or 0)

            result = await self.db.execute(
                select(ProjectMaster)
                .join(_PD, _PD.project_id == ProjectMaster.id)
                .options(
                    selectinload(ProjectMaster.target_info),
                    selectinload(ProjectMaster.detail),
                    selectinload(ProjectMaster.valuations),
                )
                .where(*filters, detail_filter)
                .order_by(order_clause)
                .offset(offset)
                .limit(page_size)
            )
        else:
            count_q = select(func.count()).select_from(
                select(ProjectMaster).where(*filters).subquery()
            )
            total_result = await self.db.execute(count_q)
            total = int(total_result.scalar() or 0)

            result = await self.db.execute(
                select(ProjectMaster)
                .options(
                    selectinload(ProjectMaster.target_info),
                    selectinload(ProjectMaster.detail),
                    selectinload(ProjectMaster.valuations),
                )
                .where(*filters)
                .order_by(order_clause)
                .offset(offset)
                .limit(page_size)
            )

        items = list(result.scalars().unique().all())
        return items, total

