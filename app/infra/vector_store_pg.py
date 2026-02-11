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
    knowledge_base_id: str | None = None


class AsyncPgVectorStore:
    """
    PostgreSQL pgvector 异步向量存储
    
    特性：
    - 按知识库隔离表：每个 KB 独立一张表，支持不同维度
    - 动态维度：根据实际 embedding 维度自动创建/调整表
    - 多租户：通过 tenant_id 字段隔离
    - 连接池优化：使用 AsyncAdaptedQueuePool
    """
    
    # 表名前缀
    TABLE_PREFIX = "pgvec_kb_"
    
    def __init__(self):
        self._settings = get_settings()
        self._engine = None
        self._session_factory = None
        self._created_tables: set[str] = set()  # 已创建的表名缓存
    
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
    
    def _get_table_name(self, kb_id: str) -> str:
        """获取知识库对应的表名"""
        # 将 UUID 中的 - 替换为 _，确保是有效的表名
        safe_kb_id = kb_id.replace("-", "_")
        return f"{self.TABLE_PREFIX}{safe_kb_id}"
    
    async def _get_table_dim(self, session: AsyncSession, table_name: str) -> int | None:
        """获取现有表的向量维度"""
        try:
            result = await session.execute(text(f"""
                SELECT atttypmod
                FROM pg_attribute
                WHERE attrelid = '{table_name}'::regclass
                AND attname = 'embedding'
            """))
            row = result.fetchone()
            if row and row[0] > 0:
                return row[0]
        except Exception:
            pass
        return None
    
    async def _ensure_table(self, session: AsyncSession, table_name: str, dim: int) -> None:
        """确保向量表存在（按 KB 隔离），并处理维度变更"""
        if table_name in self._created_tables:
            return
        
        # 检查表是否存在
        result = await session.execute(text(f"""
            SELECT EXISTS (
                SELECT FROM information_schema.tables 
                WHERE table_name = '{table_name}'
            )
        """))
        table_exists = result.scalar()
        
        if not table_exists:
            # 创建新表（每个 KB 独立一张表）
            await session.execute(text(f"""
                CREATE TABLE {table_name} (
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
                CREATE INDEX IF NOT EXISTS idx_{table_name}_tenant 
                ON {table_name} (tenant_id)
            """))
            
            # 创建 HNSW 索引
            if dim <= 2000:
                await session.execute(text(f"""
                    CREATE INDEX IF NOT EXISTS idx_{table_name}_embedding 
                    ON {table_name} 
                    USING hnsw (embedding vector_cosine_ops) WITH (m = 16, ef_construction = 64)
                """))
                logger.info(f"创建向量表 {table_name}，维度={dim}，已创建 HNSW 索引 (vector)")
            elif dim <= 4000:
                await session.execute(text(f"""
                    CREATE INDEX IF NOT EXISTS idx_{table_name}_embedding 
                    ON {table_name} 
                    USING hnsw ((embedding::halfvec({dim})) halfvec_cosine_ops) WITH (m = 16, ef_construction = 64)
                """))
                logger.info(f"创建向量表 {table_name}，维度={dim}，已创建 HNSW 索引 (halfvec)")
            else:
                logger.warning(f"创建向量表 {table_name}，维度={dim}，维度超过 4000，跳过索引创建")
            
            await session.commit()
        else:
            # 检查现有表的维度
            existing_dim = await self._get_table_dim(session, table_name)
            if existing_dim and existing_dim != dim:
                # 检查表中是否有数据
                count_result = await session.execute(text(f"""
                    SELECT COUNT(*) FROM {table_name}
                """))
                row_count = count_result.scalar() or 0
                
                if row_count > 0:
                    # 表中有数据，不能改变维度
                    logger.error(
                        f"向量维度冲突: 知识库表 {table_name} 中已有 {row_count} 条 {existing_dim} 维向量，"
                        f"但当前 Embedding 模型生成 {dim} 维向量。"
                        f"请确保知识库配置的 Embedding 模型与已有数据一致。"
                    )
                    raise ValueError(
                        f"向量维度冲突: 该知识库已有 {existing_dim} 维向量，当前生成 {dim} 维。"
                        f"请在知识库配置中指定正确的 embedding 模型，或清空知识库后重新入库。"
                    )
                else:
                    # 表为空，可以安全地调整维度
                    logger.warning(f"向量维度变更: {existing_dim} -> {dim}，正在调整表结构...")
                    await session.execute(text(f"DROP INDEX IF EXISTS idx_{table_name}_embedding"))
                    await session.execute(text(f"""
                        ALTER TABLE {table_name} 
                        ALTER COLUMN embedding TYPE vector({dim})
                    """))
                    if dim <= 2000:
                        await session.execute(text(f"""
                            CREATE INDEX idx_{table_name}_embedding 
                            ON {table_name} 
                            USING hnsw (embedding vector_cosine_ops) WITH (m = 16, ef_construction = 64)
                        """))
                    elif dim <= 4000:
                        await session.execute(text(f"""
                            CREATE INDEX idx_{table_name}_embedding 
                            ON {table_name} 
                            USING hnsw ((embedding::halfvec({dim})) halfvec_cosine_ops) WITH (m = 16, ef_construction = 64)
                        """))
                    await session.commit()
                    logger.info(f"向量表维度已调整为 {dim}")
        
        self._created_tables.add(table_name)
    
    async def upsert_chunks(
        self,
        *,
        tenant_id: str,
        kb_id: str,
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
        
        # 获取实际维度和表名
        dim = len(embeddings[0])
        table_name = self._get_table_name(kb_id)
        
        async with self.session_factory() as session:
            try:
                await self._ensure_extension(session)
                await self._ensure_table(session, table_name, dim)
                
                # 批量 upsert
                for chunk, embedding in zip(chunks, embeddings):
                    metadata_json = json.dumps(chunk.get("metadata", {}), ensure_ascii=False)
                    embedding_str = "[" + ",".join(str(x) for x in embedding) + "]"
                    
                    await session.execute(text(f"""
                        INSERT INTO {table_name} 
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
                logger.info(f"pgvector 写入成功: 表={table_name}, {len(chunks)} chunks, dim={dim}")
                
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
        
        # 按 KB 分别查询并合并结果（每个 KB 可能有不同维度）
        all_records: list[VectorRecord] = []
        
        async with self.session_factory() as session:
            for kb_id in kb_ids:
                table_name = self._get_table_name(kb_id)
                
                # 检查表是否存在
                check_result = await session.execute(text(f"""
                    SELECT EXISTS (
                        SELECT FROM information_schema.tables 
                        WHERE table_name = '{table_name}'
                    )
                """))
                if not check_result.scalar():
                    continue  # 表不存在，跳过
                
                result = await session.execute(text(f"""
                    SELECT 
                        id, text, metadata, kb_id,
                        1 - (embedding <=> :embedding) as score
                    FROM {table_name}
                    WHERE tenant_id = :tenant_id
                    ORDER BY embedding <=> :embedding
                    LIMIT :top_k
                """), {
                    "embedding": embedding_str,
                    "tenant_id": tenant_id,
                    "top_k": top_k,
                })
                
                for row in result.fetchall():
                    metadata = row[2] if isinstance(row[2], dict) else json.loads(row[2] or "{}")
                    all_records.append(VectorRecord(
                        chunk_id=row[0],
                        text=row[1],
                        score=float(row[4]),
                        metadata=metadata,
                        knowledge_base_id=row[3],
                    ))
            
            # 按分数排序并取 top_k
            all_records.sort(key=lambda x: x.score, reverse=True)
            return all_records[:top_k]
    
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
                deleted = 0
                
                if kb_id:
                    # 删除指定 KB 的数据
                    table_name = self._get_table_name(kb_id)
                    
                    # 检查表是否存在
                    check_result = await session.execute(text(f"""
                        SELECT EXISTS (
                            SELECT FROM information_schema.tables 
                            WHERE table_name = '{table_name}'
                        )
                    """))
                    if check_result.scalar():
                        if chunk_ids:
                            ids_str = ",".join(f"'{cid}'" for cid in chunk_ids)
                            result = await session.execute(text(f"""
                                DELETE FROM {table_name}
                                WHERE tenant_id = :tenant_id AND id IN ({ids_str})
                            """), {"tenant_id": tenant_id})
                        else:
                            result = await session.execute(text(f"""
                                DELETE FROM {table_name}
                                WHERE tenant_id = :tenant_id
                            """), {"tenant_id": tenant_id})
                        deleted = result.rowcount
                else:
                    # 未指定 kb_id，需要遍历所有表（不推荐）
                    logger.warning("pgvector 删除: 未指定 kb_id，跳过删除")
                
                await session.commit()
                logger.info(f"pgvector 删除成功: {deleted} records")
                return deleted
                
            except Exception as e:
                await session.rollback()
                logger.error(f"pgvector 删除失败: {e}")
                raise
    
    async def upsert_vectors(
        self,
        *,
        tenant_id: str,
        knowledge_base_id: str,
        vectors: list[dict],
    ) -> int:
        """
        批量写入已有向量（不重新生成 embedding，用于 RAPTOR 等场景）
        
        Args:
            tenant_id: 租户 ID
            knowledge_base_id: 知识库 ID
            vectors: 向量列表，每个包含 {id, vector, payload}
            
        Returns:
            写入的向量数量
        """
        if not vectors:
            return 0
        
        # 获取维度和表名
        dim = len(vectors[0]["vector"])
        table_name = self._get_table_name(knowledge_base_id)
        
        async with self.session_factory() as session:
            try:
                await self._ensure_extension(session)
                await self._ensure_table(session, table_name, dim)
                
                count = 0
                for vec in vectors:
                    vec_id = vec["id"]
                    vector = vec["vector"]
                    payload = vec.get("payload", {})
                    
                    chunk_text = payload.get("text", "")
                    metadata_json = json.dumps(payload, ensure_ascii=False)
                    embedding_str = "[" + ",".join(str(x) for x in vector) + "]"
                    
                    await session.execute(text(f"""
                        INSERT INTO {table_name} 
                        (id, tenant_id, kb_id, text, embedding, metadata)
                        VALUES (:id, :tenant_id, :kb_id, :text, :embedding, :metadata)
                        ON CONFLICT (id) DO UPDATE SET
                            text = EXCLUDED.text,
                            embedding = EXCLUDED.embedding,
                            metadata = EXCLUDED.metadata
                    """), {
                        "id": str(vec_id),
                        "tenant_id": tenant_id,
                        "kb_id": knowledge_base_id,
                        "text": chunk_text,
                        "embedding": embedding_str,
                        "metadata": metadata_json,
                    })
                    count += 1
                
                await session.commit()
                logger.info(f"pgvector upsert_vectors 成功: 表={table_name}, {count} vectors, dim={dim}")
                return count
                
            except Exception as e:
                await session.rollback()
                logger.error(f"pgvector upsert_vectors 失败: {e}")
                raise


# 全局单例
_pg_vector_store: AsyncPgVectorStore | None = None


def get_pg_vector_store() -> AsyncPgVectorStore:
    """获取 pgvector 存储单例"""
    global _pg_vector_store
    if _pg_vector_store is None:
        _pg_vector_store = AsyncPgVectorStore()
    return _pg_vector_store
