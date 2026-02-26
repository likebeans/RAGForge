"""报告服务"""

from sqlalchemy import func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models import Report, User


class ReportService:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def get_by_id(self, report_id: int) -> Report | None:
        result = await self.db.execute(
            select(Report)
            .options(selectinload(Report.creator))
            .where(
                Report.id == report_id,
                Report.is_deleted == False,
            )
        )
        return result.scalar_one_or_none()

    async def create(self, report: Report) -> Report:
        self.db.add(report)
        await self.db.commit()
        await self.db.refresh(report)
        return report

    async def update(self, report: Report, **kwargs) -> Report:
        for key, value in kwargs.items():
            if value is not None and hasattr(report, key):
                setattr(report, key, value)
        await self.db.commit()
        await self.db.refresh(report)
        return report

    async def soft_delete(self, report: Report) -> None:
        report.is_deleted = True
        await self.db.commit()

    async def query_reports(
        self,
        page: int,
        page_size: int,
        keyword: str | None = None,
        sort_by: str | None = None,
        sort_order: str = "desc",
        ids: list[int] | None = None,
    ) -> tuple[list[Report], int]:
        filters = [Report.is_deleted == False]

        if keyword:
            like = f"%{keyword}%"
            filters.append(or_(Report.title.ilike(like), Report.content.ilike(like)))

        if ids:
            filters.append(Report.id.in_(ids))

        sort_map = {
            "created_at": Report.created_at,
            "updated_at": Report.updated_at,
            "title": Report.title,
            "created_by": User.username,
            "created_by_username": User.username,
        }
        sort_col = sort_map.get(sort_by or "created_at", Report.created_at)
        order_clause = sort_col.desc() if sort_order.lower() == "desc" else sort_col.asc()

        total_result = await self.db.execute(select(func.count()).select_from(select(Report).where(*filters).subquery()))
        total = int(total_result.scalar() or 0)

        offset = (page - 1) * page_size
        stmt = (
            select(Report)
            .options(selectinload(Report.creator))
            .where(*filters)
        )
        if sort_col is User.username:
            stmt = stmt.outerjoin(User, Report.created_by == User.id)

        result = await self.db.execute(
            stmt.order_by(order_clause).offset(offset).limit(page_size)
        )
        items = list(result.scalars().all())
        return items, total

    async def list_reports(
        self,
        keyword: str | None = None,
        sort_by: str | None = None,
        sort_order: str = "desc",
        ids: list[int] | None = None,
        limit: int = 5000,
    ) -> list[Report]:
        filters = [Report.is_deleted == False]

        if keyword:
            like = f"%{keyword}%"
            filters.append(or_(Report.title.ilike(like), Report.content.ilike(like)))

        if ids:
            filters.append(Report.id.in_(ids))

        sort_map = {
            "created_at": Report.created_at,
            "updated_at": Report.updated_at,
            "title": Report.title,
            "created_by": User.username,
            "created_by_username": User.username,
        }
        sort_col = sort_map.get(sort_by or "created_at", Report.created_at)
        order_clause = sort_col.desc() if sort_order.lower() == "desc" else sort_col.asc()

        stmt = (
            select(Report)
            .options(selectinload(Report.creator))
            .where(*filters)
        )
        if sort_col is User.username:
            stmt = stmt.outerjoin(User, Report.created_by == User.id)

        result = await self.db.execute(stmt.order_by(order_clause).limit(limit))
        return list(result.scalars().all())
