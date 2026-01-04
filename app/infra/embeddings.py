"""
文本向量化模块 (Embeddings)

将文本转换为向量表示，用于语义相似度计算。

支持的 Embedding 提供者：
- OpenAI (text-embedding-3-small/large)
- Ollama (本地模型：bge-m3, qwen3-embedding 等)
- Gemini (text-embedding-004)
- Qwen/通义千问 (text-embedding-v3)
- 智谱 AI (embedding-3)
- SiliconFlow (多种开源模型)

使用示例：
    from app.infra.embeddings import get_embeddings, get_embedding
    
    # 单个文本
    vec = await get_embedding("什么是 RAG？")
    
    # 批量文本
    vecs = await get_embeddings(["文本1", "文本2"])
"""

import hashlib
import logging
import math
from functools import lru_cache
from typing import Any

import httpx
from openai import AsyncOpenAI

from app.config import get_settings
from app.infra.url_utils import normalize_base_url

logger = logging.getLogger(__name__)

# 各 Embedding 提供商的 API 批次限制
# 参考官方文档，超过限制会导致 API 调用失败
EMBEDDING_BATCH_LIMITS: dict[str, int] = {
    "ollama": 1000,      # 本地部署，无硬性限制
    "openai": 2048,      # https://platform.openai.com/docs/api-reference/embeddings
    "qwen": 10,          # 阿里云 DashScope text-embedding-v3 限制
    "zhipu": 16,         # 智谱 AI embedding-3 限制
    "gemini": 100,       # Google AI 限制
    "siliconflow": 64,   # SiliconFlow 限制
    "deepseek": 100,     # DeepSeek 限制（假设值）
    "kimi": 100,         # Moonshot 限制（假设值）
}


def get_provider_batch_limit(provider: str, user_batch_size: int | None = None) -> int:
    """
    获取指定提供商的有效批次大小
    
    Args:
        provider: 提供商名称
        user_batch_size: 用户配置的批次大小（可选）
    
    Returns:
        有效的批次大小（取用户配置和提供商限制的较小值）
    """
    provider_limit = EMBEDDING_BATCH_LIMITS.get(provider, 100)
    if user_batch_size is not None:
        return min(user_batch_size, provider_limit)
    return provider_limit


@lru_cache(maxsize=8)
def _get_openai_compatible_client(api_key: str | None, base_url: str | None) -> AsyncOpenAI:
    """获取 OpenAI 兼容客户端（支持多种提供商）"""
    base_url = normalize_base_url(base_url)
    return AsyncOpenAI(
        api_key=api_key or "dummy",  # Ollama 不需要 API Key
        base_url=base_url,
        timeout=60.0,
    )


async def _ollama_embedding(text: str, config: dict[str, Any]) -> list[float]:
    """通过 Ollama API 获取 Embedding"""
    url = f"{config['base_url']}/api/embeddings"

    async with httpx.AsyncClient(timeout=60.0) as client:
        response = await client.post(
            url,
            json={"model": config["model"], "prompt": text},
        )
        response.raise_for_status()
        return response.json()["embedding"]


async def _ollama_embeddings_batch(texts: list[str], config: dict[str, Any]) -> list[list[float]]:
    """批量获取 Ollama Embedding（顺序调用）"""
    results = []
    for text in texts:
        vec = await _ollama_embedding(text, config)
        results.append(vec)
    return results


async def _openai_compatible_embedding(
    text: str,
    config: dict[str, Any]
) -> list[float]:
    """通过 OpenAI 兼容 API 获取 Embedding"""
    client = _get_openai_compatible_client(config.get("api_key"), config.get("base_url"))
    try:
        response = await client.embeddings.create(
            model=config["model"],
            input=text,
        )
        return response.data[0].embedding
    except Exception as exc:
        status = getattr(getattr(exc, "response", None), "status_code", None)
        body = None
        try:
            resp = getattr(exc, "response", None)
            body = resp.text[:2000] if resp and resp.text else None
        except Exception:
            body = None
        logger.error(
            f"Embedding 请求失败 ({config.get('provider')}): {exc} status={status} body={body}",
            exc_info=True,
            extra={
                "embedding_provider": config.get("provider"),
                "embedding_model": config.get("model"),
                "base_url": config.get("base_url"),
                "status": status,
                "body": body,
            },
        )
        raise


async def _openai_compatible_embeddings_batch(
    texts: list[str],
    config: dict[str, Any],
    batch_size: int = 100
) -> list[list[float]]:
    """批量获取 OpenAI 兼容 API Embedding"""
    client = _get_openai_compatible_client(config.get("api_key"), config.get("base_url"))
    results: list[list[float]] = []
    
    for i in range(0, len(texts), batch_size):
        batch = texts[i:i + batch_size]
        try:
            response = await client.embeddings.create(
                model=config["model"],
                input=batch,
            )
            sorted_data = sorted(response.data, key=lambda x: x.index)
            results.extend([d.embedding for d in sorted_data])
        except Exception as exc:
            status = getattr(getattr(exc, "response", None), "status_code", None)
            body = None
            try:
                resp = getattr(exc, "response", None)
                body = resp.text[:2000] if resp and resp.text else None
            except Exception:
                body = None
            logger.error(
                f"批量 Embedding 请求失败 ({config.get('provider')}): {exc} status={status} body={body}",
                exc_info=True,
                extra={
                    "embedding_provider": config.get("provider"),
                    "embedding_model": config.get("model"),
                    "base_url": config.get("base_url"),
                    "status": status,
                    "body": body,
                    "batch_size": batch_size,
                    "text_count": len(batch),
                },
            )
            raise
    
    return results


async def _siliconflow_embeddings_batch(
    texts: list[str],
    config: dict[str, Any],
    batch_size: int = 100,
) -> list[list[float]]:
    """批量获取 SiliconFlow Embedding（HTTP 方式，便于输出详细错误）"""
    api_key = config.get("api_key")
    base_url = normalize_base_url(config.get("base_url")) or "https://api.siliconflow.cn/v1"
    base_url = base_url.rstrip("/")
    url = f"{base_url}/embeddings"
    headers = {"Authorization": f"Bearer {api_key}"}
    results: list[list[float]] = []

    async with httpx.AsyncClient(timeout=60.0) as client:
        for i in range(0, len(texts), batch_size):
            batch = texts[i:i + batch_size]
            payload = {
                "model": config["model"],
                "input": batch,
            }
            try:
                response = await client.post(url, headers=headers, json=payload)
            except httpx.RequestError as exc:
                logger.error(
                    "siliconflow embeddings 连接失败",
                    exc_info=True,
                    extra={
                        "embedding_provider": "siliconflow",
                        "embedding_model": config.get("model"),
                        "base_url": base_url,
                        "batch_size": batch_size,
                        "text_count": len(batch),
                    },
                )
                raise exc

            body_preview = response.text[:2000] if response.text else ""
            if response.status_code >= 400:
                logger.error(
                    f"siliconflow embeddings 请求失败 status={response.status_code} body={body_preview}",
                    extra={
                        "embedding_provider": "siliconflow",
                        "embedding_model": config.get("model"),
                        "base_url": base_url,
                        "status": response.status_code,
                        "body": body_preview,
                        "batch_size": batch_size,
                        "text_count": len(batch),
                    },
                )
                response.raise_for_status()

            try:
                data = response.json()
            except Exception:
                logger.error(
                    f"siliconflow embeddings 响应无法解析 status={response.status_code} body={body_preview}",
                    extra={
                        "embedding_provider": "siliconflow",
                        "embedding_model": config.get("model"),
                        "base_url": base_url,
                        "status": response.status_code,
                        "body": body_preview,
                        "batch_size": batch_size,
                        "text_count": len(batch),
                    },
                )
                raise RuntimeError("siliconflow embeddings 响应无法解析")

            if isinstance(data, dict) and data.get("error"):
                logger.error(
                    f"siliconflow embeddings 返回错误对象 status={response.status_code} body={data}",
                    extra={
                        "embedding_provider": "siliconflow",
                        "embedding_model": config.get("model"),
                        "base_url": base_url,
                        "status": response.status_code,
                        "body": data,
                        "batch_size": batch_size,
                        "text_count": len(batch),
                    },
                )
                raise RuntimeError("siliconflow embeddings 返回错误对象")

            items = data.get("data") if isinstance(data, dict) else None
            if not items:
                logger.error(
                    f"siliconflow embeddings 返回空响应 status={response.status_code} body={data}",
                    extra={
                        "embedding_provider": "siliconflow",
                        "embedding_model": config.get("model"),
                        "base_url": base_url,
                        "status": response.status_code,
                        "body": data,
                        "batch_size": batch_size,
                        "text_count": len(batch),
                    },
                )
                raise RuntimeError("siliconflow embeddings 返回空响应")

            sorted_data = sorted(items, key=lambda x: x.get("index", 0))
            results.extend([d.get("embedding") for d in sorted_data])

    return results


async def _siliconflow_embedding(text: str, config: dict[str, Any]) -> list[float]:
    """单条 SiliconFlow Embedding"""
    results = await _siliconflow_embeddings_batch([text], config, batch_size=1)
    return results[0]


async def _gemini_embedding(text: str, config: dict[str, Any]) -> list[float]:
    """通过 Gemini API 获取 Embedding"""
    base_url = normalize_base_url(config["base_url"]) or config["base_url"]
    url = f"{base_url}/models/{config['model']}:embedContent"
    
    async with httpx.AsyncClient(timeout=60.0) as client:
        response = await client.post(
            url,
            params={"key": config["api_key"]},
            json={
                "model": f"models/{config['model']}",
                "content": {"parts": [{"text": text}]},
            },
        )
        response.raise_for_status()
        return response.json()["embedding"]["values"]


async def _gemini_embeddings_batch(texts: list[str], config: dict[str, Any]) -> list[list[float]]:
    """批量获取 Gemini Embedding"""
    # Gemini 也支持 batchEmbedContents，但这里简单起见使用循环
    results = []
    for text in texts:
        vec = await _gemini_embedding(text, config)
        results.append(vec)
    return results


async def get_embedding(text: str) -> list[float]:
    """
    获取单个文本的 Embedding 向量
    
    Args:
        text: 输入文本
    
    Returns:
        list[float]: 向量
    
    Raises:
        Exception: Embedding 生成失败
    """
    settings = get_settings()
    config = settings.get_embedding_config()
    provider = config["provider"]
    
    try:
        if provider == "ollama":
            logger.debug(f"使用 Ollama Embedding: {config['model']}")
            return await _ollama_embedding(text, config)
        
        elif provider == "gemini":
            if not config.get("api_key"):
                raise RuntimeError("GEMINI_API_KEY 未配置，无法生成真实 Embedding")
            logger.debug(f"使用 Gemini Embedding: {config['model']}")
            return await _gemini_embedding(text, config)
        
        elif provider == "siliconflow":
            if not config.get("api_key"):
                raise RuntimeError("SILICONFLOW_API_KEY 未配置，无法生成真实 Embedding")
            logger.debug(f"使用 siliconflow Embedding: {config['model']}")
            return await _siliconflow_embedding(text, config)

        elif provider in ("openai", "qwen", "zhipu", "deepseek", "kimi"):
            # 这些都是 OpenAI 兼容 API
            if not config.get("api_key"):
                raise RuntimeError(f"{provider.upper()}_API_KEY 未配置，无法生成真实 Embedding")
            logger.debug(f"使用 {provider} Embedding: {config['model']}")
            return await _openai_compatible_embedding(text, config)
        
        else:
            raise RuntimeError(f"未知 Embedding 提供者: {provider}")
            
    except Exception as e:
        logger.error(
            f"Embedding 生成失败 ({provider}): {e}",
            exc_info=True,
            extra={"embedding_provider": provider, "embedding_model": config.get("model")},
        )
        raise


async def get_embeddings(texts: list[str]) -> list[list[float]]:
    """
    批量获取文本的 Embedding 向量
    
    Args:
        texts: 文本列表
    
    Returns:
        list[list[float]]: 向量列表，顺序与输入对应
    """
    if not texts:
        return []
    
    settings = get_settings()
    config = settings.get_embedding_config()
    provider = config["provider"]
    # 使用统一的批次限制逻辑（取用户配置和提供商限制的较小值）
    batch_size = get_provider_batch_limit(provider, settings.embedding_batch_size)
    
    try:
        if provider == "ollama":
            logger.debug(f"使用 Ollama 批量 Embedding: {config['model']}")
            return await _ollama_embeddings_batch(texts, config)
        
        elif provider == "gemini":
            if not config.get("api_key"):
                raise RuntimeError("GEMINI_API_KEY 未配置，无法生成真实 Embedding")
            logger.debug(f"使用 Gemini 批量 Embedding: {config['model']} (batch_size={batch_size})")
            return await _gemini_embeddings_batch(texts, config)
        
        elif provider == "siliconflow":
            if not config.get("api_key"):
                raise RuntimeError("SILICONFLOW_API_KEY 未配置，无法生成真实 Embedding")
            logger.debug(f"使用 siliconflow 批量 Embedding: {config['model']} (batch_size={batch_size})")
            return await _siliconflow_embeddings_batch(texts, config, batch_size)

        elif provider in ("openai", "qwen", "zhipu", "deepseek", "kimi"):
            if not config.get("api_key"):
                raise RuntimeError(f"{provider.upper()}_API_KEY 未配置，无法生成真实 Embedding")
            logger.debug(f"使用 {provider} 批量 Embedding: {config['model']} (batch_size={batch_size})")
            return await _openai_compatible_embeddings_batch(texts, config, batch_size)
        
        else:
            raise RuntimeError(f"未知 Embedding 提供者: {provider}")
            
    except Exception as e:
        logger.error(
            f"批量 Embedding 生成失败 ({provider}): {e}",
            exc_info=True,
            extra={"embedding_provider": provider, "embedding_model": config.get("model")},
        )
        raise


def deterministic_hash_embed(text: str, dim: int = 1536) -> list[float]:
    """
    确定性哈希 Embedding（无需 API，用于测试）
    
    使用 MD5 哈希（确定性）替代 Python hash()（每次运行不同）。
    注意：无语义信息，仅用于开发测试环境。
    
    Args:
        text: 输入文本
        dim: 向量维度
    
    Returns:
        list[float]: 归一化后的向量
    """
    vec = [0.0] * dim
    for token in text.split():
        # 使用 MD5 确保确定性
        h = int(hashlib.md5(token.encode()).hexdigest(), 16)
        idx = h % dim
        vec[idx] += 1.0
    
    # L2 归一化
    norm = math.sqrt(sum(v * v for v in vec)) or 1.0
    return [v / norm for v in vec]


# 兼容旧接口
def hash_embed(text: str, dim: int = 256) -> list[float]:
    """
    【已废弃】使用 deterministic_hash_embed 替代
    
    保留此函数仅为向后兼容，将在未来版本移除。
    """
    logger.warning("hash_embed 已废弃，请使用 get_embedding 或 deterministic_hash_embed")
    return deterministic_hash_embed(text, dim=dim)


# ==================== 动态配置支持 ====================


async def get_embedding_with_config(
    text: str,
    provider_config: dict[str, Any],
) -> list[float]:
    """
    使用指定配置获取单个文本的 Embedding 向量
    
    此函数支持动态配置，配置来自 ModelConfigResolver 解析的结果。
    
    Args:
        text: 输入文本
        provider_config: 提供商配置，包含 provider, model, api_key, base_url
    
    Returns:
        list[float]: 向量
    
    Example:
        config = await model_config_resolver.get_embedding_config(session, tenant, kb)
        provider_config = settings._get_provider_config(
            config["embedding_provider"], 
            config["embedding_model"],
            model_type="embedding"
        )
        vec = await get_embedding_with_config(text, provider_config)
    """
    provider = provider_config.get("provider")
    
    try:
        if provider == "ollama":
            logger.debug(f"使用 Ollama Embedding: {provider_config['model']}")
            return await _ollama_embedding(text, provider_config)
        
        elif provider == "gemini":
            if not provider_config.get("api_key"):
                raise RuntimeError("GEMINI_API_KEY 未配置，无法生成真实 Embedding")
            logger.debug(f"使用 Gemini Embedding: {provider_config['model']}")
            return await _gemini_embedding(text, provider_config)
        
        elif provider in ("openai", "qwen", "zhipu", "siliconflow", "deepseek", "kimi"):
            if not provider_config.get("api_key"):
                raise RuntimeError(f"{provider.upper()}_API_KEY 未配置，无法生成真实 Embedding")
            logger.debug(f"使用 {provider} Embedding: {provider_config['model']}")
            return await _openai_compatible_embedding(text, provider_config)
        
        else:
            raise RuntimeError(f"未知 Embedding 提供者: {provider}")
            
    except Exception as e:
        logger.error(f"Embedding 生成失败 ({provider}): {e}")
        raise


async def get_embeddings_with_config(
    texts: list[str],
    provider_config: dict[str, Any],
    batch_size: int | None = None,
) -> list[list[float]]:
    """
    使用指定配置批量获取文本的 Embedding 向量
    
    Args:
        texts: 文本列表
        provider_config: 提供商配置
        batch_size: 批处理大小（默认使用环境变量配置）
    
    Returns:
        list[list[float]]: 向量列表，顺序与输入对应
    """
    if not texts:
        return []
    
    provider = provider_config.get("provider")
    
    # 使用统一的批次限制逻辑（取用户配置和提供商限制的较小值）
    actual_batch_size = get_provider_batch_limit(provider, batch_size)
    
    try:
        if provider == "ollama":
            logger.debug(f"使用 Ollama 批量 Embedding: {provider_config['model']}")
            return await _ollama_embeddings_batch(texts, provider_config)
        
        elif provider == "gemini":
            if not provider_config.get("api_key"):
                raise RuntimeError("GEMINI_API_KEY 未配置，无法生成真实 Embedding")
            logger.debug(f"使用 Gemini 批量 Embedding: {provider_config['model']} (batch_size={actual_batch_size})")
            return await _gemini_embeddings_batch(texts, provider_config)
        
        elif provider in ("openai", "qwen", "zhipu", "siliconflow", "deepseek", "kimi"):
            if not provider_config.get("api_key"):
                raise RuntimeError(f"{provider.upper()}_API_KEY 未配置，无法生成真实 Embedding")
            logger.debug(f"使用 {provider} 批量 Embedding: {provider_config['model']} (batch_size={actual_batch_size})")
            return await _openai_compatible_embeddings_batch(texts, provider_config, actual_batch_size)
        
        else:
            raise RuntimeError(f"未知 Embedding 提供者: {provider}")
            
    except Exception as e:
        logger.error(f"批量 Embedding 生成失败 ({provider}): {e}")
        raise
