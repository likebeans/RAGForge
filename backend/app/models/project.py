"""创新药项目模型"""

from sqlalchemy import String, Text, ForeignKey, Boolean, Integer, Numeric
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base
from app.models.mixins import TimestampMixin


class DrugProject(TimestampMixin, Base):
    """创新药项目表"""

    __tablename__ = "drug_projects"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)

    # 基础信息
    project_name: Mapped[str] = mapped_column(String(200), nullable=False, index=True)
    target: Mapped[str | None] = mapped_column(String(100), index=True)
    target_type: Mapped[str | None] = mapped_column(String(50), index=True)
    mechanism: Mapped[str | None] = mapped_column(String(500))

    # 研发属性
    drug_type: Mapped[str | None] = mapped_column(String(50), index=True)
    dosage_form: Mapped[str | None] = mapped_column(String(50), index=True)
    research_stage: Mapped[str | None] = mapped_column(String(50), index=True)

    # 核心价值
    indication: Mapped[str | None] = mapped_column(String(200), index=True)
    indication_type: Mapped[str | None] = mapped_column(String(100), index=True)
    project_highlights: Mapped[str | None] = mapped_column(Text)
    differentiation: Mapped[str | None] = mapped_column(Text)

    # 临床数据
    efficacy_indicators: Mapped[str | None] = mapped_column(Text)
    safety_indicators: Mapped[str | None] = mapped_column(Text)
    current_therapy: Mapped[str | None] = mapped_column(Text)

    # 竞争与专利
    competition_status: Mapped[str | None] = mapped_column(Text)
    patent_status: Mapped[str | None] = mapped_column(Text)
    patent_layout: Mapped[str | None] = mapped_column(Text)

    # 估值与评分
    asking_price: Mapped[float | None] = mapped_column(Numeric(15, 2))
    project_valuation: Mapped[float | None] = mapped_column(Numeric(15, 2))
    company_valuation: Mapped[float | None] = mapped_column(Numeric(15, 2))
    overall_score: Mapped[float | None] = mapped_column(Numeric(3, 1), index=True)
    strategic_fit_score: Mapped[float | None] = mapped_column(Numeric(3, 1))

    # 辅助管理
    research_institution: Mapped[str | None] = mapped_column(String(200), index=True)
    project_leader: Mapped[str | None] = mapped_column(String(200))
    risk_notes: Mapped[str | None] = mapped_column(Text)

    # 系统字段
    created_by: Mapped[str | None] = mapped_column(String(36), ForeignKey("users.id"), nullable=True)
    is_deleted: Mapped[bool] = mapped_column(Boolean, default=False, index=True)
