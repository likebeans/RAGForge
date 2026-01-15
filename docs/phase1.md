# Phase 1 开发问题记录与解决方案

## 1. 构建与依赖
- **问题**：`uv sync` 报错 “Multiple top-level packages discovered”。  
  **原因**：setuptools 自动发现拾取了 `app`/`sdk`/`alembic`。  
  **解决**：在 `pyproject.toml` 配置 `[tool.setuptools.packages.find]`，明确 `include=app,sdk`，`exclude=alembic,tests`。

## 2. 容器网络与端口
- **问题**：API 容器无法访问 Postgres/Qdrant，启动报 `ConnectionRefusedError`，健康检查无响应。  
  **原因**：`.env` 中写了宿主机地址（localhost:5435/6333），容器内无法访问；端口映射不一致（容器监听 8000，外部走 8020/8000 混用）。  
  **解决**：`.env` 改为 `DATABASE_URL=...@db:5432/kb`、`QDRANT_URL=http://qdrant:6333`；`docker-compose.yml` 改为 API 使用 `uvicorn --port 8020` 且映射 `8020:8020`，重启容器。

## 3. 数据模型/迁移不一致
- **问题**：文档入库 500，提示 `column "extra_metadata" ... does not exist`。  
  **原因**：模型字段名 `extra_metadata` 映射到列 `metadata`，初始迁移列名为 `metadata`。  
  **解决**：模型 `Document.extra_metadata`、`Chunk.extra_metadata` 显式 `mapped_column("metadata", JSON, ...)`，重建容器（或迁移）。

## 4. Qdrant 兼容与检索为空
- **问题**：检索返回空结果，或客户端版本不兼容日志。  
  **原因**：客户端 1.16.1 对服务端 1.9.0 报兼容告警；搜索异常被吞。  
  **解决**：锁定 `qdrant-client>=1.9,<1.10`，移除 `check_compatibility`，增加超时与错误输出，重启容器后检索恢复。

## 5. API Key 与鉴权
- **问题**：401 Unauthorized。  
  **原因**：使用的 Key 未写入数据库。  
  **解决**：在容器内生成 Key：  
  ```bash
  cat <<'PY' | docker compose exec -T api uv run python -
  import asyncio
  from app.db.session import SessionLocal, init_models
  from app.models import Tenant, APIKey
  from app.auth.api_key import generate_api_key
  from app.config import get_settings

  async def main():
      await init_models()
      async with SessionLocal() as s:
          tenant = Tenant(name="demo-tenant")
          s.add(tenant); await s.flush()
          display, hashed, prefix = generate_api_key(get_settings().api_key_prefix)
          s.add(APIKey(tenant_id=tenant.id, name="default", prefix=prefix, hashed_key=hashed, revoked=False))
          await s.commit()
          print("API_KEY", display)
  asyncio.run(main())
  PY
  ```

## 6. E2E 测试
- **问题**：测试 502/返回空结果。  
  **原因**：代理干扰/端口错误/检索空。  
  **解决**：测试客户端 `trust_env=False` 关闭代理；确保 `API_BASE=http://localhost:8020`；修复 Qdrant 后检索返回结果，`test/test_live_e2e.py` 通过。

## 7. Ingestion / Query 手工冒烟
- **问题**：`Invalid API key` / 404（kb_id 为空） / 502。  
  **原因**：临时环境变量未传入 curl（`Authorization: Bearer` 为空），或 URL 中 kb_id 拼接缺失。  
  **解决**：用 `sh -c` 确保变量生效，端口使用 8020。示例：
  ```bash
  # 创建 KB
  sh -c 'API_KEY=<your-key>; curl -s -H "Authorization: Bearer $API_KEY" \
    -H "Content-Type: application/json" \
    -d "{\"name\":\"kb_cli_ingest\"}" http://localhost:8020/v1/knowledge-bases'

  # 文档入库
  sh -c 'API_KEY=<your-key>; KB_ID=<上一步返回的id>; curl -s -H "Authorization: Bearer $API_KEY" \
    -H "Content-Type: application/json" \
    -d "{\"title\":\"hello\",\"content\":\"hello world\"}" \
    http://localhost:8020/v1/knowledge-bases/$KB_ID/documents'

  # 检索
  sh -c 'API_KEY=<your-key>; KB_ID=<同上>; curl -s -H "Authorization: Bearer $API_KEY" \
    -H "Content-Type: application/json" \
    -d "{\"query\":\"hello\",\"knowledge_base_ids\":[\"$KB_ID\"],\"top_k\":3}" \
    http://localhost:8020/v1/retrieve'
  ```
  - 如果返回 401/502，先确认容器的 API 端口映射 `8020:8020`，并确保 Key 有效且传入。检索应返回至少 1 条结果。

## 8. 基础认证（API Key）冒烟
- **问题**：401 / 422。  
  **原因**：使用的 Key 未落库，或 JSON 传参格式错误。  
  **解决与验证命令**（确保 API_BASE 指向 8020，使用有效 root Key）：  
  ```bash
  # 创建新 Key
  sh -c 'API_KEY=<root-key>; curl -s -H "Authorization: Bearer $API_KEY" \
    -H "Content-Type: application/json" \
    -d "{\"name\":\"tmp-key\"}" http://localhost:8020/v1/api-keys'

  # 列表
  sh -c 'API_KEY=<root-key>; curl -s -H "Authorization: Bearer $API_KEY" \
    http://localhost:8020/v1/api-keys'

  # 吊销
  sh -c 'API_KEY=<root-key>; KEY_ID=<目标key id>; curl -s -H "Authorization: Bearer $API_KEY" \
    -X POST http://localhost:8020/v1/api-keys/$KEY_ID/revoke'

  # 轮换
  sh -c 'API_KEY=<root-key>; KEY_ID=<目标key id>; curl -s -H "Authorization: Bearer $API_KEY" \
    -X POST http://localhost:8020/v1/api-keys/$KEY_ID/rotate'
  ```
  - 若出现 401，先确认 Key 写入数据库且 Bearer 头正常传入；422 通常是 JSON 未转义。

## 9. Python SDK 冒烟
- **问题**：验证 `KBClient.create_kb / add_document / query` 全链路。  
  **解决**：使用有效 API Key 与 API_BASE=8020，示例脚本：
  ```bash
  API_KEY=<root-key> API_BASE=http://localhost:8020 uv run python - <<'PY'
  import os, uuid
  from sdk.kb_client import KBClient

  client = KBClient(api_key=os.environ["API_KEY"], base_url=os.environ["API_BASE"])
  kb = client.create_kb(name=f"sdk-kb-{uuid.uuid4().hex[:8]}")
  doc = client.add_document(kb_id=kb["id"], title="hello", content="hello from sdk client")
  res = client.query(query="hello", knowledge_base_ids=[kb["id"]], top_k=3)
  print(kb, doc, res)
  client.close()
  PY
  ```
  - 期望：创建 KB 成功，文档入库 `chunk_count=1`，检索返回包含刚入库文本的结果。
