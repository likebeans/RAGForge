"""项目 Schemas"""

from datetime import datetime

from pydantic import BaseModel


class ProjectBase(BaseModel):
    project_name: str
    target: str | None = None
    target_type: str | None = None
    mechanism: str | None = None

    drug_type: str | None = None
    dosage_form: str | None = None
    research_stage: str | None = None

    indication: str | None = None
    indication_type: str | None = None
    project_highlights: str | None = None
    differentiation: str | None = None

    efficacy_indicators: str | None = None
    safety_indicators: str | None = None
    current_therapy: str | None = None

    competition_status: str | None = None
    patent_status: str | None = None
    patent_layout: str | None = None

    asking_price: float | None = None
    project_valuation: float | None = None
    company_valuation: float | None = None
    overall_score: float | None = None
    strategic_fit_score: float | None = None

    research_institution: str | None = None
    project_leader: str | None = None
    risk_notes: str | None = None


class ProjectCreate(ProjectBase):
    pass


class ProjectUpdate(BaseModel):
    project_name: str | None = None
    target: str | None = None
    target_type: str | None = None
    mechanism: str | None = None

    drug_type: str | None = None
    dosage_form: str | None = None
    research_stage: str | None = None

    indication: str | None = None
    indication_type: str | None = None
    project_highlights: str | None = None
    differentiation: str | None = None

    efficacy_indicators: str | None = None
    safety_indicators: str | None = None
    current_therapy: str | None = None

    competition_status: str | None = None
    patent_status: str | None = None
    patent_layout: str | None = None

    asking_price: float | None = None
    project_valuation: float | None = None
    company_valuation: float | None = None
    overall_score: float | None = None
    strategic_fit_score: float | None = None

    research_institution: str | None = None
    project_leader: str | None = None
    risk_notes: str | None = None


class ProjectResponse(ProjectBase):
    id: int
    created_by: str | None = None
    is_deleted: bool
    created_at: datetime
    updated_at: datetime | None = None

    class Config:
        from_attributes = True


class ProjectListResponse(BaseModel):
    items: list[ProjectResponse]
    total: int
    page: int
    page_size: int
