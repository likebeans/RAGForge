"""
重建 BM25 索引脚本

用途：
    - 服务重启后从数据库重建 BM25 内存索引
    - 关闭/开启 BM25 后手动触发重建

用法示例：
    uv run python scripts/rebuild_bm25.py --tenant TENANT_ID
    uv run python scripts/rebuild_bm25.py --tenant TENANT_ID --kb KB_ID
"""

import argparse
import asyncio

from app.db.session import SessionLocal
from app.infra.bm25_store import bm25_store


async def main() -> None:
    parser = argparse.ArgumentParser(description="Rebuild BM25 index from database")
    parser.add_argument("--tenant", required=True, help="Tenant ID")
    parser.add_argument("--kb", help="Knowledge base ID (optional, rebuild specific KB)")
    args = parser.parse_args()

    if not bm25_store.enabled:
        print("BM25 is disabled by configuration (bm25_enabled=False). Nothing to rebuild.")
        return

    async with SessionLocal() as session:
        if args.kb:
            count = await bm25_store.rebuild_from_db(
                session=session,
                tenant_id=args.tenant,
                knowledge_base_id=args.kb,
            )
            print(f"Rebuilt BM25 for KB {args.kb}: {count} chunks")
        else:
            count = await bm25_store.rebuild_all(
                session=session,
                tenant_id=args.tenant,
            )
            print(f"Rebuilt BM25 for tenant {args.tenant}: {count} chunks")


if __name__ == "__main__":
    asyncio.run(main())
