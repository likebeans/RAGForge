"""项目服务"""

from sqlalchemy import func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import DrugProject


class ProjectService:
    """项目服务"""

    def __init__(self, db: AsyncSession):
        self.db = db

    async def get_by_id(self, project_id: int) -> DrugProject | None:
        result = await self.db.execute(
            select(DrugProject).where(
                DrugProject.id == project_id,
                DrugProject.is_deleted == False,
            )
        )
        return result.scalar_one_or_none()

    async def create(self, project: DrugProject) -> DrugProject:
        self.db.add(project)
        await self.db.commit()
        await self.db.refresh(project)
        return project

    async def update(self, project: DrugProject, **kwargs) -> DrugProject:
        for key, value in kwargs.items():
            if value is not None and hasattr(project, key):
                setattr(project, key, value)
        await self.db.commit()
        await self.db.refresh(project)
        return project

    async def soft_delete(self, project: DrugProject) -> None:
        project.is_deleted = True
        await self.db.commit()

    async def query_projects(
        self,
        page: int,
        page_size: int,
        keyword: str | None = None,
        target_type: list[str] | None = None,
        drug_type: list[str] | None = None,
        research_stage: list[str] | None = None,
        indication_type: list[str] | None = None,
        score_min: float | None = None,
        score_max: float | None = None,
        valuation_min: float | None = None,
        valuation_max: float | None = None,
        sort_by: str | None = None,
        sort_order: str = "desc",
    ) -> tuple[list[DrugProject], int]:
        filters = [DrugProject.is_deleted == False]

        if keyword:
            like = f"%{keyword}%"
            filters.append(
                or_(
                    DrugProject.project_name.ilike(like),
                    DrugProject.target.ilike(like),
                    DrugProject.indication.ilike(like),
                )
            )

        if target_type:
            filters.append(DrugProject.target_type.in_(target_type))
        if drug_type:
            filters.append(DrugProject.drug_type.in_(drug_type))
        if research_stage:
            filters.append(DrugProject.research_stage.in_(research_stage))
        if indication_type:
            filters.append(DrugProject.indication_type.in_(indication_type))

        if score_min is not None:
            filters.append(DrugProject.overall_score >= score_min)
        if score_max is not None:
            filters.append(DrugProject.overall_score <= score_max)
        if valuation_min is not None:
            filters.append(DrugProject.project_valuation >= valuation_min)
        if valuation_max is not None:
            filters.append(DrugProject.project_valuation <= valuation_max)

        sort_map = {
            "created_at": DrugProject.created_at,
            "overall_score": DrugProject.overall_score,
            "project_valuation": DrugProject.project_valuation,
            "project_name": DrugProject.project_name,
        }
        sort_col = sort_map.get(sort_by or "created_at", DrugProject.created_at)
        order_clause = sort_col.desc() if sort_order.lower() == "desc" else sort_col.asc()

        total_result = await self.db.execute(select(func.count()).select_from(select(DrugProject).where(*filters).subquery()))
        total = int(total_result.scalar() or 0)

        offset = (page - 1) * page_size
        result = await self.db.execute(
            select(DrugProject)
            .where(*filters)
            .order_by(order_clause)
            .offset(offset)
            .limit(page_size)
        )
        items = list(result.scalars().all())
        return items, total
