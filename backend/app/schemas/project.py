"""项目管理相关 Data Schemas

基于拆分后的 7 张模型表重建的 Pydantic 模型。
1. ProjectMaster
2. ProjectDetail
3. ProjectValuation
4. ResearchDetail
5. TargetDict
6. ProjectManagementInfo
"""

from datetime import datetime
from pydantic import BaseModel, ConfigDict, Field
from app.models.project import DevPhaseEnum, OverallStatusEnum


# ==========================================
# 细节组件 Schemas (对应各类 1:1 或 1:N 附属表)
# ==========================================

class TargetDictBase(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    standard_name: str
    aliases: dict | None = None
    moa_default: str | None = None

class TargetDictResponse(TargetDictBase):
    id: str

class ProjectDetailBase(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    drug_type: str | None = None
    dosage_form: str | None = None
    mechanism: str | None = None
    project_highlights: str | None = None
    differentiation: str | None = None
    efficacy_indicators: dict | None = None
    safety_indicators: dict | None = None
    current_therapy: str | None = None

class ResearchDetailBase(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    market_json: dict | None = None
    target_mech: str | None = None
    competitor_data: dict | None = None
    patent_json: dict | None = None
    policy_impact: str | None = None

class ProjectManagementInfoBase(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    project_leader_id: str | None = None
    risk_notes: str | None = None
    follow_up_records: list | None = None

class ProjectValuationBase(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    asking_price: float | None = None
    project_valuation: float | None = None
    company_valuation: float | None = None
    strategic_fit_score: float | None = None
    valuation_date: datetime | None = None

class ProjectValuationResponse(ProjectValuationBase):
    id: int

# ==========================================
# 主项目聚合 Schemas
# ==========================================

class ProjectCreate(BaseModel):
    """创建项目 - 平铺 DTO，后端自动拆分写入各子表"""

    # ── project_master ──────────────────────────────
    project_name: str = Field(..., description="药物/项目名称")
    target_name: str | None = Field(None, description="靶点名称（后端自动匹配/创建 target_dict）")
    indication: str | None = Field(None, description="适应症")
    dev_phase: DevPhaseEnum | None = Field(None, description="研发阶段")
    overall_status: OverallStatusEnum = Field(OverallStatusEnum.SCREENING, description="项目状态")
    overall_score: float | None = Field(None, ge=0, le=10, description="综合评分 0-10")

    # ── project_details (1:1) ───────────────────────
    drug_type: str | None = Field(None, description="药物类型，如 biologic / small_molecule")
    dosage_form: str | None = Field(None, description="剂型，如 injection / tablet")
    mechanism: str | None = Field(None, description="作用机制")
    project_highlights: str | None = Field(None, description="项目亮点")
    differentiation: str | None = Field(None, description="差异化创新点")
    current_therapy: str | None = Field(None, description="当前标准疗法")
    efficacy_indicators: dict | None = Field(None, description="药效指标 JSON")
    safety_indicators: dict | None = Field(None, description="安全性指标 JSON")

    # ── project_valuations (初始一条) ───────────────
    asking_price: float | None = Field(None, description="报价（万元）")
    project_valuation: float | None = Field(None, description="项目估值（万元）")
    company_valuation: float | None = Field(None, description="公司估值（万元）")
    strategic_fit_score: float | None = Field(None, ge=0, le=10, description="战略匹配度 0-10")
    valuation_date: str | None = Field(None, description="估值日期 ISO8601，默认当天")

    # ── project_management_info (1:1) ───────────────
    risk_notes: str | None = Field(None, description="风险提示")
    follow_up_records: list | None = Field(None, description="跟进记录列表")

    # ── research_details (1:1) ──────────────────────
    market_json: dict | None = Field(None, description="市场信息 JSON")
    competitor_data: dict | None = Field(None, description="竞品数据 JSON")
    patent_json: dict | None = Field(None, description="专利信息 JSON")
    policy_impact: str | None = Field(None, description="政策影响")


class ProjectUpdate(BaseModel):
    """更新项目时的聚合传参结构"""
    project_name: str | None = None
    target_id: str | None = None
    indication: str | None = None
    dev_phase: DevPhaseEnum | None = None
    overall_status: OverallStatusEnum | None = None
    overall_score: float | None = None

    detail: ProjectDetailBase | None = None
    research_detail: ResearchDetailBase | None = None
    management_info: ProjectManagementInfoBase | None = None


class ProjectResponse(BaseModel):
    """列表页/精简信息响应 (含主表 + 关联子表的平铺字段)"""
    id: str
    project_name: str
    target_id: str | None = None
    target_name: str | None = None       # 来自 target_dict.standard_name
    indication: str | None = None
    dev_phase: DevPhaseEnum | None = None
    overall_status: OverallStatusEnum
    overall_score: float | None = None

    # 来自 project_details
    drug_type: str | None = None
    dosage_form: str | None = None

    # 来自 project_valuations (最新一条的 asking_price)
    asking_price: float | None = None

    created_by: str | None = None
    created_at: datetime
    updated_at: datetime | None = None

    @classmethod
    def from_orm_with_joins(cls, project) -> "ProjectResponse":
        """从含关联对象的 ORM 实体中构建响应"""
        return cls(
            id=project.id,
            project_name=project.project_name,
            target_id=project.target_id,
            target_name=project.target_info.standard_name if project.target_info else None,
            indication=project.indication,
            dev_phase=project.dev_phase,
            overall_status=project.overall_status,
            overall_score=float(project.overall_score) if project.overall_score else None,
            drug_type=project.detail.drug_type if project.detail else None,
            dosage_form=project.detail.dosage_form if project.detail else None,
            asking_price=(
                float(project.valuations[-1].asking_price)
                if project.valuations and project.valuations[-1].asking_price
                else None
            ),
            created_by=project.created_by,
            created_at=project.created_at,
            updated_at=project.updated_at,
        )

    class Config:
        from_attributes = True


class ProjectDetailResponse(ProjectResponse):
    """详情页响应 (包含所有聚合的 1:1 信息及 1:N 估值列表)"""
    detail: ProjectDetailBase | None = None
    research_detail: ResearchDetailBase | None = None
    management_info: ProjectManagementInfoBase | None = None
    valuations: list[ProjectValuationResponse] | None = None

    class Config:
        from_attributes = True


class ProjectListResponse(BaseModel):
    items: list[ProjectResponse]
    total: int
    page: int
    page_size: int
