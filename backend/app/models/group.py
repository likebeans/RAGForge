"""部门模型"""

from uuid import uuid4
from sqlalchemy import String, Text, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.models.mixins import TimestampMixin


class Group(TimestampMixin, Base):
    """部门表"""
    __tablename__ = "groups"
    
    id: Mapped[str] = mapped_column(
        String(36),
        primary_key=True,
        default=lambda: str(uuid4())
    )
    name: Mapped[str] = mapped_column(String(50), unique=True, nullable=False)
    display_name: Mapped[str | None] = mapped_column(String(100))
    description: Mapped[str | None] = mapped_column(Text)
    parent_id: Mapped[str | None] = mapped_column(
        String(36),
        ForeignKey("groups.id"),
        nullable=True
    )
    
    users: Mapped[list["User"]] = relationship(
        "User",
        secondary="user_groups",
        back_populates="groups"
    )
    
    children: Mapped[list["Group"]] = relationship(
        "Group",
        back_populates="parent"
    )
    parent: Mapped["Group | None"] = relationship(
        "Group",
        back_populates="children",
        remote_side=[id]
    )
