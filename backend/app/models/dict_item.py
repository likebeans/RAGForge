"""字典项模型"""

from sqlalchemy import String, Boolean, Integer, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base
from app.models.mixins import TimestampMixin


class DictItem(TimestampMixin, Base):
    """字典项表"""

    __tablename__ = "dict_items"
    __table_args__ = (UniqueConstraint("category", "code", name="uq_dict_items_category_code"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)

    category: Mapped[str] = mapped_column(String(50), nullable=False, index=True)
    code: Mapped[str] = mapped_column(String(50), nullable=False)
    label: Mapped[str] = mapped_column(String(100), nullable=False)
    sort_order: Mapped[int] = mapped_column(Integer, default=0)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, index=True)
