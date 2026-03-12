"""项目管理路由"""

from fastapi import APIRouter, Depends, HTTPException, status, UploadFile, File
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_admin_user, get_current_user
from app.db.session import get_db
from app.models.user import User
from app.schemas.project import ProjectCreate, ProjectListResponse, ProjectResponse, ProjectDetailResponse, ProjectUpdate
from app.services.project_service import ProjectService
from app.services.import_export_service import ImportExportService

router = APIRouter()


def _split_csv(value: str | None) -> list[str] | None:
    if not value:
        return None
    parts = [v.strip() for v in value.split(",") if v.strip()]
    return parts or None


@router.get("/template/download")
async def download_template(
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_user),
):
    """下载 Excel 导入模板"""
    service = ImportExportService(db)
    template = service.create_template()
    
    return StreamingResponse(
        template,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={
            "Content-Disposition": "attachment; filename=project_import_template.xlsx"
        }
    )


@router.post("/import")
async def import_projects(
    file: UploadFile = File(...),
    mode: str = "append",
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_admin_user),
):
    """
    导入 Excel 文件
    
    Args:
        file: Excel 文件
        mode: 导入模式 (append: 追加, replace: 替换全部)
    """
    if not file.filename.endswith(('.xlsx', '.xls')):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Only Excel files (.xlsx, .xls) are supported"
        )
    
    if mode not in ["append", "replace"]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Mode must be 'append' or 'replace'"
        )
    
    try:
        content = await file.read()
        service = ImportExportService(db)
        result = await service.import_from_excel(
            file_content=content,
            mode=mode,
            created_by=current_user.id
        )
        return result
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Import failed: {str(e)}"
        )


@router.get("/export")
async def export_projects(
    page: int = 1,
    page_size: int = 1000,
    keyword: str | None = None,
    sort_by: str | None = None,
    sort_order: str = "desc",
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_user),
):
    """导出项目数据到 Excel（支持筛选条件）"""
    # ... 后续需要重构 ImportExportService 以适配新的 7 张表关联关系
    service = ImportExportService(db)
    
    excel_file = await service.export_to_excel(
        page=page,
        page_size=page_size,
        keyword=keyword,
        sort_by=sort_by,
        sort_order=sort_order,
    )
    
    from datetime import datetime
    filename = f"projects_export_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx"
    
    return StreamingResponse(
        excel_file,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={
            "Content-Disposition": f"attachment; filename={filename}"
        }
    )


@router.get("", response_model=ProjectListResponse)
async def list_projects(
    page: int = 1,
    page_size: int = 20,
    keyword: str | None = None,
    drug_type: str | None = None,
    dev_phase: str | None = None,
    score_min: float | None = None,
    score_max: float | None = None,
    sort_by: str | None = None,
    sort_order: str = "desc",
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_user),
):
    service = ProjectService(db)

    if page < 1 or page_size < 1 or page_size > 200:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid pagination")

    items, total = await service.query_projects(
        page=page,
        page_size=page_size,
        keyword=keyword,
        drug_type=drug_type,
        dev_phase=dev_phase,
        score_min=score_min,
        score_max=score_max,
        sort_by=sort_by,
        sort_order=sort_order,
    )

    return ProjectListResponse(
        items=[ProjectResponse.from_orm_with_joins(p) for p in items],
        total=total,
        page=page,
        page_size=page_size,
    )


@router.get("/{project_id}", response_model=ProjectDetailResponse)
async def get_project(
    project_id: str,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_user),
):
    service = ProjectService(db)
    project = await service.get_by_id_with_joins(project_id)
    if not project:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Project not found")
    return ProjectDetailResponse.model_validate(project)


@router.post("", response_model=ProjectResponse)
async def create_project(
    data: ProjectCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_admin_user),
):
    service = ProjectService(db)
    project = await service.create(project_in=data, created_by=current_user.id)
    # 重新加载含子表的完整对象
    project = await service.get_by_id_with_joins(project.id)
    return ProjectResponse.from_orm_with_joins(project)


@router.put("/{project_id}", response_model=ProjectDetailResponse)
async def update_project(
    project_id: str,
    data: ProjectUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_admin_user),
):
    service = ProjectService(db)

    project = await service.get_by_id(project_id)
    if not project:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Project not found")

    project = await service.update(project=project, update_data=data)
    project.created_by = project.created_by or current_user.id
    
    return ProjectDetailResponse.model_validate(project)


@router.delete("/{project_id}")
async def delete_project(
    project_id: str,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_admin_user),
):
    service = ProjectService(db)

    project = await service.get_by_id(project_id)
    if not project:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Project not found")

    await service.soft_delete(project)
    return {"message": "Project deleted"}
