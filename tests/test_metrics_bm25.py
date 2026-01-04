from app.infra.metrics import RetrievalMetrics


def test_retrieval_metrics_backend_and_error():
    m = RetrievalMetrics(
        retriever="bm25_es",
        query_length=5,
        result_count=1,
        latency_ms=12.3,
        backend="es",
        error="timeout",
    )
    d = m.to_dict()
    assert d["backend"] == "es"
    assert d["error"] == "timeout"


def test_metrics_collector_backend_stats():
    from app.infra.metrics import metrics_collector
    metrics_collector.record_retrieval(
        retriever="bm25_es",
        query="q",
        results=[],
        latency_ms=10,
        backend="es",
        error="fail",
    )
    stats = metrics_collector.get_stats()
    es_stats = stats["retrieval_backends"].get("es")
    assert es_stats
    assert es_stats["errors"] >= 1
