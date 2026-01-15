# 安全基线

本文列出当前威胁模型、密钥与权限管理、审计与上报流程。

## 威胁模型与风险
- **多租户越权**：API Key scope_kb_ids、租户状态、文档 ACL/Security Trimming 必须生效。
- **凭证泄漏**：API Key、管理员 Token、模型 API Keys 存于环境变量；需轮换与最小暴露。
- **数据存储**：元数据在 PostgreSQL，向量与 ACL 在 Qdrant payload；BM25 为内存索引（多实例不共享）。
- **供应商调用**：LLM/Embedding/Rerank 调用外部服务，需合理超时/重试与审计。
- **DoS/滥用**：限流、请求体大小、并发控制、长耗时摄取任务。

## 身份与权限
- **管理员接口**：`/admin/*` 需 `X-Admin-Token`（强随机、仅后端/运维持有）。
- **API Key**：`app/auth/api_key.py` 校验哈希、过期、撤销、角色与 KB 白名单；`identity` 用于 ACL（user/roles/groups/clearance）。
- **ACL/Sensitivity**：文档 `sensitivity_level` + `acl_allow_users/roles/groups`；摄取时写入 chunk payload，检索时向量库过滤 + 应用层过滤。
- **租户隔离**：数据库层按 `tenant_id` 外键与索引；向量库按 collection/partition + payload 过滤。

## 密钥与配置管理

### 环境变量管理
- 使用 `.env`/环境变量注入，避免写入仓库；生产使用密钥管控（Vault/KMS/Secrets Manager）。
- Docker 镜像运行时应清理构建期代理/调试环境变量。
- 建议为 API Key 设置过期、定期轮换；管理员 Token 定期更换并限制可访问源 IP。

### 凭据管理器 (CredentialManager)

项目提供了完整的凭据管理系统（`app/security/credential_manager.py`），支持：

**核心功能**：
- **主备密钥机制**：每个提供商可配置主密钥和备用密钥
- **自动故障切换**：主密钥失效时自动切换到备用密钥
- **密钥轮换**：支持无缝轮换 API 密钥，旧主密钥自动降级为备用
- **密钥验证**：自动验证密钥格式（OpenAI sk-前缀、Gemini AIzaSy前缀等）
- **过期检测**：基于最后验证时间判断密钥是否需要轮换
- **审计日志**：记录所有密钥操作（轮换、切换、失效）

**配置示例**：
```bash
# 主密钥（从 .env 或环境变量）
OPENAI_API_KEY=sk-main-key
GEMINI_API_KEY=AIzaSy-main-key

# 备用密钥（环境变量，命名规则：{PROVIDER}_API_KEY_FALLBACK）
OPENAI_API_KEY_FALLBACK=sk-backup-key
GEMINI_API_KEY_FALLBACK=AIzaSy-backup-key
```

**使用示例**：
```python
from app.security.credential_manager import CredentialManager
from app.config import get_settings

settings = get_settings()
manager = CredentialManager(settings)

# 获取密钥（自动主备切换）
api_key = manager.get_api_key("openai")

# 轮换密钥
success = await manager.rotate_key("openai", "new-key-value")

# 标记密钥失效（触发自动切换）
manager.mark_key_invalid("openai")

# 检查密钥状态
status = manager.get_key_status("openai")  # ACTIVE/FALLBACK/EXPIRED/INVALID
```

**密钥状态枚举**：
- `ACTIVE`: 主密钥活跃可用
- `FALLBACK`: 使用备用密钥
- `EXPIRED`: 密钥已过期需轮换
- `INVALID`: 密钥无效

### 凭据扫描 (CredentialScanner)

自动检测代码中的硬编码凭据和敏感信息（`app/security/credential_scanner.py`）：

**检测模式**：
- 硬编码 API 密钥（通用模式）
- Google Gemini API 密钥（AIzaSy 前缀）
- OpenAI API 密钥（sk- 前缀）
- 通义千问 API 密钥
- 通用密钥/密码/令牌
- 弱管理员令牌（test/demo/12345 等）
- 内网 IP 地址（192.168.x.x、10.x.x.x、172.16-31.x.x）

**Pre-commit 钩子集成**：
```bash
# 安装 pre-commit
pip install pre-commit
pre-commit install

# 手动运行扫描
python scripts/pre-commit-security-check.py --all

# 生成基线文件（白名单已知的安全例外）
python scripts/pre-commit-security-check.py --all --generate-baseline
```

**配置文件**：`.pre-commit-config.yaml` 包含：
- 通用代码质量检查（trailing-whitespace、check-yaml 等）
- Python 代码格式化（ruff）
- 凭据检测（detect-secrets + 自定义扫描器）

**白名单机制**：
- 基线文件：`.secrets.baseline`（JSON 格式）
- 记录已知的安全例外（如测试文件中的占位符）
- 扫描时自动跳过白名单中的检测结果

### 安全令牌生成

使用加密安全的随机生成器：
```python
from app.security.credential_manager import CredentialManager

# 生成管理员令牌（32字节 = 43字符 base64）
admin_token = CredentialManager.generate_secure_token(length=32)

# 生成 API 密钥（64字节 = 86字符 base64）
api_key = CredentialManager.generate_secure_token(length=64)
```

**注意**：
- 使用 `secrets.token_urlsafe()` 而非 `random`
- 生产环境管理员令牌至少 32 字节
- 避免使用弱令牌（test、demo、12345 等）

## 审计与可观测
- **审计日志**：`AuditLogMiddleware` 记录检索/RAG/KB/文档关键操作，落库（状态码、耗时、IP、UA、tenant/api_key）。
- **结构化日志**：`app/infra/logging.py` JSON/控制台格式，支持 request_id；建议补充 tenant_id 透传。
- **指标**：`/metrics` 返回运行时与调用/检索统计；推荐接入 Prometheus/OpenTelemetry 统一采集。
- **慢查询/错误**：外部调用统一经 `metrics.track_call` 记录；需对异常堆栈与关键参数做采样日志。

## 安全基线与加固建议
- CORS 在生产环境收敛到受信任域；开启 HTTPS（LB/Ingress）。
- API 速率限制与请求体大小限制（上传/摄取接口需额外约束）。
- 模型/向量/数据库调用设置超时、重试、熔断，避免阻塞事件循环。
- 向量库 ACL 下推（Qdrant Filter）+ 应用层二次过滤，避免敏感文本泄露。
- 替换 BM25 内存索引为可持久/多实例方案（ES/OpenSearch）；或启动时从 DB 回填。
- 依赖与密钥扫描：在 CI 运行 `pip-audit`/`safety` 与 `gitleaks`。
- **凭据管理**：使用 CredentialManager 管理 API 密钥，配置主备密钥实现故障切换。
- **Pre-commit 钩子**：启用凭据扫描，防止硬编码密钥提交到版本控制。
- **环境隔离**：生产环境密钥存储在 `.env.local` 或密钥管理服务，不提交到仓库。
- **管理员令牌**：使用加密安全的随机生成器，至少 32 字节，避免弱令牌。

## 漏洞上报
- 请通过私有渠道（安全邮箱/企业 IM/工单）提交，避免公开 Issue。
- 报告内容：问题描述、复现步骤、影响面、是否有已知利用方式。
- 我们将在 24-48 小时内确认并协商修复与披露窗口。

