"""报告 Schemas"""

from datetime import datetime, timezone, timedelta
from typing import Optional

from pydantic import BaseModel, field_serializer
from app.models.report import ReportStatus
from html import unescape
import re


class ReportBase(BaseModel):
    title: str
    content: str | None = None


class ReportCreate(ReportBase):
    status: ReportStatus | None = None


class ReportUpdate(BaseModel):
    title: str | None = None
    content: str | None = None
    status: ReportStatus | None = None


class UserSummary(BaseModel):
    id: str
    username: str | None = None
    display_name: str | None = None

    class Config:
        from_attributes = True


class ReportResponse(ReportBase):
    id: str
    user_id: str
    user: Optional[UserSummary] = None
    is_deleted: bool = False
    created_at: datetime
    updated_at: datetime | None = None
    status: ReportStatus | None = None

    @field_serializer('content')
    def serialize_content(self, content: Optional[str], _info):
        if content is None:
            return None
        return content

    @field_serializer('created_at', 'updated_at')
    def serialize_datetime(self, dt: Optional[datetime], _info):
        """将UTC时间转换为北京时间（UTC+8）"""
        if dt is None:
            return None
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        beijing_tz = timezone(timedelta(hours=8))
        return dt.astimezone(beijing_tz)

    class Config:
        from_attributes = True


class ReportListResponse(BaseModel):
    items: list[ReportResponse]
    total: int
    page: int
    page_size: int


class ReportBulkDeleteRequest(BaseModel):
    ids: list[str]


class ReportBulkDeleteResponse(BaseModel):
    deleted_count: int
