# 安全运维指南

本文档详细描述 Self-RAG Pipeline 的安全基线、威胁模型、权限管理和安全加固措施。

## 威胁模型与风险评估

### 主要威胁

| 威胁类型 | 风险等级 | 描述 | 缓解措施 |
|---------|---------|------|---------|
| **多租户越权** | 🔴 高 | API Key scope_kb_ids、租户状态、文档 ACL 绕过 | 多层权限校验、Security Trimming |
| **凭证泄漏** | 🔴 高 | API Key、管理员 Token、模型 API Keys 泄露 | 密钥轮换、最小暴露原则 |
| **数据泄露** | 🟠 中 | 敏感文档通过检索接口泄露 | ACL 过滤、审计日志 |
| **供应商风险** | 🟡 低 | LLM/Embedding 服务调用外部 API | 超时控制、审计记录 |
| **DoS 攻击** | 🟡 低 | 大量请求导致服务不可用 | 限流、请求体大小限制 |

### 数据存储安全

- **元数据**：存储在 PostgreSQL，包含租户隔离和访问控制
- **向量数据**：存储在 Qdrant，包含 ACL 信息在 payload 中
- **BM25 索引**：内存存储，多实例不共享（需要持久化改进）
- **审计日志**：完整记录所有关键操作和访问

## 身份认证与授权

### 管理员接口认证

- **认证方式**：`X-Admin-Token` 头部认证
- **Token 要求**：强随机生成，至少 32 字节
- **访问范围**：仅限 `/admin/*` 接口
- **安全建议**：
  - 定期轮换管理员 Token
  - 限制可访问的源 IP 地址
  - 仅后端/运维人员持有

### API Key 管理

API Key 认证通过 `app/auth/api_key.py` 实现：

- **存储方式**：SHA256 哈希存储，不保存明文
- **过期机制**：支持设置过期时间
- **撤销机制**：支持主动撤销无效 Key
- **角色权限**：admin/write/read 三级权限
- **KB 白名单**：`scope_kb_ids` 限制可访问的知识库

#### API Key 角色权限

| 角色 | 权限范围 |
|------|---------|
| `admin` | 全部权限 + 管理 API Key |
| `write` | 创建/删除 KB、上传文档、检索 |
| `read` | 仅检索和列表查询 |

#### Identity 字段用于 ACL

API Key 的 `identity` 字段用于文档级访问控制：

```json
{
  "user": "john.doe",
  "roles": ["engineer", "manager"],
  "groups": ["dev-team", "product-team"],
  "clearance": "confidential"
}
```

### 文档级访问控制 (ACL)

#### 敏感度级别

文档支持设置敏感度级别：
- `public`: 公开文档，所有用户可访问
- `internal`: 内部文档，需要认证
- `confidential`: 机密文档，需要特定权限
- `secret`: 秘密文档，最高权限

#### ACL 白名单

文档可设置以下 ACL 字段：
- `acl_allow_users`: 允许访问的用户列表
- `acl_allow_roles`: 允许访问的角色列表
- `acl_allow_groups`: 允许访问的组列表

#### Security Trimming 实现

1. **摄取阶段**：将 `sensitivity_level` 和 `acl_*` 字段写入 chunk payload
2. **检索阶段**：
   - 向量库层面过滤（Qdrant Filter）
   - 应用层二次过滤（`filter_results_by_acl`）
   - 完全过滤时返回 403 `NO_PERMISSION`

### 租户隔离

#### 数据库层隔离

- 所有数据表包含 `tenant_id` 字段
- 外键约束确保数据完整性
- 查询时强制过滤 `tenant_id`

#### 向量库隔离

支持三种隔离策略：

| 模式 | Collection 名称 | 隔离方式 | 适用场景 |
|------|----------------|---------|---------|
| **Partition** | `kb_shared` | 通过 `kb_id` 字段过滤 | 小规模、资源共享 |
| **Collection** | `kb_{tenant_id}` | 每租户独立 Collection | 大规模、高性能需求 |
| **Auto** | 自动选择 | 根据数据量自动切换 | 自动优化 |

## 密钥与凭据管理

### 凭据管理器 (CredentialManager)

项目提供完整的凭据管理系统，支持：

#### 核心功能

- **主备密钥机制**：每个提供商可配置主密钥和备用密钥
- **自动故障切换**：主密钥失效时自动切换到备用密钥
- **密钥轮换**：支持无缝轮换 API 密钥
- **密钥验证**：自动验证密钥格式
- **过期检测**：基于最后验证时间判断密钥状态
- **审计日志**：记录所有密钥操作

#### 配置示例

```bash
# 主密钥（从 .env 或环境变量）
OPENAI_API_KEY=sk-main-key
GEMINI_API_KEY=AIzaSy-main-key

# 备用密钥（环境变量，命名规则：{PROVIDER}_API_KEY_FALLBACK）
OPENAI_API_KEY_FALLBACK=sk-backup-key
GEMINI_API_KEY_FALLBACK=AIzaSy-backup-key
```

#### 使用示例

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

#### 密钥状态枚举

- `ACTIVE`: 主密钥活跃可用
- `FALLBACK`: 使用备用密钥
- `EXPIRED`: 密钥已过期需轮换
- `INVALID`: 密钥无效

### 凭据扫描 (CredentialScanner)

自动检测代码中的硬编码凭据和敏感信息：

#### 检测模式

- 硬编码 API 密钥（通用模式）
- Google Gemini API 密钥（AIzaSy 前缀）
- OpenAI API 密钥（sk- 前缀）
- 通义千问 API 密钥
- 通用密钥/密码/令牌
- 弱管理员令牌（test/demo/12345 等）
- 内网 IP 地址（192.168.x.x、10.x.x.x、172.16-31.x.x）

#### Pre-commit 钩子集成

```bash
# 安装 pre-commit
pip install pre-commit
pre-commit install

# 手动运行扫描
python scripts/pre-commit-security-check.py --all

# 生成基线文件（白名单已知的安全例外）
python scripts/pre-commit-security-check.py --all --generate-baseline
```

#### 配置文件

`.pre-commit-config.yaml` 包含：
- 通用代码质量检查（trailing-whitespace、check-yaml 等）
- Python 代码格式化（ruff）
- 凭据检测（detect-secrets + 自定义扫描器）

#### 白名单机制

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

**安全要求**：
- 使用 `secrets.token_urlsafe()` 而非 `random`
- 生产环境管理员令牌至少 32 字节
- 避免使用弱令牌（test、demo、12345 等）

### 环境变量管理

#### 最佳实践

- 使用 `.env`/环境变量注入，避免写入仓库
- 生产使用密钥管控（Vault/KMS/Secrets Manager）
- Docker 镜像运行时应清理构建期代理/调试环境变量
- 为 API Key 设置过期、定期轮换

#### 环境隔离

- 开发环境：`.env.local`（不提交到版本控制）
- 测试环境：使用测试专用密钥
- 生产环境：使用密钥管理服务

## 审计与可观测性

### 审计日志

`AuditLogMiddleware` 记录关键操作：

- **记录范围**：检索/RAG/KB/文档关键操作
- **记录内容**：状态码、耗时、IP、UA、tenant/api_key
- **存储方式**：落库持久化
- **查询接口**：支持按租户、时间范围查询

### 结构化日志

`app/infra/logging.py` 提供统一日志格式：

- **格式**：JSON/控制台格式可选
- **字段**：timestamp、level、logger、message、request_id
- **建议**：补充 tenant_id 透传

### 系统指标

`/metrics` 端点返回运行时统计：

```json
{
  "service": {
    "uptime_seconds": 3600.5,
    "uptime_human": "1h 0m 0s"
  },
  "config": {
    "llm_provider": "ollama",
    "embedding_provider": "ollama"
  },
  "stats": {
    "calls": {
      "llm:ollama": {"count": 150, "avg_latency_ms": 1200}
    },
    "retrievals": {
      "hybrid": {"count": 200}
    }
  }
}
```

### 监控建议

- 接入 Prometheus/OpenTelemetry 统一采集
- 对异常堆栈与关键参数做采样日志
- 设置慢查询/错误告警阈值

## 网络安全

### HTTPS 配置

生产环境必须启用 HTTPS：

```nginx
server {
    listen 443 ssl;
    server_name api.example.com;
    
    ssl_certificate /etc/ssl/certs/api.crt;
    ssl_certificate_key /etc/ssl/private/api.key;
    
    # 安全头部
    add_header Strict-Transport-Security "max-age=31536000; includeSubDomains" always;
    add_header X-Content-Type-Options nosniff;
    add_header X-Frame-Options DENY;
    add_header X-XSS-Protection "1; mode=block";
    
    location / {
        proxy_pass http://localhost:8020;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Request-ID $request_id;
    }
}
```

### CORS 配置

生产环境收敛到受信任域：

```python
# app/main.py
app.add_middleware(
    CORSMiddleware,
    allow_origins=["https://trusted-domain.com"],  # 生产环境限制域名
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE"],
    allow_headers=["*"],
)
```

### 网络隔离

- 数据库和向量库不暴露公网端口
- API 服务仅通过反向代理访问
- 使用 Docker 网络或 K8s NetworkPolicy 隔离

## 安全加固措施

### API 安全

#### 限流控制

- **默认限流**：120 次/分钟
- **Redis 限流**：支持集群部署
- **自定义限流**：可按 API Key 独立配置

```python
# Redis 限流配置
REDIS_URL=redis://localhost:6379/0
RATE_LIMIT_STORAGE=redis  # 或 memory
```

#### 请求体大小限制

```python
# 上传/摄取接口额外约束
MAX_CONTENT_LENGTH = 50 * 1024 * 1024  # 50MB
MAX_BATCH_SIZE = 50  # 批量上传最多50个文档
```

#### 超时控制

```python
# 模型/向量/数据库调用超时设置
LLM_TIMEOUT = 30  # 秒
EMBEDDING_TIMEOUT = 10  # 秒
QDRANT_TIMEOUT = 5  # 秒
```

### 数据安全

#### 向量库 ACL 下推

将 ACL 过滤下推到 Qdrant Filter，避免敏感文本泄露：

```python
# Qdrant 查询时附加 ACL Filter
filter_conditions = {
    "must": [
        {"key": "tenant_id", "match": {"value": tenant_id}},
        {"key": "sensitivity_level", "match": {"any": allowed_levels}},
    ]
}
```

#### BM25 索引持久化

当前 BM25 为内存索引，建议改进：
- 替换为 ES/OpenSearch 持久化方案
- 或启动时从 DB 回填索引

### 依赖安全

#### 依赖扫描

在 CI 中运行安全扫描：

```bash
# Python 依赖漏洞扫描
pip install pip-audit safety
pip-audit
safety check

# 密钥泄露扫描
pip install gitleaks
gitleaks detect --source . --verbose
```

#### 依赖更新

- 定期更新依赖包到最新安全版本
- 使用 `uv` 管理依赖锁定版本
- 监控安全公告和 CVE 通知

## 安全检查清单

### 部署前检查

- [ ] 管理员 Token 使用强随机生成（至少32字节）
- [ ] 生产环境密钥存储在密钥管理服务
- [ ] HTTPS 证书配置正确
- [ ] CORS 限制到受信任域名
- [ ] 数据库和向量库网络隔离
- [ ] 限流和超时配置合理
- [ ] 审计日志正常记录

### 运行时监控

- [ ] API Key 使用情况监控
- [ ] 异常访问模式检测
- [ ] 敏感文档访问审计
- [ ] 系统资源使用监控
- [ ] 错误率和延迟监控

### 定期维护

- [ ] 管理员 Token 定期轮换
- [ ] API Key 过期清理
- [ ] 审计日志定期归档
- [ ] 依赖包安全更新
- [ ] 安全配置审查

## 漏洞响应

### 上报流程

1. **私有渠道**：通过安全邮箱/企业 IM/工单提交，避免公开 Issue
2. **报告内容**：
   - 问题描述和影响范围
   - 详细复现步骤
   - 是否有已知利用方式
   - 建议修复方案

### 响应时间

- **确认响应**：24-48 小时内确认收到
- **初步评估**：3-5 个工作日内完成风险评估
- **修复计划**：根据严重程度制定修复时间表
- **披露协调**：与报告者协商披露窗口

### 严重程度分级

| 级别 | 描述 | 响应时间 |
|------|------|---------|
| 🔴 严重 | 远程代码执行、数据泄露 | 24小时内 |
| 🟠 高危 | 权限提升、认证绕过 | 72小时内 |
| 🟡 中危 | 信息泄露、DoS | 1周内 |
| 🟢 低危 | 配置问题、信息收集 | 2周内 |

## 合规要求

### 数据保护

- 支持数据删除（GDPR Right to be Forgotten）
- 数据处理透明度（审计日志）
- 数据最小化原则（仅收集必要信息）

### 访问控制

- 基于角色的访问控制 (RBAC)
- 最小权限原则
- 定期访问权限审查

### 审计要求

- 完整的操作审计日志
- 日志完整性保护
- 日志保留期限管理