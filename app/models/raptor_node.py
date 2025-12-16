"""
RAPTOR 节点模型

存储 RAPTOR 索引树的节点信息，包括原始 Chunks（叶子节点）和摘要节点。

数据流向: Chunks → RaptorIndexer → RaptorNodes → 向量库
         检索时: Query → 向量库 → RaptorNodes → 返回结果

树结构示例::

    Layer 2 (Root):     [Summary]
                            |
    Layer 1:        [S1]       [S2]
                    /  |        |  \\
    Layer 0:     [C1][C2]    [C3][C4]  (原始 Chunks)
"""

from uuid import uuid4

from sqlalchemy import ForeignKey, Integer, JSON, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base
from app.models.mixins import TIMESTAMP_PK, TimestampMixin


class RaptorNode(TimestampMixin, Base):
    """
    RAPTOR 树节点表
    
    存储 RAPTOR 索引的所有节点，包括：
    - 叶子节点（level=0）：对应原始 Chunk
    - 摘要节点（level>0）：聚类后生成的摘要
    """
    __tablename__ = "raptor_nodes"

    # ==================== 主键与关联 ====================
    # 主键
    id: Mapped[TIMESTAMP_PK] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid4()),
    )
    
    # 所属租户（冗余存储，便于查询过滤）
    tenant_id: Mapped[str] = mapped_column(
        ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False, index=True,
    )
    
    # 所属知识库
    knowledge_base_id: Mapped[str] = mapped_column(
        ForeignKey("knowledge_bases.id", ondelete="CASCADE"), nullable=False, index=True,
    )
    
    # 关联的原始 Chunk ID（仅叶子节点有值）
    # 摘要节点此字段为 None
    chunk_id: Mapped[str | None] = mapped_column(
        ForeignKey("chunks.id", ondelete="CASCADE"), nullable=True, index=True,
    )

    # ==================== 节点内容 ====================
    # 节点文本内容（原始文本或摘要）
    text: Mapped[str] = mapped_column(Text, nullable=False)
    
    # 节点层级
    # 0 = 叶子节点（原始 Chunk）
    # 1, 2, 3... = 摘要层级（数字越大层级越高）
    level: Mapped[int] = mapped_column(Integer, nullable=False, default=0, index=True)
    
    # ==================== 树结构 ====================
    # 父节点 ID（根节点此字段为 None）
    parent_id: Mapped[str | None] = mapped_column(
        ForeignKey("raptor_nodes.id", ondelete="CASCADE"), nullable=True, index=True,
    )
    
    # 子节点 ID 列表（JSON 数组）
    # 叶子节点此字段为空数组 []
    children_ids: Mapped[list] = mapped_column(JSON, default=list)
    
    # ==================== 向量索引 ====================
    # 向量数据库中的 ID
    vector_id: Mapped[str | None] = mapped_column(String(128))
    
    # 索引状态：pending / indexing / indexed / failed
    indexing_status: Mapped[str] = mapped_column(String(20), default="pending", index=True)
    
    # 索引失败原因（可选）
    indexing_error: Mapped[str | None] = mapped_column(Text)
    
    # ==================== 元数据 ====================
    # 节点元数据（JSON 格式）
    # 可存储的信息示例：
    # {
    #     "cluster_id": 3,           # 所属聚类 ID
    #     "cluster_size": 5,         # 聚类中的节点数
    #     "summary_model": "qwen3",  # 生成摘要使用的模型
    #     "embedding_model": "bge-m3" # 使用的 embedding 模型
    # }
    extra_metadata: Mapped[dict | None] = mapped_column("metadata", JSON, default=dict)
