"""Playground Ground（临时知识库）相关模型"""

from datetime import datetime
from pydantic import BaseModel, Field


class GroundCreate(BaseModel):
    name: str | None = Field(default=None, description="Ground 名称，未传则自动生成")
    description: str | None = Field(default=None, description="描述")


class GroundInfo(BaseModel):
    ground_id: str
    knowledge_base_id: str
    name: str
    description: str | None = None
    created_at: datetime
    document_count: int = 0
    saved: bool = False


class GroundListResponse(BaseModel):
    items: list[GroundInfo]
    total: int
