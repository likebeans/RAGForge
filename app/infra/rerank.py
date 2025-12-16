"""
Rerank 重排模块

对检索结果进行重新排序，提高相关性。

支持的 Rerank 提供商：
- Ollama (本地模型：bge-reranker-large 等)
- Cohere (商业服务)
- 智谱 AI (reranker)
- SiliconFlow (BAAI/bge-reranker 等)

使用示例：
    from app.infra.rerank import rerank_results
    
    # 重排检索结果
    reranked = await rerank_results(
        query="什么是机器学习",
        documents=["文档1内容", "文档2内容", ...],
        top_k=5,
    )
"""

import logging
from typing import Any

import httpx
from openai import AsyncOpenAI

from app.config import get_settings

logger = logging.getLogger(__name__)


async def rerank_results(
    query: str,
    documents: list[str],
    top_k: int | None = None,
    rerank_override: dict | None = None,
) -> list[dict[str, Any]]:
    """
    对文档列表进行重排序
    
    Args:
        query: 查询文本
        documents: 待排序的文档列表
        top_k: 返回的文档数量，None 返回全部
        rerank_override: 临时覆盖 Rerank 配置（provider/model/api_key/base_url）
    
    Returns:
        list[dict]: 重排后的结果，每项包含 index, score, text
    """
    if not documents:
        return []
    
    settings = get_settings()
    
    # 如果有 override，使用 override 配置；缺失的 key 从系统配置补全，避免仅传 provider/model 时丢失 api_key/base_url
    if rerank_override:
        provider = rerank_override.get("provider", "none")
        model = rerank_override.get("model")
        # 从系统默认构建当前 provider 的基础配置
        if provider == "cohere":
            base_config = {
                "provider": "cohere",
                "model": model or settings.rerank_model,
                "api_key": settings.cohere_api_key,
            }
        elif provider == "vllm":
            base_config = {
                "provider": "vllm",
                "model": model or settings.rerank_model,
                "base_url": settings.vllm_rerank_base_url,
            }
        else:
            # openai 兼容/ollama 等使用统一 provider 配置
            base_config = settings._get_provider_config(provider, model or settings.rerank_model)
        
        config = {**base_config}
        # 覆盖用户显式传入的字段（包括 api_key/base_url）
        if model is not None:
            config["model"] = model
        for key in ("api_key", "base_url"):
            if rerank_override.get(key) is not None:
                config[key] = rerank_override[key]
        
        logger.info(f"使用 rerank_override: {provider}/{config.get('model')}, base_url={config.get('base_url')}")
    else:
        config = settings.get_rerank_config()
        provider = config.get("provider", "none")
    
    if provider == "none":
        # 不进行重排，保持原顺序
        return [
            {"index": i, "score": 1.0 - i * 0.01, "text": doc}
            for i, doc in enumerate(documents)
        ][:top_k]
    
    if top_k is None:
        top_k = settings.rerank_top_k
    
    try:
        if provider == "ollama":
            return await _ollama_rerank(query, documents, config, top_k)
        
        elif provider == "cohere":
            if not config.get("api_key"):
                raise ValueError("COHERE_API_KEY 未配置")
            return await _cohere_rerank(query, documents, config, top_k)
        
        elif provider in ("zhipu", "siliconflow"):
            if not config.get("api_key"):
                raise ValueError(f"{provider.upper()}_API_KEY 未配置")
            return await _openai_compatible_rerank(query, documents, config, top_k)
        
        elif provider == "vllm":
            if not config.get("base_url"):
                raise ValueError("VLLM_RERANK_BASE_URL 未配置")
            return await _vllm_rerank(query, documents, config, top_k)
        
        else:
            logger.warning(f"未知的 Rerank 提供者: {provider}，跳过重排")
            return [
                {"index": i, "score": 1.0, "text": doc}
                for i, doc in enumerate(documents)
            ][:top_k]
            
    except Exception as e:
        logger.error(f"Rerank 失败 ({provider}): {e}")
        # 失败时返回原顺序
        return [
            {"index": i, "score": 1.0, "text": doc}
            for i, doc in enumerate(documents)
        ][:top_k]


async def _ollama_rerank(
    query: str,
    documents: list[str],
    config: dict[str, Any],
    top_k: int,
) -> list[dict[str, Any]]:
    """
    Ollama Rerank
    
    注意：Ollama 原生不支持 rerank API，这里使用交叉编码器模型
    通过 /api/embeddings 获取 query-doc 对的相似度分数
    """
    url = f"{config['base_url']}/api/embeddings"
    model = config["model"]
    
    results = []
    
    async with httpx.AsyncClient(timeout=60.0) as client:
        for i, doc in enumerate(documents):
            # 将 query 和 doc 拼接，让 reranker 模型评估相关性
            # 格式: "query: {query} document: {doc}"
            combined = f"query: {query} document: {doc}"
            
            try:
                response = await client.post(
                    url,
                    json={"model": model, "prompt": combined},
                )
                response.raise_for_status()
                
                # 对于 reranker 模型，embedding 的第一个值通常表示相关性分数
                embedding = response.json().get("embedding", [0])
                score = embedding[0] if embedding else 0.0
                
                results.append({
                    "index": i,
                    "score": score,
                    "text": doc,
                })
            except Exception as e:
                logger.warning(f"Ollama rerank 单条失败: {e}")
                results.append({
                    "index": i,
                    "score": 0.0,
                    "text": doc,
                })
    
    # 按分数降序排序
    results.sort(key=lambda x: x["score"], reverse=True)
    return results[:top_k]


async def _cohere_rerank(
    query: str,
    documents: list[str],
    config: dict[str, Any],
    top_k: int,
) -> list[dict[str, Any]]:
    """Cohere Rerank API"""
    url = "https://api.cohere.ai/v1/rerank"
    
    async with httpx.AsyncClient(timeout=60.0) as client:
        response = await client.post(
            url,
            headers={
                "Authorization": f"Bearer {config['api_key']}",
                "Content-Type": "application/json",
            },
            json={
                "model": config.get("model", "rerank-multilingual-v3.0"),
                "query": query,
                "documents": documents,
                "top_n": top_k,
            },
        )
        response.raise_for_status()
        data = response.json()
        
        return [
            {
                "index": r["index"],
                "score": r["relevance_score"],
                "text": documents[r["index"]],
            }
            for r in data["results"]
        ]


async def _openai_compatible_rerank(
    query: str,
    documents: list[str],
    config: dict[str, Any],
    top_k: int,
) -> list[dict[str, Any]]:
    """
    OpenAI 兼容的 Rerank API（如智谱、SiliconFlow）
    
    这些服务通常提供 /rerank 端点
    """
    base_url = config.get("base_url", "").rstrip("/")
    url = f"{base_url}/rerank"
    
    async with httpx.AsyncClient(timeout=60.0) as client:
        response = await client.post(
            url,
            headers={
                "Authorization": f"Bearer {config['api_key']}",
                "Content-Type": "application/json",
            },
            json={
                "model": config["model"],
                "query": query,
                "documents": documents,
                "top_n": top_k,
            },
        )
        response.raise_for_status()
        data = response.json()
        
        # 解析响应（不同服务格式可能略有不同）
        results = data.get("results", data.get("data", []))
        
        return [
            {
                "index": r.get("index", i),
                "score": r.get("relevance_score", r.get("score", 0.0)),
                "text": documents[r.get("index", i)],
            }
            for i, r in enumerate(results)
        ][:top_k]


def _sigmoid(x: float) -> float:
    """Sigmoid 函数，将 logits 转换为 0-1 概率"""
    import math
    try:
        return 1 / (1 + math.exp(-x))
    except OverflowError:
        return 0.0 if x < 0 else 1.0


async def _vllm_rerank(
    query: str,
    documents: list[str],
    config: dict[str, Any],
    top_k: int,
) -> list[dict[str, Any]]:
    """
    vLLM Cross-Encoder Rerank (OpenAI 兼容格式)
    
    使用 /v1/rerank 端点（OpenAI 兼容）
    请求格式: {"model": "xxx", "query": "...", "documents": [...]}
    
    注意：Cross-encoder 模型（如 bge-reranker）返回的是原始 logits，
    可能是负数，需要应用 sigmoid 转换为 0-1 范围的分数。
    """
    base_url = config.get("base_url", "").rstrip("/")
    # base_url 已经包含 /v1，直接拼接 /rerank
    url = f"{base_url}/rerank"
    model = config["model"]
    
    async with httpx.AsyncClient(timeout=120.0) as client:
        response = await client.post(
            url,
            headers={"Content-Type": "application/json"},
            json={
                "model": model,
                "query": query,
                "documents": documents,
                "top_n": top_k,
            },
        )
        response.raise_for_status()
        data = response.json()
        
        # 调试: 打印 vLLM 原始返回
        logger.info(f"vLLM rerank 原始响应: {data}")
        
        # OpenAI 兼容格式: {"results": [{"index": 0, "relevance_score": 0.85}, ...]}
        # 或 {"data": [{"index": 0, "score": 0.85}, ...]}
        results = data.get("results", data.get("data", []))
        
        # 构建结果列表
        scored_results = []
        for i, r in enumerate(results):
            raw_score = r.get("relevance_score", r.get("score", 0.0))
            # Cross-encoder 返回的是 logits，需要转换为概率
            # 如果分数不在 0-1 范围内，应用 sigmoid
            if raw_score < 0 or raw_score > 1:
                score = _sigmoid(raw_score)
            else:
                score = raw_score
            scored_results.append({
                "index": r.get("index", i),
                "score": score,
                "text": documents[r.get("index", i)],
            })
        
        # 按分数降序排序（有些服务已经排序，但保险起见再排一次）
        scored_results.sort(key=lambda x: x["score"], reverse=True)
        return scored_results[:top_k]
