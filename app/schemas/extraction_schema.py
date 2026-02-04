# 提取模板 Pydantic 模型

from pydantic import BaseModel, Field
from datetime import datetime


class ExtractionField(BaseModel):
    """提取字段定义"""
    name: str = Field(..., description="字段名称")
    type: str = Field(default="string", description="字段类型: string/number/date/boolean")
    required: bool = Field(default=False, description="是否必填")
    description: str | None = Field(default=None, description="字段说明")


class ExtractionSchemaCreate(BaseModel):
    """创建提取模板请求"""
    name: str = Field(..., description="模板名称")
    description: str | None = Field(default=None, description="模板描述")
    knowledge_base_id: str | None = Field(default=None, description="关联的知识库 ID")


class ExtractionSchemaResponse(BaseModel):
    """提取模板响应"""
    id: str
    name: str
    description: str | None = None
    fields: list[dict]
    source_filename: str | None = None
    usage_count: str = "0"
    created_at: datetime
    
    class Config:
        from_attributes = True


class ExtractionSchemaListResponse(BaseModel):
    """提取模板列表响应"""
    items: list[ExtractionSchemaResponse]
    total: int


class ExtractedResult(BaseModel):
    """单个文件的提取结果"""
    filename: str
    success: bool = True
    fields: dict | None = None
    error: str | None = None


class BatchExtractResponse(BaseModel):
    """批量提取响应"""
    results: list[ExtractedResult]
    total: int
    success: int
    failed: int
