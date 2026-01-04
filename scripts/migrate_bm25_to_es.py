"""
将数据库中的 chunks 迁移到 BM25 后端（memory 或 ES/OpenSearch）

用法：
    uv run python scripts/migrate_bm25_to_es.py --tenant TENANT_ID [--kb KB_ID] --backend es
    # watch 模式：持续扫描 DB 追加写入（简易双写）
    uv run python scripts/migrate_bm25_to_es.py --tenant TENANT_ID --backend es --watch --interval 10
"""

import argparse
import asyncio
import time
from typing import Optional

from sqlalchemy import select

from app.db.session import SessionLocal
from app.infra.bm25_store import BM25Facade
from app.models import Chunk


async def migrate_once(
    tenant_id: str,
    kb_id: Optional[str],
    backend: BM25Facade,
    limit: Optional[int] = None,
) -> int:
    """从 DB 读取 chunks 写入 BM25 后端"""
    async with SessionLocal() as session:
        stmt = select(Chunk).where(Chunk.tenant_id == tenant_id)
        if kb_id:
            stmt = stmt.where(Chunk.knowledge_base_id == kb_id)
        if limit:
            stmt = stmt.limit(limit)
        result = await session.execute(stmt)
        rows = result.scalars().all()
        payload = [
            {
                "chunk_id": c.id,
                "text": c.text,
                "metadata": c.extra_metadata or {},
                "knowledge_base_id": c.knowledge_base_id,
            }
            for c in rows
        ]
        # 按 KB 分组写入
        grouped: dict[str, list[dict]] = {}
        for item in payload:
            grouped.setdefault(item["knowledge_base_id"], []).append(item)
        total = 0
        for kb, items in grouped.items():
            await backend.upsert_chunks(tenant_id=tenant_id, knowledge_base_id=kb, chunks=items)
            total += len(items)
        return total


async def main() -> None:
    parser = argparse.ArgumentParser(description="Migrate BM25 chunks to backend")
    parser.add_argument("--tenant", required=True, help="Tenant ID")
    parser.add_argument("--kb", help="Knowledge base ID (optional)")
    parser.add_argument("--backend", default="es", choices=["es", "memory"], help="Target backend")
    parser.add_argument("--limit", type=int, help="Limit chunks")
    parser.add_argument("--watch", action="store_true", help="Enable watch loop (pseudo dual-write)")
    parser.add_argument("--interval", type=int, default=30, help="Watch interval seconds")
    args = parser.parse_args()

    bm25 = BM25Facade()
    bm25.enabled = True
    bm25.backend_name = args.backend
    # 强制选择后端
    if args.backend == "es":
        from app.infra.bm25_es import ElasticBM25Store

        bm25.backend = ElasticBM25Store()
    else:
        from app.infra.bm25_store import InMemoryBM25Store

        bm25.backend = InMemoryBM25Store()

    def log(msg: str):
        print(f"[{time.strftime('%Y-%m-%d %H:%M:%S')}] {msg}")

    async def run_once():
        count = await migrate_once(args.tenant, args.kb, bm25, args.limit)
        log(f"Migrated {count} chunks to backend={args.backend}")

    await run_once()
    if args.watch:
        while True:
            await asyncio.sleep(args.interval)
            await run_once()


if __name__ == "__main__":
    asyncio.run(main())
