"""
PostgreSQL pgvector 向量存储实现

支持：
- 动态向量维度（根据 embedding 自动适配）
- 多租户隔离（通过 tenant_id 字段）
- 批量操作（upsert_chunks）
- 相似度搜索（cosine similarity）
"""

import json
import logging
from dataclasses import dataclass
from typing import Any

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker
from sqlalchemy.pool import AsyncAdaptedQueuePool

from app.config import get_settings
from app.infra.embeddings import get_embeddings_with_config, get_embedding_with_config

logger = logging.getLogger(__name__)


@dataclass
class VectorRecord:
    """向量记录"""
    chunk_id: str
    text: str
    score: float
    metadata: dict


class AsyncPgVectorStore:
    """
    PostgreSQL pgvector 异步向量存储
    
    特性：
    - 动态维度：根据实际 embedding 维度自动创建/调整表
    - 多租户：通过 tenant_id 字段隔离
    - 连接池优化：使用 AsyncAdaptedQueuePool
    """
    
    # 默认表名
    DEFAULT_TABLE = "vector_chunks"
    
    def __init__(self, table_name: str | None = None):
        self._settings = get_settings()
        self._table_name = table_name or self.DEFAULT_TABLE
        self._engine = None
        self._session_factory = None
        self._table_created = False
        self._current_dim: int | None = None  # 当前表的向量维度
    
    @property
    def engine(self):
        if self._engine is None:
            self._engine = create_async_engine(
                self._settings.database_url,
                poolclass=AsyncAdaptedQueuePool,
                pool_size=50,
                max_overflow=50,
                pool_recycle=3600,
                connect_args={
                    "server_settings": {
                        "application_name": "ragforge-pgvector"
                    }
                }
            )
        return self._engine
    
    @property
    def session_factory(self):
        if self._session_factory is None:
            self._session_factory = async_sessionmaker(
                self.engine, 
                class_=AsyncSession,
                expire_on_commit=False
            )
        return self._session_factory
    
    async def _ensure_extension(self, session: AsyncSession) -> None:
        """确保 pgvector 扩展已安装"""
        await session.execute(text("CREATE EXTENSION IF NOT EXISTS vector"))
        await session.commit()
    
    async def _get_table_dim(self, session: AsyncSession) -> int | None:
        """获取当前表的向量维度"""
        try:
            result = await session.execute(text(f"""
                SELECT atttypmod 
                FROM pg_attribute 
                WHERE attrelid = '{self._table_name}'::regclass 
                AND attname = 'embedding'
            """))
            row = result.fetchone()
            if row and row[0] > 0:
                return row[0]
        except Exception:
            pass
        return None
    
    async def _ensure_table(self, session: AsyncSession, dim: int) -> None:
        """
        确保向量表存在，支持动态维度调整
        
        Args:
            session: 数据库会话
            dim: 向量维度
        """
        if self._table_created and self._current_dim == dim:
            return
        
        # 检查表是否存在
        result = await session.execute(text(f"""
            SELECT EXISTS (
                SELECT FROM information_schema.tables 
                WHERE table_name = '{self._table_name}'
            )
        """))
        table_exists = result.scalar()
        
        if not table_exists:
            # 创建新表
            await session.execute(text(f"""
                CREATE TABLE {self._table_name} (
                    id VARCHAR(255) PRIMARY KEY,
                    tenant_id VARCHAR(255) NOT NULL,
                    kb_id VARCHAR(255) NOT NULL,
                    text TEXT NOT NULL,
                    embedding vector({dim}),
                    metadata JSONB,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """))
            # 创建索引
            await session.execute(text(f"""
                CREATE INDEX IF NOT EXISTS idx_{self._table_name}_tenant_kb 
                ON {self._table_name} (tenant_id, kb_id)
            """))
            
            # 创建 HNSW 索引
            # - vector: 最多 2000 维度，使用 vector_cosine_ops
            # - halfvec: 最多 4000 维度，使用 halfvec_cosine_ops（需要转换类型）
            # 参考: https://supabase.com/docs/guides/ai/vector-indexes/hnsw-indexes
            if dim <= 2000:
                await session.execute(text(f"""
                    CREATE INDEX IF NOT EXISTS idx_{self._table_name}_embedding 
                    ON {self._table_name} 
                    USING hnsw (embedding vector_cosine_ops) WITH (m = 16, ef_construction = 64)
                """))
                logger.info(f"创建向量表 {self._table_name}，维度={dim}，已创建 HNSW 索引 (vector)")
            elif dim <= 4000:
                # 高维度向量使用 halfvec 类型创建索引
                await session.execute(text(f"""
                    CREATE INDEX IF NOT EXISTS idx_{self._table_name}_embedding 
                    ON {self._table_name} 
                    USING hnsw ((embedding::halfvec({dim})) halfvec_cosine_ops) WITH (m = 16, ef_construction = 64)
                """))
                logger.info(f"创建向量表 {self._table_name}，维度={dim}，已创建 HNSW 索引 (halfvec)")
            else:
                logger.warning(f"创建向量表 {self._table_name}，维度={dim}，维度超过 4000，跳过索引创建")
            
            await session.commit()
        else:
            # 检查现有表的维度
            existing_dim = await self._get_table_dim(session)
            if existing_dim and existing_dim != dim:
                logger.warning(f"向量维度变更: {existing_dim} -> {dim}，正在调整表结构...")
                # 删除旧索引
                await session.execute(text(f"""
                    DROP INDEX IF EXISTS idx_{self._table_name}_embedding
                """))
                # 修改列维度
                await session.execute(text(f"""
                    ALTER TABLE {self._table_name} 
                    ALTER COLUMN embedding TYPE vector({dim})
                """))
                # 重建 HNSW 索引
                if dim <= 2000:
                    await session.execute(text(f"""
                        CREATE INDEX idx_{self._table_name}_embedding 
                        ON {self._table_name} 
                        USING hnsw (embedding vector_cosine_ops) WITH (m = 16, ef_construction = 64)
                    """))
                elif dim <= 4000:
                    await session.execute(text(f"""
                        CREATE INDEX idx_{self._table_name}_embedding 
                        ON {self._table_name} 
                        USING hnsw ((embedding::halfvec({dim})) halfvec_cosine_ops) WITH (m = 16, ef_construction = 64)
                    """))
                await session.commit()
                logger.info(f"向量表维度已调整为 {dim}")
        
        self._table_created = True
        self._current_dim = dim
    
    async def upsert_chunks(
        self,
        *,
        tenant_id: str,
        chunks: list[dict],
        embedding_config: dict | None = None,
    ) -> None:
        """
        批量写入 chunks
        
        Args:
            tenant_id: 租户 ID
            chunks: chunk 列表，每个包含 chunk_id, kb_id, text, metadata
            embedding_config: embedding 配置 {provider, model, api_key, base_url}
        """
        if not chunks:
            return
        
        # 提取文本并生成 embeddings
        texts = [c["text"] for c in chunks]
        embeddings = await get_embeddings_with_config(texts, embedding_config)
        
        if not embeddings or len(embeddings) == 0:
            raise ValueError("无法生成 embeddings")
        
        # 获取实际维度
        dim = len(embeddings[0])
        
        async with self.session_factory() as session:
            try:
                await self._ensure_extension(session)
                await self._ensure_table(session, dim)
                
                # 批量 upsert
                for chunk, embedding in zip(chunks, embeddings):
                    metadata_json = json.dumps(chunk.get("metadata", {}), ensure_ascii=False)
                    embedding_str = "[" + ",".join(str(x) for x in embedding) + "]"
                    
                    # 兼容两种字段名: kb_id 或 knowledge_base_id
                    kb_id = chunk.get("kb_id") or chunk.get("knowledge_base_id")
                    
                    await session.execute(text(f"""
                        INSERT INTO {self._table_name} 
                        (id, tenant_id, kb_id, text, embedding, metadata)
                        VALUES (:id, :tenant_id, :kb_id, :text, :embedding, :metadata)
                        ON CONFLICT (id) DO UPDATE SET
                            text = EXCLUDED.text,
                            embedding = EXCLUDED.embedding,
                            metadata = EXCLUDED.metadata
                    """), {
                        "id": chunk["chunk_id"],
                        "tenant_id": tenant_id,
                        "kb_id": kb_id,
                        "text": chunk["text"],
                        "embedding": embedding_str,
                        "metadata": metadata_json,
                    })
                
                await session.commit()
                logger.info(f"pgvector 写入成功: {len(chunks)} chunks, dim={dim}")
                
            except Exception as e:
                await session.rollback()
                logger.error(f"pgvector 写入失败: {e}")
                raise
    
    async def search(
        self,
        *,
        query: str,
        tenant_id: str,
        kb_ids: list[str],
        top_k: int = 10,
        embedding_config: dict | None = None,
    ) -> list[VectorRecord]:
        """
        相似度搜索
        
        Args:
            query: 查询文本
            tenant_id: 租户 ID
            kb_ids: 知识库 ID 列表
            top_k: 返回数量
            embedding_config: embedding 配置
            
        Returns:
            VectorRecord 列表（按相似度降序）
        """
        # 生成查询向量
        query_embedding = await get_embedding_with_config(query, embedding_config)
        if not query_embedding:
            raise ValueError("无法生成查询 embedding")
        
        embedding_str = "[" + ",".join(str(x) for x in query_embedding) + "]"
        kb_ids_str = ",".join(f"'{kb_id}'" for kb_id in kb_ids)
        
        async with self.session_factory() as session:
            result = await session.execute(text(f"""
                SELECT 
                    id, text, metadata,
                    1 - (embedding <=> :embedding) as score
                FROM {self._table_name}
                WHERE tenant_id = :tenant_id 
                AND kb_id IN ({kb_ids_str})
                ORDER BY embedding <=> :embedding
                LIMIT :top_k
            """), {
                "embedding": embedding_str,
                "tenant_id": tenant_id,
                "top_k": top_k,
            })
            
            records = []
            for row in result.fetchall():
                metadata = row[2] if isinstance(row[2], dict) else json.loads(row[2] or "{}")
                records.append(VectorRecord(
                    chunk_id=row[0],
                    text=row[1],
                    score=float(row[3]),
                    metadata=metadata,
                ))
            
            return records
    
    async def delete(
        self,
        *,
        tenant_id: str,
        kb_id: str | None = None,
        chunk_ids: list[str] | None = None,
    ) -> int:
        """
        删除向量
        
        Args:
            tenant_id: 租户 ID
            kb_id: 知识库 ID（可选，删除整个 KB）
            chunk_ids: chunk ID 列表（可选，删除特定 chunks）
            
        Returns:
            删除的记录数
        """
        async with self.session_factory() as session:
            try:
                if chunk_ids:
                    ids_str = ",".join(f"'{cid}'" for cid in chunk_ids)
                    result = await session.execute(text(f"""
                        DELETE FROM {self._table_name}
                        WHERE tenant_id = :tenant_id AND id IN ({ids_str})
                    """), {"tenant_id": tenant_id})
                elif kb_id:
                    result = await session.execute(text(f"""
                        DELETE FROM {self._table_name}
                        WHERE tenant_id = :tenant_id AND kb_id = :kb_id
                    """), {"tenant_id": tenant_id, "kb_id": kb_id})
                else:
                    result = await session.execute(text(f"""
                        DELETE FROM {self._table_name}
                        WHERE tenant_id = :tenant_id
                    """), {"tenant_id": tenant_id})
                
                await session.commit()
                deleted = result.rowcount
                logger.info(f"pgvector 删除成功: {deleted} records")
                return deleted
                
            except Exception as e:
                await session.rollback()
                logger.error(f"pgvector 删除失败: {e}")
                raise


# 全局单例
_pg_vector_store: AsyncPgVectorStore | None = None


def get_pg_vector_store() -> AsyncPgVectorStore:
    """获取 pgvector 存储单例"""
    global _pg_vector_store
    if _pg_vector_store is None:
        _pg_vector_store = AsyncPgVectorStore()
    return _pg_vector_store
