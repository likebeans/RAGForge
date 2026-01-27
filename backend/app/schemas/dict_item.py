"""字典 Schemas"""

from datetime import datetime

from pydantic import BaseModel


class DictItemResponse(BaseModel):
    id: int
    category: str
    code: str
    label: str
    sort_order: int
    is_active: bool
    created_at: datetime
    updated_at: datetime | None = None

    class Config:
        from_attributes = True
