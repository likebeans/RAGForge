# 提取模板模型（用于 PDF 字段提取）

from uuid import uuid4
from sqlalchemy import Column, String, JSON, ForeignKey, Text

from app.db.base import Base
from app.models.mixins import TimestampMixin


class ExtractionSchema(Base, TimestampMixin):
    """
    提取模板（用于结构化提取 PDF 数据）
    
    用户上传 Excel 模板定义要提取的字段，
    然后上传 PDF 文件，系统按模板提取字段并导出 Excel。
    """
    __tablename__ = "extraction_schemas"
    
    id = Column(String(36), primary_key=True, default=lambda: str(uuid4()))
    tenant_id = Column(String(36), ForeignKey("tenants.id"), nullable=False, index=True)
    knowledge_base_id = Column(String(36), ForeignKey("knowledge_bases.id"), nullable=True, index=True)
    
    name = Column(String(255), nullable=False)
    description = Column(Text, nullable=True)
    
    # 字段定义 JSON
    # [{"name": "产品名称", "type": "string", "required": true}, ...]
    fields = Column(JSON, nullable=False, default=list)
    
    # 来源文件名
    source_filename = Column(String(255), nullable=True)
    
    # 使用统计
    usage_count = Column(String(36), default="0")  # 提取次数
