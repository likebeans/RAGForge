# 监控运维指南

本文档详细介绍 Self-RAG Pipeline 系统的监控、指标收集、告警配置和可观测性最佳实践。

## 监控架构概览

```
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   Application   │    │   Prometheus    │    │     Grafana     │
│   (Metrics)     │───▶│   (Collection)  │───▶│  (Visualization)│
└─────────────────┘    └─────────────────┘    └─────────────────┘
         │                       │                       │
         ▼                       ▼                       ▼
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   Structured    │    │   AlertManager  │    │   Notification  │
│     Logs        │───▶│   (Alerting)    │───▶│   (Slack/Email) │
└─────────────────┘    └─────────────────┘    └─────────────────┘
         │
         ▼
┌─────────────────┐
│   ELK Stack     │
│ (Log Analysis)  │
└─────────────────┘
```

## 系统指标

### 应用指标

#### 核心业务指标

| 指标名称 | 类型 | 说明 | 标签 |
|---------|------|------|------|
| `http_requests_total` | Counter | HTTP 请求总数 | method, endpoint, status_code |
| `http_request_duration_seconds` | Histogram | 请求延迟分布 | method, endpoint |
| `rag_operations_total` | Counter | RAG 操作总数 | operation_type, status |
| `retrieval_operations_total` | Counter | 检索操作总数 | retriever_type, kb_id |
| `document_ingestion_total` | Counter | 文档摄取总数 | status, chunker_type |
| `active_api_keys` | Gauge | 活跃 API Key 数量 | tenant_id |
| `knowledge_bases_total` | Gauge | 知识库总数 | tenant_id |
| `documents_total` | Gauge | 文档总数 | tenant_id, kb_id |
| `chunks_total` | Gauge | 文档块总数 | tenant_id, kb_id, status |

#### 外部服务调用指标

| 指标名称 | 类型 | 说明 | 标签 |
|---------|------|------|------|
| `llm_calls_total` | Counter | LLM 调用总数 | provider, model, status |
| `llm_call_duration_seconds` | Histogram | LLM 调用延迟 | provider, model |
| `embedding_calls_total` | Counter | Embedding 调用总数 | provider, model, status |
| `embedding_call_duration_seconds` | Histogram | Embedding 调用延迟 | provider, model |
| `vector_store_operations_total` | Counter | 向量库操作总数 | operation, collection |
| `vector_store_operation_duration_seconds` | Histogram | 向量库操作延迟 | operation, collection |

#### 系统资源指标

| 指标名称 | 类型 | 说明 |
|---------|------|------|
| `process_cpu_seconds_total` | Counter | CPU 使用时间 |
| `process_resident_memory_bytes` | Gauge | 内存使用量 |
| `process_open_fds` | Gauge | 打开的文件描述符数 |
| `database_connections_active` | Gauge | 活跃数据库连接数 |
| `database_connections_idle` | Gauge | 空闲数据库连接数 |
| `cache_hits_total` | Counter | 缓存命中次数 |
| `cache_misses_total` | Counter | 缓存未命中次数 |

### 指标收集配置

#### Prometheus 配置

```yaml
# prometheus.yml
global:
  scrape_interval: 15s
  evaluation_interval: 15s

rule_files:
  - "alert_rules.yml"

scrape_configs:
  - job_name: 'rag-pipeline-api'
    static_configs:
      - targets: ['api:8020']
    metrics_path: '/metrics'
    scrape_interval: 30s
    scrape_timeout: 10s

  - job_name: 'qdrant'
    static_configs:
      - targets: ['qdrant:6333']
    metrics_path: '/metrics'
    scrape_interval: 30s

  - job_name: 'postgres'
    static_configs:
      - targets: ['postgres-exporter:9187']
    scrape_interval: 30s

  - job_name: 'redis'
    static_configs:
      - targets: ['redis-exporter:9121']
    scrape_interval: 30s

  - job_name: 'node'
    static_configs:
      - targets: ['node-exporter:9100']
    scrape_interval: 30s

alerting:
  alertmanagers:
    - static_configs:
        - targets:
          - alertmanager:9093
```

#### 应用指标暴露

```python
# app/infra/metrics.py
from prometheus_client import Counter, Histogram, Gauge, generate_latest
import time
from functools import wraps

# 定义指标
http_requests_total = Counter(
    'http_requests_total',
    'Total HTTP requests',
    ['method', 'endpoint', 'status_code']
)

http_request_duration = Histogram(
    'http_request_duration_seconds',
    'HTTP request duration',
    ['method', 'endpoint']
)

llm_calls_total = Counter(
    'llm_calls_total',
    'Total LLM calls',
    ['provider', 'model', 'status']
)

llm_call_duration = Histogram(
    'llm_call_duration_seconds',
    'LLM call duration',
    ['provider', 'model']
)

database_connections_active = Gauge(
    'database_connections_active',
    'Active database connections'
)

# 装饰器用于自动记录指标
def track_http_metrics(func):
    @wraps(func)
    async def wrapper(request, *args, **kwargs):
        start_time = time.time()
        method = request.method
        endpoint = request.url.path
        
        try:
            response = await func(request, *args, **kwargs)
            status_code = response.status_code
            http_requests_total.labels(
                method=method, 
                endpoint=endpoint, 
                status_code=status_code
            ).inc()
            return response
        except Exception as e:
            http_requests_total.labels(
                method=method, 
                endpoint=endpoint, 
                status_code=500
            ).inc()
            raise
        finally:
            duration = time.time() - start_time
            http_request_duration.labels(
                method=method, 
                endpoint=endpoint
            ).observe(duration)
    
    return wrapper

def track_llm_call(provider: str, model: str):
    def decorator(func):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            start_time = time.time()
            try:
                result = await func(*args, **kwargs)
                llm_calls_total.labels(
                    provider=provider, 
                    model=model, 
                    status='success'
                ).inc()
                return result
            except Exception as e:
                llm_calls_total.labels(
                    provider=provider, 
                    model=model, 
                    status='error'
                ).inc()
                raise
            finally:
                duration = time.time() - start_time
                llm_call_duration.labels(
                    provider=provider, 
                    model=model
                ).observe(duration)
        return wrapper
    return decorator

# 指标端点
async def metrics_endpoint():
    return generate_latest()
```

#### 中间件集成

```python
# app/middleware/metrics.py
from starlette.middleware.base import BaseHTTPMiddleware
from app.infra.metrics import track_http_metrics

class MetricsMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request, call_next):
        return await track_http_metrics(call_next)(request)
```

## 健康检查

### 健康检查端点

#### 基础健康检查

```python
# app/api/routes/health.py
from fastapi import APIRouter, HTTPException
from app.db.session import async_session_maker
from app.infra.vector_store import get_vector_store
import asyncio
import time

router = APIRouter()

@router.get("/health")
async def health_check():
    """基础健康检查 - 用于负载均衡器"""
    return {"status": "ok", "timestamp": time.time()}

@router.get("/ready")
async def readiness_check():
    """就绪检查 - 检查所有依赖服务"""
    checks = {}
    overall_status = "ok"
    
    # 检查数据库
    try:
        start_time = time.time()
        async with async_session_maker() as session:
            await session.execute("SELECT 1")
        db_latency = (time.time() - start_time) * 1000
        checks["database"] = {
            "status": "ok",
            "message": "connected",
            "latency_ms": round(db_latency, 2)
        }
    except Exception as e:
        checks["database"] = {
            "status": "error",
            "message": str(e)
        }
        overall_status = "error"
    
    # 检查向量库
    try:
        start_time = time.time()
        vector_store = get_vector_store()
        collections = await vector_store.list_collections()
        qdrant_latency = (time.time() - start_time) * 1000
        checks["qdrant"] = {
            "status": "ok",
            "message": f"connected ({len(collections)} collections)",
            "latency_ms": round(qdrant_latency, 2)
        }
    except Exception as e:
        checks["qdrant"] = {
            "status": "error",
            "message": str(e)
        }
        overall_status = "error"
    
    # 检查 Redis（如果启用）
    if settings.redis_url:
        try:
            start_time = time.time()
            # Redis 连接检查
            redis_latency = (time.time() - start_time) * 1000
            checks["redis"] = {
                "status": "ok",
                "message": "connected",
                "latency_ms": round(redis_latency, 2)
            }
        except Exception as e:
            checks["redis"] = {
                "status": "error",
                "message": str(e)
            }
            overall_status = "error"
    
    status_code = 200 if overall_status == "ok" else 503
    return {
        "status": overall_status,
        "checks": checks,
        "timestamp": time.time()
    }

@router.get("/metrics")
async def system_metrics():
    """系统指标 - 用于监控"""
    from app.infra.metrics import get_system_metrics
    return await get_system_metrics()
```

#### 深度健康检查

```python
@router.get("/health/deep")
async def deep_health_check():
    """深度健康检查 - 测试核心功能"""
    checks = {}
    
    # 测试数据库查询
    try:
        async with async_session_maker() as session:
            result = await session.execute("""
                SELECT 
                    COUNT(*) as total_tenants,
                    (SELECT COUNT(*) FROM knowledge_bases) as total_kbs,
                    (SELECT COUNT(*) FROM documents) as total_docs,
                    (SELECT COUNT(*) FROM chunks WHERE indexing_status = 'indexed') as indexed_chunks
            """)
            row = result.fetchone()
            checks["database_query"] = {
                "status": "ok",
                "data": {
                    "total_tenants": row.total_tenants,
                    "total_kbs": row.total_kbs,
                    "total_docs": row.total_docs,
                    "indexed_chunks": row.indexed_chunks
                }
            }
    except Exception as e:
        checks["database_query"] = {"status": "error", "message": str(e)}
    
    # 测试向量库查询
    try:
        vector_store = get_vector_store()
        collections_info = await vector_store.get_collections_info()
        checks["vector_store_query"] = {
            "status": "ok",
            "data": collections_info
        }
    except Exception as e:
        checks["vector_store_query"] = {"status": "error", "message": str(e)}
    
    # 测试 LLM 调用（如果配置）
    if settings.llm_provider != "none":
        try:
            from app.infra.llm import get_llm_client
            llm = get_llm_client()
            response = await llm.agenerate("Hello")
            checks["llm_service"] = {
                "status": "ok",
                "message": f"LLM responded: {response[:50]}..."
            }
        except Exception as e:
            checks["llm_service"] = {"status": "error", "message": str(e)}
    
    return {"checks": checks, "timestamp": time.time()}
```

### 容器健康检查

#### Docker Compose 配置

```yaml
# docker-compose.yml
services:
  api:
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8020/health"]
      interval: 30s
      timeout: 10s
      retries: 3
      start_period: 40s
    
  db:
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U kb -d kb"]
      interval: 10s
      timeout: 5s
      retries: 5
      start_period: 30s
    
  qdrant:
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:6333/health"]
      interval: 30s
      timeout: 10s
      retries: 3
    
  redis:
    healthcheck:
      test: ["CMD", "redis-cli", "ping"]
      interval: 10s
      timeout: 5s
      retries: 3
```

#### Kubernetes 探针配置

```yaml
# k8s deployment
spec:
  containers:
  - name: api
    livenessProbe:
      httpGet:
        path: /health
        port: 8020
      initialDelaySeconds: 30
      periodSeconds: 30
      timeoutSeconds: 10
      failureThreshold: 3
    
    readinessProbe:
      httpGet:
        path: /ready
        port: 8020
      initialDelaySeconds: 10
      periodSeconds: 10
      timeoutSeconds: 5
      failureThreshold: 3
    
    startupProbe:
      httpGet:
        path: /health
        port: 8020
      initialDelaySeconds: 10
      periodSeconds: 5
      timeoutSeconds: 3
      failureThreshold: 30
```

## 告警配置

### 告警规则

```yaml
# alert_rules.yml
groups:
- name: rag-pipeline-alerts
  rules:
  
  # 服务可用性告警
  - alert: ServiceDown
    expr: up{job="rag-pipeline-api"} == 0
    for: 1m
    labels:
      severity: critical
      team: platform
    annotations:
      summary: "RAG Pipeline API service is down"
      description: "The RAG Pipeline API service has been down for more than 1 minute"
      runbook_url: "https://docs.company.com/runbooks/rag-pipeline-down"
  
  # 高错误率告警
  - alert: HighErrorRate
    expr: |
      (
        rate(http_requests_total{status_code=~"5.."}[5m]) /
        rate(http_requests_total[5m])
      ) > 0.05
    for: 2m
    labels:
      severity: warning
      team: platform
    annotations:
      summary: "High error rate detected"
      description: "Error rate is {{ $value | humanizePercentage }} over the last 5 minutes"
  
  # 高延迟告警
  - alert: HighLatency
    expr: |
      histogram_quantile(0.99, 
        rate(http_request_duration_seconds_bucket[5m])
      ) > 5
    for: 5m
    labels:
      severity: warning
      team: platform
    annotations:
      summary: "High latency detected"
      description: "99th percentile latency is {{ $value }}s over the last 5 minutes"
  
  # 数据库连接告警
  - alert: DatabaseConnectionsHigh
    expr: database_connections_active > 18
    for: 2m
    labels:
      severity: warning
      team: platform
    annotations:
      summary: "Database connections near limit"
      description: "Active database connections: {{ $value }}/20"
  
  # LLM 调用失败率告警
  - alert: LLMCallFailureRate
    expr: |
      (
        rate(llm_calls_total{status="error"}[10m]) /
        rate(llm_calls_total[10m])
      ) > 0.1
    for: 5m
    labels:
      severity: warning
      team: ai
    annotations:
      summary: "High LLM call failure rate"
      description: "LLM call failure rate is {{ $value | humanizePercentage }}"
  
  # 磁盘空间告警
  - alert: DiskSpaceHigh
    expr: |
      (
        node_filesystem_size_bytes{fstype!="tmpfs"} - 
        node_filesystem_free_bytes{fstype!="tmpfs"}
      ) / node_filesystem_size_bytes{fstype!="tmpfs"} > 0.8
    for: 5m
    labels:
      severity: warning
      team: infrastructure
    annotations:
      summary: "Disk space usage high"
      description: "Disk usage is {{ $value | humanizePercentage }} on {{ $labels.device }}"
  
  # 内存使用告警
  - alert: MemoryUsageHigh
    expr: |
      (
        node_memory_MemTotal_bytes - 
        node_memory_MemAvailable_bytes
      ) / node_memory_MemTotal_bytes > 0.9
    for: 5m
    labels:
      severity: critical
      team: infrastructure
    annotations:
      summary: "Memory usage critical"
      description: "Memory usage is {{ $value | humanizePercentage }}"
  
  # 向量库操作失败告警
  - alert: VectorStoreOperationFailures
    expr: |
      rate(vector_store_operations_total{status="error"}[5m]) > 0.1
    for: 3m
    labels:
      severity: warning
      team: platform
    annotations:
      summary: "Vector store operation failures"
      description: "Vector store error rate: {{ $value }} errors/sec"

- name: business-alerts
  rules:
  
  # 文档摄取失败告警
  - alert: DocumentIngestionFailures
    expr: |
      rate(document_ingestion_total{status="failed"}[10m]) > 0.05
    for: 5m
    labels:
      severity: warning
      team: platform
    annotations:
      summary: "Document ingestion failures detected"
      description: "Document ingestion failure rate: {{ $value }} failures/sec"
  
  # 检索操作异常告警
  - alert: RetrievalOperationAnomalies
    expr: |
      histogram_quantile(0.95, 
        rate(http_request_duration_seconds_bucket{endpoint="/v1/retrieve"}[10m])
      ) > 10
    for: 5m
    labels:
      severity: warning
      team: ai
    annotations:
      summary: "Retrieval operations are slow"
      description: "95th percentile retrieval latency: {{ $value }}s"
  
  # 租户配额告警
  - alert: TenantQuotaExceeded
    expr: |
      documents_total > 1000
    for: 1m
    labels:
      severity: info
      team: business
    annotations:
      summary: "Tenant approaching document quota"
      description: "Tenant {{ $labels.tenant_id }} has {{ $value }} documents"
```

### AlertManager 配置

```yaml
# alertmanager.yml
global:
  smtp_smarthost: 'smtp.company.com:587'
  smtp_from: 'alerts@company.com'
  smtp_auth_username: 'alerts@company.com'
  smtp_auth_password: 'password'

route:
  group_by: ['alertname', 'severity']
  group_wait: 10s
  group_interval: 10s
  repeat_interval: 1h
  receiver: 'default'
  routes:
  - match:
      severity: critical
    receiver: 'critical-alerts'
  - match:
      team: ai
    receiver: 'ai-team'
  - match:
      team: platform
    receiver: 'platform-team'

receivers:
- name: 'default'
  email_configs:
  - to: 'oncall@company.com'
    subject: '[RAG Pipeline] {{ .GroupLabels.alertname }}'
    body: |
      {{ range .Alerts }}
      Alert: {{ .Annotations.summary }}
      Description: {{ .Annotations.description }}
      {{ end }}

- name: 'critical-alerts'
  email_configs:
  - to: 'oncall@company.com'
    subject: '[CRITICAL] RAG Pipeline Alert'
  slack_configs:
  - api_url: 'https://hooks.slack.com/services/...'
    channel: '#alerts-critical'
    title: 'Critical Alert: {{ .GroupLabels.alertname }}'
    text: |
      {{ range .Alerts }}
      {{ .Annotations.summary }}
      {{ .Annotations.description }}
      {{ end }}

- name: 'ai-team'
  slack_configs:
  - api_url: 'https://hooks.slack.com/services/...'
    channel: '#ai-team'
    title: 'AI Service Alert: {{ .GroupLabels.alertname }}'

- name: 'platform-team'
  slack_configs:
  - api_url: 'https://hooks.slack.com/services/...'
    channel: '#platform-team'
    title: 'Platform Alert: {{ .GroupLabels.alertname }}'

inhibit_rules:
- source_match:
    severity: 'critical'
  target_match:
    severity: 'warning'
  equal: ['alertname', 'instance']
```

## 日志管理

### 结构化日志配置

```python
# app/infra/logging.py
import logging
import json
import sys
from datetime import datetime
from typing import Dict, Any

class JSONFormatter(logging.Formatter):
    """JSON 格式化器"""
    
    def format(self, record: logging.LogRecord) -> str:
        log_entry = {
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
        }
        
        # 添加额外字段
        if hasattr(record, 'request_id'):
            log_entry['request_id'] = record.request_id
        if hasattr(record, 'tenant_id'):
            log_entry['tenant_id'] = record.tenant_id
        if hasattr(record, 'user_id'):
            log_entry['user_id'] = record.user_id
        if hasattr(record, 'duration_ms'):
            log_entry['duration_ms'] = record.duration_ms
        
        # 添加异常信息
        if record.exc_info:
            log_entry['exception'] = self.formatException(record.exc_info)
        
        # 添加自定义字段
        if hasattr(record, 'extra_fields'):
            log_entry.update(record.extra_fields)
        
        return json.dumps(log_entry, ensure_ascii=False)

def setup_logging(log_level: str = "INFO", log_format: str = "json"):
    """配置日志系统"""
    
    # 设置日志级别
    level = getattr(logging, log_level.upper())
    
    # 创建根日志器
    root_logger = logging.getLogger()
    root_logger.setLevel(level)
    
    # 清除现有处理器
    for handler in root_logger.handlers[:]:
        root_logger.removeHandler(handler)
    
    # 创建控制台处理器
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(level)
    
    # 设置格式化器
    if log_format.lower() == "json":
        formatter = JSONFormatter()
    else:
        formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        )
    
    console_handler.setFormatter(formatter)
    root_logger.addHandler(console_handler)
    
    # 配置第三方库日志级别
    logging.getLogger("uvicorn").setLevel(logging.INFO)
    logging.getLogger("sqlalchemy.engine").setLevel(logging.WARNING)
    logging.getLogger("qdrant_client").setLevel(logging.WARNING)

# 日志上下文管理器
class LogContext:
    """日志上下文管理器"""
    
    def __init__(self, **kwargs):
        self.context = kwargs
        self.old_factory = logging.getLogRecordFactory()
    
    def __enter__(self):
        def record_factory(*args, **kwargs):
            record = self.old_factory(*args, **kwargs)
            for key, value in self.context.items():
                setattr(record, key, value)
            return record
        
        logging.setLogRecordFactory(record_factory)
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        logging.setLogRecordFactory(self.old_factory)

# 使用示例
logger = logging.getLogger(__name__)

# 在请求处理中使用
async def process_request(request_id: str, tenant_id: str):
    with LogContext(request_id=request_id, tenant_id=tenant_id):
        logger.info("Processing request", extra={
            'extra_fields': {
                'endpoint': '/v1/retrieve',
                'method': 'POST'
            }
        })
```

### 日志聚合配置

#### ELK Stack 配置

```yaml
# docker-compose.logging.yml
version: '3.8'

services:
  elasticsearch:
    image: docker.elastic.co/elasticsearch/elasticsearch:8.11.0
    environment:
      - discovery.type=single-node
      - xpack.security.enabled=false
      - "ES_JAVA_OPTS=-Xms512m -Xmx512m"
    volumes:
      - elasticsearch_data:/usr/share/elasticsearch/data
    ports:
      - "9200:9200"

  kibana:
    image: docker.elastic.co/kibana/kibana:8.11.0
    environment:
      - ELASTICSEARCH_HOSTS=http://elasticsearch:9200
    ports:
      - "5601:5601"
    depends_on:
      - elasticsearch

  filebeat:
    image: docker.elastic.co/beats/filebeat:8.11.0
    user: root
    volumes:
      - ./filebeat.yml:/usr/share/filebeat/filebeat.yml:ro
      - /var/lib/docker/containers:/var/lib/docker/containers:ro
      - /var/run/docker.sock:/var/run/docker.sock:ro
    depends_on:
      - elasticsearch

volumes:
  elasticsearch_data:
```

```yaml
# filebeat.yml
filebeat.inputs:
- type: container
  paths:
    - '/var/lib/docker/containers/*/*.log'
  processors:
  - add_docker_metadata:
      host: "unix:///var/run/docker.sock"
  - decode_json_fields:
      fields: ["message"]
      target: ""
      overwrite_keys: true

output.elasticsearch:
  hosts: ["elasticsearch:9200"]
  index: "rag-pipeline-%{+yyyy.MM.dd}"

setup.template.name: "rag-pipeline"
setup.template.pattern: "rag-pipeline-*"
setup.template.settings:
  index.number_of_shards: 1
  index.number_of_replicas: 0

logging.level: info
```

#### Loki 配置

```yaml
# promtail.yml
server:
  http_listen_port: 9080
  grpc_listen_port: 0

positions:
  filename: /tmp/positions.yaml

clients:
  - url: http://loki:3100/loki/api/v1/push

scrape_configs:
- job_name: containers
  static_configs:
  - targets:
      - localhost
    labels:
      job: containerlogs
      __path__: /var/lib/docker/containers/*/*log

  pipeline_stages:
  - json:
      expressions:
        output: log
        stream: stream
        attrs:
  - json:
      expressions:
        tag: attrs.tag
      source: attrs
  - regex:
      expression: (?P<container_name>(?:[^|]*))\|
      source: tag
  - timestamp:
      format: RFC3339Nano
      source: time
  - labels:
      stream:
      container_name:
  - output:
      source: output
```

## 性能监控

### 应用性能监控 (APM)

#### 自定义性能追踪

```python
# app/infra/tracing.py
import time
import asyncio
from functools import wraps
from typing import Dict, Any, Optional
from contextvars import ContextVar
import logging

# 追踪上下文
trace_context: ContextVar[Dict[str, Any]] = ContextVar('trace_context', default={})

class PerformanceTracker:
    """性能追踪器"""
    
    def __init__(self):
        self.spans: Dict[str, Dict[str, Any]] = {}
        self.logger = logging.getLogger(__name__)
    
    def start_span(self, name: str, **attributes) -> str:
        """开始一个追踪跨度"""
        span_id = f"{name}_{int(time.time() * 1000000)}"
        self.spans[span_id] = {
            'name': name,
            'start_time': time.time(),
            'attributes': attributes,
            'children': []
        }
        return span_id
    
    def end_span(self, span_id: str, **attributes):
        """结束一个追踪跨度"""
        if span_id in self.spans:
            span = self.spans[span_id]
            span['end_time'] = time.time()
            span['duration'] = span['end_time'] - span['start_time']
            span['attributes'].update(attributes)
            
            # 记录性能日志
            self.logger.info(
                f"Span completed: {span['name']}",
                extra={
                    'extra_fields': {
                        'span_name': span['name'],
                        'duration_ms': span['duration'] * 1000,
                        'attributes': span['attributes']
                    }
                }
            )
    
    def get_span(self, span_id: str) -> Optional[Dict[str, Any]]:
        """获取跨度信息"""
        return self.spans.get(span_id)

# 全局追踪器
tracer = PerformanceTracker()

def trace_async(name: str, **attributes):
    """异步函数追踪装饰器"""
    def decorator(func):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            span_id = tracer.start_span(name, **attributes)
            try:
                result = await func(*args, **kwargs)
                tracer.end_span(span_id, status='success')
                return result
            except Exception as e:
                tracer.end_span(span_id, status='error', error=str(e))
                raise
        return wrapper
    return decorator

def trace_sync(name: str, **attributes):
    """同步函数追踪装饰器"""
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            span_id = tracer.start_span(name, **attributes)
            try:
                result = func(*args, **kwargs)
                tracer.end_span(span_id, status='success')
                return result
            except Exception as e:
                tracer.end_span(span_id, status='error', error=str(e))
                raise
        return wrapper
    return decorator

# 使用示例
@trace_async("document_ingestion", operation="ingest")
async def ingest_document(content: str, kb_id: str):
    # 文档摄取逻辑
    pass

@trace_async("retrieval_operation", operation="retrieve")
async def retrieve_chunks(query: str, kb_ids: list):
    # 检索逻辑
    pass
```

#### 数据库查询监控

```python
# app/infra/db_monitoring.py
from sqlalchemy import event
from sqlalchemy.engine import Engine
import time
import logging

logger = logging.getLogger("sqlalchemy.performance")

@event.listens_for(Engine, "before_cursor_execute")
def receive_before_cursor_execute(conn, cursor, statement, parameters, context, executemany):
    context._query_start_time = time.time()

@event.listens_for(Engine, "after_cursor_execute")
def receive_after_cursor_execute(conn, cursor, statement, parameters, context, executemany):
    total = time.time() - context._query_start_time
    
    # 记录慢查询（> 1秒）
    if total > 1.0:
        logger.warning(
            "Slow query detected",
            extra={
                'extra_fields': {
                    'query_time_ms': total * 1000,
                    'statement': statement[:200],  # 截断长查询
                    'parameters': str(parameters)[:100] if parameters else None
                }
            }
        )
    
    # 记录所有查询（调试模式）
    logger.debug(
        "Database query executed",
        extra={
            'extra_fields': {
                'query_time_ms': total * 1000,
                'statement': statement[:100]
            }
        }
    )
```

### 外部服务监控

```python
# app/infra/external_monitoring.py
import httpx
import time
from typing import Dict, Any
import logging

logger = logging.getLogger("external_services")

class MonitoredHTTPClient:
    """带监控的 HTTP 客户端"""
    
    def __init__(self, service_name: str):
        self.service_name = service_name
        self.client = httpx.AsyncClient()
    
    async def request(self, method: str, url: str, **kwargs) -> httpx.Response:
        """发送 HTTP 请求并记录指标"""
        start_time = time.time()
        
        try:
            response = await self.client.request(method, url, **kwargs)
            
            # 记录成功请求
            duration = time.time() - start_time
            logger.info(
                f"{self.service_name} request completed",
                extra={
                    'extra_fields': {
                        'service': self.service_name,
                        'method': method,
                        'url': url,
                        'status_code': response.status_code,
                        'duration_ms': duration * 1000,
                        'response_size': len(response.content)
                    }
                }
            )
            
            return response
            
        except Exception as e:
            # 记录失败请求
            duration = time.time() - start_time
            logger.error(
                f"{self.service_name} request failed",
                extra={
                    'extra_fields': {
                        'service': self.service_name,
                        'method': method,
                        'url': url,
                        'error': str(e),
                        'duration_ms': duration * 1000
                    }
                }
            )
            raise

# 使用示例
openai_client = MonitoredHTTPClient("openai")
ollama_client = MonitoredHTTPClient("ollama")
```

## Grafana 仪表板

### 系统概览仪表板

```json
{
  "dashboard": {
    "title": "RAG Pipeline - System Overview",
    "panels": [
      {
        "title": "Service Status",
        "type": "stat",
        "targets": [
          {
            "expr": "up{job=\"rag-pipeline-api\"}",
            "legendFormat": "API Service"
          }
        ]
      },
      {
        "title": "Request Rate",
        "type": "graph",
        "targets": [
          {
            "expr": "rate(http_requests_total[5m])",
            "legendFormat": "{{method}} {{endpoint}}"
          }
        ]
      },
      {
        "title": "Response Time",
        "type": "graph",
        "targets": [
          {
            "expr": "histogram_quantile(0.95, rate(http_request_duration_seconds_bucket[5m]))",
            "legendFormat": "95th percentile"
          },
          {
            "expr": "histogram_quantile(0.50, rate(http_request_duration_seconds_bucket[5m]))",
            "legendFormat": "50th percentile"
          }
        ]
      },
      {
        "title": "Error Rate",
        "type": "graph",
        "targets": [
          {
            "expr": "rate(http_requests_total{status_code=~\"5..\"}[5m]) / rate(http_requests_total[5m])",
            "legendFormat": "Error Rate"
          }
        ]
      }
    ]
  }
}
```

### 业务指标仪表板

```json
{
  "dashboard": {
    "title": "RAG Pipeline - Business Metrics",
    "panels": [
      {
        "title": "Active Tenants",
        "type": "stat",
        "targets": [
          {
            "expr": "count(count by (tenant_id) (documents_total))",
            "legendFormat": "Active Tenants"
          }
        ]
      },
      {
        "title": "Document Ingestion Rate",
        "type": "graph",
        "targets": [
          {
            "expr": "rate(document_ingestion_total[5m])",
            "legendFormat": "{{status}}"
          }
        ]
      },
      {
        "title": "Retrieval Operations",
        "type": "graph",
        "targets": [
          {
            "expr": "rate(retrieval_operations_total[5m])",
            "legendFormat": "{{retriever_type}}"
          }
        ]
      },
      {
        "title": "LLM Call Success Rate",
        "type": "graph",
        "targets": [
          {
            "expr": "rate(llm_calls_total{status=\"success\"}[5m]) / rate(llm_calls_total[5m])",
            "legendFormat": "{{provider}} {{model}}"
          }
        ]
      }
    ]
  }
}
```

## 监控最佳实践

### 1. 监控策略

#### 四个黄金信号

1. **延迟 (Latency)**：请求处理时间
2. **流量 (Traffic)**：系统处理的请求量
3. **错误 (Errors)**：失败请求的比例
4. **饱和度 (Saturation)**：系统资源使用情况

#### SLI/SLO 定义

```yaml
# SLI (Service Level Indicators)
sli:
  availability:
    description: "API 可用性"
    query: "up{job='rag-pipeline-api'}"
    
  latency:
    description: "API 响应延迟"
    query: "histogram_quantile(0.95, rate(http_request_duration_seconds_bucket[5m]))"
    
  error_rate:
    description: "API 错误率"
    query: "rate(http_requests_total{status_code=~'5..'}[5m]) / rate(http_requests_total[5m])"

# SLO (Service Level Objectives)
slo:
  availability: 99.9%    # 99.9% 可用性
  latency: 2s           # 95% 请求 < 2秒
  error_rate: 0.1%      # 错误率 < 0.1%
```

### 2. 告警策略

#### 告警分级

- **P0 (Critical)**：服务完全不可用，需要立即响应
- **P1 (High)**：核心功能受影响，需要在1小时内响应
- **P2 (Medium)**：部分功能受影响，需要在4小时内响应
- **P3 (Low)**：性能下降或潜在问题，需要在24小时内响应

#### 告警疲劳预防

1. **合理设置阈值**：避免过于敏感的告警
2. **告警抑制**：相关告警的抑制规则
3. **告警分组**：按服务、团队分组
4. **告警升级**：未及时处理的告警自动升级

### 3. 容量规划

#### 资源使用趋势

```promql
# CPU 使用趋势（7天）
avg_over_time(rate(process_cpu_seconds_total[5m])[7d:1h])

# 内存使用趋势（7天）
avg_over_time(process_resident_memory_bytes[7d:1h])

# 数据库连接数趋势（7天）
avg_over_time(database_connections_active[7d:1h])

# 存储使用趋势（7天）
avg_over_time(node_filesystem_size_bytes - node_filesystem_free_bytes[7d:1h])
```

#### 容量预测

基于历史数据预测未来资源需求：

1. **线性增长预测**：基于过去30天的增长趋势
2. **季节性调整**：考虑业务周期性变化
3. **突发流量准备**：预留20-30%的缓冲容量

---

通过完善的监控体系，可以及时发现和解决问题，确保 Self-RAG Pipeline 系统的稳定运行。