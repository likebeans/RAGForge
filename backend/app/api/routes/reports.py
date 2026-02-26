"""报告管理路由"""

import csv
import io
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import Response
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user
from app.db.session import get_db
from app.models import Report, User
from app.schemas.report import (
    ReportBulkDeleteRequest,
    ReportBulkDeleteResponse,
    ReportCreate,
    ReportListResponse,
    ReportResponse,
    ReportUpdate,
)
from app.services.report_service import ReportService

router = APIRouter()


@router.get("", response_model=ReportListResponse)
async def list_reports(
    page: int = 1,
    page_size: int = 20,
    keyword: str | None = None,
    sort_by: str | None = None,
    sort_order: str = "desc",
    ids: str | None = None,
    status: str | None = None,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_user),
):
    service = ReportService(db)

    if page < 1 or page_size < 1 or page_size > 200:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid pagination")

    id_list: list[int] | None = None
    if ids:
        try:
            id_list = [int(x) for x in ids.split(",") if x.strip()]
        except ValueError:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid ids")

    items, total = await service.query_reports(
        page=page,
        page_size=page_size,
        keyword=keyword,
        sort_by=sort_by,
        sort_order=sort_order,
        ids=id_list,
        status=status,
    )

    return ReportListResponse(
        items=[ReportResponse.model_validate(r) for r in items],
        total=total,
        page=page,
        page_size=page_size,
    )


@router.get("/export")
async def export_reports(
    keyword: str | None = None,
    sort_by: str | None = None,
    sort_order: str = "desc",
    ids: str | None = None,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_user),
):
    service = ReportService(db)

    id_list: list[int] | None = None
    if ids:
        try:
            id_list = [int(x) for x in ids.split(",") if x.strip()]
        except ValueError:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid ids")

    items = await service.list_reports(
        keyword=keyword,
        sort_by=sort_by,
        sort_order=sort_order,
        ids=id_list,
        limit=5000,
    )

    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(["id", "title", "created_by_username", "created_at", "updated_at", "content"])
    for r in items:
        writer.writerow(
            [
                r.id,
                r.title,
                r.user.username if r.user else "",
                r.created_at.isoformat() if r.created_at else "",
                r.updated_at.isoformat() if r.updated_at else "",
                (r.content or "").replace("\r\n", "\n"),
            ]
        )

    csv_text = output.getvalue()
    output.close()

    filename = f"reports_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
    content = ("\ufeff" + csv_text).encode("utf-8")
    return Response(
        content=content,
        media_type="text/csv; charset=utf-8",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


@router.post("/bulk-delete", response_model=ReportBulkDeleteResponse)
async def bulk_delete_reports(
    data: ReportBulkDeleteRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    service = ReportService(db)

    ids = [i for i in (data.ids or []) if i]
    if not ids:
        return ReportBulkDeleteResponse(deleted_count=0)

    deleted = 0
    for report_id in ids:
        report = await service.get_by_id(report_id)
        if not report:
            continue
        if not current_user.is_admin and report.user_id and report.user_id != current_user.id:
            continue
        await service.soft_delete(report)
        deleted += 1

    return ReportBulkDeleteResponse(deleted_count=deleted)



@router.get("/{report_id}", response_model=ReportResponse)
async def get_report(
    report_id: str,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_user),
):
    service = ReportService(db)
    report = await service.get_by_id(report_id)
    if not report:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Report not found")
    return ReportResponse.model_validate(report)


@router.post("", response_model=ReportResponse)
async def create_report(
    data: ReportCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    service = ReportService(db)
    report = Report(**data.model_dump(), user_id=current_user.id)
    report = await service.create(report)
    report = await service.get_by_id(report.id) or report
    return ReportResponse.model_validate(report)


@router.put("/{report_id}", response_model=ReportResponse)
async def update_report(
    report_id: str,
    data: ReportUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    service = ReportService(db)
    report = await service.get_by_id(report_id)
    if not report:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Report not found")

    if not current_user.is_admin and report.user_id and report.user_id != current_user.id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Permission denied")

    update_data = data.model_dump(exclude_unset=True)
    report = await service.update(report, **update_data)
    report.user_id = report.user_id or current_user.id
    await db.commit()
    report = await service.get_by_id(report.id) or report
    return ReportResponse.model_validate(report)


@router.delete("/{report_id}")
async def delete_report(
    report_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    service = ReportService(db)
    report = await service.get_by_id(report_id)
    if not report:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Report not found")

    if not current_user.is_admin and report.user_id and report.user_id != current_user.id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Permission denied")

    await service.soft_delete(report)
    return {"message": "Report deleted"}
