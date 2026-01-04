"""
可观测性指标收集

提供 LLM/Embedding/Rerank 调用追踪和检索质量指标。

功能：
- 调用日志：记录每次外部服务调用的详情
- 检索指标：统计检索结果的质量分布
- 性能追踪：记录各阶段耗时

使用示例：
    from app.infra.metrics import metrics_collector, track_call
    
    # 记录 LLM 调用
    with track_call("llm", provider="ollama", model="qwen3:14b") as tracker:
        result = await llm_call(...)
        tracker.set_tokens(input_tokens=100, output_tokens=50)
    
    # 记录检索指标
    metrics_collector.record_retrieval(
        retriever="hybrid",
        query=query,
        results=results,
        latency_ms=150,
    )
"""

import logging
import time
from contextlib import contextmanager
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Generator
from collections import defaultdict

from app.infra.logging import get_request_id, get_tenant_id

logger = logging.getLogger(__name__)


@dataclass
class CallMetrics:
    """单次调用的指标"""
    call_type: str  # llm, embedding, rerank, vector_search, bm25_search
    provider: str
    model: str | None
    start_time: float
    end_time: float | None = None
    latency_ms: float | None = None
    success: bool = True
    error: str | None = None
    
    # LLM 特有
    input_tokens: int | None = None
    output_tokens: int | None = None
    
    # Embedding 特有
    text_count: int | None = None
    
    # Rerank 特有
    doc_count: int | None = None
    
    # 检索特有
    result_count: int | None = None
    
    # 请求上下文
    request_id: str | None = None
    tenant_id: str | None = None
    
    def to_dict(self) -> dict:
        """转换为字典，用于日志输出"""
        data = {
            "call_type": self.call_type,
            "provider": self.provider,
            "model": self.model,
            "latency_ms": self.latency_ms,
            "success": self.success,
        }
        
        if self.error:
            data["error"] = self.error
        if self.input_tokens is not None:
            data["input_tokens"] = self.input_tokens
        if self.output_tokens is not None:
            data["output_tokens"] = self.output_tokens
        if self.text_count is not None:
            data["text_count"] = self.text_count
        if self.doc_count is not None:
            data["doc_count"] = self.doc_count
        if self.result_count is not None:
            data["result_count"] = self.result_count
        if self.request_id:
            data["request_id"] = self.request_id
        if self.tenant_id:
            data["tenant_id"] = self.tenant_id
            
        return data


@dataclass
class RetrievalMetrics:
    """检索结果指标"""
    retriever: str
    query_length: int
    result_count: int
    latency_ms: float
    backend: str | None = None
    error: str | None = None
    
    # 分数分布
    max_score: float | None = None
    min_score: float | None = None
    avg_score: float | None = None
    
    # 来源分布（hybrid 检索）
    source_distribution: dict[str, int] = field(default_factory=dict)
    
    # 知识库分布
    kb_distribution: dict[str, int] = field(default_factory=dict)
    
    # 请求上下文
    request_id: str | None = None
    tenant_id: str | None = None
    
    def to_dict(self) -> dict:
        """转换为字典"""
        return {
            "retriever": self.retriever,
            "query_length": self.query_length,
            "result_count": self.result_count,
            "latency_ms": self.latency_ms,
            "backend": self.backend,
            "error": self.error,
            "max_score": self.max_score,
            "min_score": self.min_score,
            "avg_score": self.avg_score,
            "source_distribution": self.source_distribution,
            "kb_distribution": self.kb_distribution,
            "request_id": self.request_id,
            "tenant_id": self.tenant_id,
        }


class CallTracker:
    """调用追踪器上下文"""
    
    def __init__(
        self,
        call_type: str,
        provider: str,
        model: str | None = None,
    ):
        self.metrics = CallMetrics(
            call_type=call_type,
            provider=provider,
            model=model,
            start_time=time.perf_counter(),
            request_id=get_request_id(),
            tenant_id=get_tenant_id(),
        )
    
    def set_tokens(self, input_tokens: int | None = None, output_tokens: int | None = None) -> None:
        """设置 token 数量（LLM 调用）"""
        self.metrics.input_tokens = input_tokens
        self.metrics.output_tokens = output_tokens
    
    def set_text_count(self, count: int) -> None:
        """设置文本数量（Embedding 调用）"""
        self.metrics.text_count = count
    
    def set_doc_count(self, count: int) -> None:
        """设置文档数量（Rerank 调用）"""
        self.metrics.doc_count = count
    
    def set_result_count(self, count: int) -> None:
        """设置结果数量"""
        self.metrics.result_count = count
    
    def set_error(self, error: str) -> None:
        """设置错误信息"""
        self.metrics.success = False
        self.metrics.error = error
    
    def finish(self) -> CallMetrics:
        """完成追踪"""
        self.metrics.end_time = time.perf_counter()
        self.metrics.latency_ms = (self.metrics.end_time - self.metrics.start_time) * 1000
        return self.metrics


class MetricsCollector:
    """
    指标收集器
    
    收集调用指标和检索质量指标，输出到日志。
    后续可扩展为 Prometheus 指标导出。
    """
    
    def __init__(self):
        # 内存中的统计信息（可选，用于聚合）
        self._call_counts: dict[str, int] = defaultdict(int)
        self._call_latencies: dict[str, list[float]] = defaultdict(list)
        self._retrieval_counts: dict[str, int] = defaultdict(int)
        self._retrieval_backends: dict[str, dict[str, float]] = defaultdict(
            lambda: {"count": 0, "errors": 0, "total_latency_ms": 0.0}
        )
        self._call_errors: dict[str, int] = defaultdict(int)
    
    def record_call(self, metrics: CallMetrics) -> None:
        """记录调用指标"""
        # 更新内存统计
        key = f"{metrics.call_type}:{metrics.provider}"
        self._call_counts[key] += 1
        if metrics.latency_ms:
            self._call_latencies[key].append(metrics.latency_ms)
            # 保留最近 1000 条用于计算平均值
            if len(self._call_latencies[key]) > 1000:
                self._call_latencies[key] = self._call_latencies[key][-1000:]
        
        # 输出结构化日志
        log_data = metrics.to_dict()
        if metrics.success:
            logger.info(
                f"[{metrics.call_type.upper()}] {metrics.provider} 调用完成 "
                f"({metrics.latency_ms:.1f}ms)",
                extra={"metrics": log_data},
            )
        else:
            logger.warning(
                f"[{metrics.call_type.upper()}] {metrics.provider} 调用失败: {metrics.error}",
                extra={"metrics": log_data},
            )
            self._call_errors[key] += 1
    
    def record_retrieval(
        self,
        retriever: str,
        query: str,
        results: list[dict],
        latency_ms: float,
        backend: str | None = None,
        error: str | None = None,
    ) -> None:
        """记录检索指标"""
        # 计算分数统计
        scores = [r.get("score", 0) for r in results if r.get("score") is not None]
        
        # 统计来源分布
        source_dist: dict[str, int] = defaultdict(int)
        kb_dist: dict[str, int] = defaultdict(int)
        
        for r in results:
            source = r.get("source", "unknown")
            source_dist[source] += 1
            
            kb_id = r.get("knowledge_base_id", "unknown")
            kb_dist[kb_id] += 1
        
        metrics = RetrievalMetrics(
            retriever=retriever,
            query_length=len(query),
            result_count=len(results),
            latency_ms=latency_ms,
            max_score=max(scores) if scores else None,
            min_score=min(scores) if scores else None,
            avg_score=sum(scores) / len(scores) if scores else None,
            source_distribution=dict(source_dist),
            kb_distribution=dict(kb_dist),
            request_id=get_request_id(),
            tenant_id=get_tenant_id(),
            backend=backend,
            error=error,
        )
        
        # 更新内存统计
        self._retrieval_counts[retriever] += 1
        backend_key = backend or retriever
        backend_stats = self._retrieval_backends[backend_key]
        backend_stats["count"] += 1
        backend_stats["total_latency_ms"] += latency_ms
        if error:
            backend_stats["errors"] += 1
        
        # 输出结构化日志
        log_data = metrics.to_dict()
        avg_score_str = f"{metrics.avg_score:.3f}" if metrics.avg_score else "0"
        logger.info(
            f"[RETRIEVAL] {retriever} 检索完成: {len(results)} 结果 "
            f"(avg_score={avg_score_str}, latency={latency_ms:.1f}ms)",
            extra={"retrieval_metrics": log_data},
        )
    
    def get_stats(self) -> dict:
        """获取聚合统计信息"""
        stats = {
            "calls": {},
            "retrievals": {},
        }
        
        for key, count in self._call_counts.items():
            latencies = self._call_latencies.get(key, [])
            stats["calls"][key] = {
                "count": count,
                "avg_latency_ms": sum(latencies) / len(latencies) if latencies else 0,
                "max_latency_ms": max(latencies) if latencies else 0,
            }
        
        for retriever, count in self._retrieval_counts.items():
            stats["retrievals"][retriever] = {"count": count}
        stats["retrieval_backends"] = {}
        for backend, data in self._retrieval_backends.items():
            count = data["count"]
            avg_latency = data["total_latency_ms"] / count if count else 0
            stats["retrieval_backends"][backend] = {
                "count": count,
                "errors": data["errors"],
                "avg_latency_ms": round(avg_latency, 2) if count else 0,
            }
        
        if self._call_errors:
            stats["call_errors"] = dict(self._call_errors)
        return stats


# 全局指标收集器
metrics_collector = MetricsCollector()


@contextmanager
def track_call(
    call_type: str,
    provider: str,
    model: str | None = None,
) -> Generator[CallTracker, None, None]:
    """
    追踪外部调用的上下文管理器
    
    使用示例：
        with track_call("llm", "ollama", "qwen3:14b") as tracker:
            result = await llm_call(...)
            tracker.set_tokens(input_tokens=100, output_tokens=50)
    """
    tracker = CallTracker(call_type, provider, model)
    try:
        yield tracker
    except Exception as e:
        tracker.set_error(str(e))
        raise
    finally:
        metrics = tracker.finish()
        metrics_collector.record_call(metrics)
