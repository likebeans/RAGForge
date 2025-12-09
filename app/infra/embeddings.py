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

logger = logging.getLogger(__name__)


@lru_cache(maxsize=8)
def _get_openai_compatible_client(api_key: str | None, base_url: str | None) -> AsyncOpenAI:
    """获取 OpenAI 兼容客户端（支持多种提供商）"""
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
    response = await client.embeddings.create(
        model=config["model"],
        input=text,
    )
    return response.data[0].embedding


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
        response = await client.embeddings.create(
            model=config["model"],
            input=batch,
        )
        sorted_data = sorted(response.data, key=lambda x: x.index)
        results.extend([d.embedding for d in sorted_data])
    
    return results


async def _gemini_embedding(text: str, config: dict[str, Any]) -> list[float]:
    """通过 Gemini API 获取 Embedding"""
    url = f"{config['base_url']}/models/{config['model']}:embedContent"
    
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
        
        elif provider in ("openai", "qwen", "zhipu", "siliconflow", "deepseek", "kimi"):
            # 这些都是 OpenAI 兼容 API
            if not config.get("api_key"):
                raise RuntimeError(f"{provider.upper()}_API_KEY 未配置，无法生成真实 Embedding")
            logger.debug(f"使用 {provider} Embedding: {config['model']}")
            return await _openai_compatible_embedding(text, config)
        
        else:
            raise RuntimeError(f"未知 Embedding 提供者: {provider}")
            
    except Exception as e:
        logger.error(f"Embedding 生成失败 ({provider}): {e}")
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
    batch_size = settings.embedding_batch_size
    
    try:
        if provider == "ollama":
            logger.debug(f"使用 Ollama 批量 Embedding: {config['model']}")
            return await _ollama_embeddings_batch(texts, config)
        
        elif provider == "gemini":
            if not config.get("api_key"):
                raise RuntimeError("GEMINI_API_KEY 未配置，无法生成真实 Embedding")
            logger.debug(f"使用 Gemini 批量 Embedding: {config['model']}")
            return await _gemini_embeddings_batch(texts, config)
        
        elif provider in ("openai", "qwen", "zhipu", "siliconflow", "deepseek", "kimi"):
            if not config.get("api_key"):
                raise RuntimeError(f"{provider.upper()}_API_KEY 未配置，无法生成真实 Embedding")
            logger.debug(f"使用 {provider} 批量 Embedding: {config['model']}")
            return await _openai_compatible_embeddings_batch(texts, config, batch_size)
        
        else:
            raise RuntimeError(f"未知 Embedding 提供者: {provider}")
            
    except Exception as e:
        logger.error(f"批量 Embedding 生成失败 ({provider}): {e}")
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
    
    if batch_size is None:
        settings = get_settings()
        batch_size = settings.embedding_batch_size
    
    try:
        if provider == "ollama":
            logger.debug(f"使用 Ollama 批量 Embedding: {provider_config['model']}")
            return await _ollama_embeddings_batch(texts, provider_config)
        
        elif provider == "gemini":
            if not provider_config.get("api_key"):
                raise RuntimeError("GEMINI_API_KEY 未配置，无法生成真实 Embedding")
            logger.debug(f"使用 Gemini 批量 Embedding: {provider_config['model']}")
            return await _gemini_embeddings_batch(texts, provider_config)
        
        elif provider in ("openai", "qwen", "zhipu", "siliconflow", "deepseek", "kimi"):
            if not provider_config.get("api_key"):
                raise RuntimeError(f"{provider.upper()}_API_KEY 未配置，无法生成真实 Embedding")
            logger.debug(f"使用 {provider} 批量 Embedding: {provider_config['model']}")
            return await _openai_compatible_embeddings_batch(texts, provider_config, batch_size)
        
        else:
            raise RuntimeError(f"未知 Embedding 提供者: {provider}")
            
    except Exception as e:
        logger.error(f"批量 Embedding 生成失败 ({provider}): {e}")
        raise
