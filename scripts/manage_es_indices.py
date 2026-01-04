"""
ES/OpenSearch 索引管理工具

功能：
- 列出索引及 shard/replica
- 删除指定索引（支持通配）
- 查看/调整 refresh 设置

用法示例：
    uv run python scripts/manage_es_indices.py list
    uv run python scripts/manage_es_indices.py delete --pattern "kb_*_old"
    uv run python scripts/manage_es_indices.py refresh --index kb_shared --value false
"""

import argparse
import asyncio

from app.infra.bm25_es import ElasticBM25Store


async def cmd_list(store: ElasticBM25Store):
    client = store.client
    indices = await client.indices.get(index=f"{store.index_prefix}*")
    for name, info in indices.items():
        settings = info.get("settings", {}).get("index", {})
        shards = settings.get("number_of_shards")
        replicas = settings.get("number_of_replicas")
        refresh = settings.get("refresh_interval")
        print(f"{name}: shards={shards}, replicas={replicas}, refresh={refresh}")


async def cmd_delete(store: ElasticBM25Store, pattern: str):
    client = store.client
    await client.indices.delete(index=pattern, ignore_unavailable=True)
    print(f"Deleted indices matching {pattern}")


async def cmd_refresh(store: ElasticBM25Store, index: str, value: str):
    client = store.client
    await client.indices.put_settings(index=index, settings={"index": {"refresh_interval": value}})
    print(f"Set refresh_interval={value} for {index}")


async def main():
    parser = argparse.ArgumentParser(description="Manage ES/OpenSearch indices")
    subparsers = parser.add_subparsers(dest="cmd", required=True)

    p_list = subparsers.add_parser("list", help="List indices")

    p_del = subparsers.add_parser("delete", help="Delete indices by pattern")
    p_del.add_argument("--pattern", required=True, help="Index pattern to delete")

    p_ref = subparsers.add_parser("refresh", help="Set refresh interval")
    p_ref.add_argument("--index", required=True, help="Index name")
    p_ref.add_argument("--value", required=True, help="Refresh interval value")

    args = parser.parse_args()

    store = ElasticBM25Store()

    if args.cmd == "list":
        await cmd_list(store)
    elif args.cmd == "delete":
        await cmd_delete(store, args.pattern)
    elif args.cmd == "refresh":
        await cmd_refresh(store, args.index, args.value)


if __name__ == "__main__":
    asyncio.run(main())
