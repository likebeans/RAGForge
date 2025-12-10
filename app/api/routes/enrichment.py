"""
增强预览 API 路由

提供文档摘要和 Chunk 增强的预览功能，
允许用户在入库前预览增强效果。
"""

import logging

from fastapi import APIRouter, Depends, HTTPException, status

from app.api.deps import get_tenant, require_role, APIKeyContext
from app.schemas.document import (
    PreviewSummaryRequest,
    PreviewSummaryResponse,
    PreviewChunkEnrichmentRequest,
    PreviewChunkEnrichmentResponse,
    EnrichedChunkResult,
)
from app.pipeline.enrichers.summarizer import DocumentSummarizer
from app.pipeline.enrichers.chunk_enricher import ChunkEnricher

logger = logging.getLogger(__name__)

router = APIRouter(tags=["Enrichment Preview"])


@router.post(
    "/v1/enrichment/preview-summary",
    response_model=PreviewSummaryResponse,
    summary="预览文档摘要",
    description="使用 LLM 生成文档摘要的预览，不会持久化存储。"
)
async def preview_summary(
    payload: PreviewSummaryRequest,
    tenant=Depends(get_tenant),
    context: APIKeyContext = Depends(require_role("admin", "write")),
):
    """
    预览文档摘要生成效果
    
    - 调用 LLM 生成摘要
    - 不会持久化存储
    - 用于入库前预览增强效果
    """
    try:
        logger.info(f"开始生成摘要，内容长度: {len(payload.content)}")
        
        summarizer = DocumentSummarizer(
            min_tokens=0,  # 预览时不限制最小长度
            max_tokens=payload.max_tokens,
        )
        
        # 使用异步方法
        summary = await summarizer.agenerate(content=payload.content)
        
        logger.info(f"摘要生成结果: {summary[:100] if summary else 'None'}...")
        
        if not summary:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail={"code": "SUMMARY_FAILED", "detail": "摘要生成失败，LLM 返回空结果"}
            )
        
        return PreviewSummaryResponse(
            summary=summary,
            content_length=len(payload.content),
            summary_length=len(summary),
        )
        
    except HTTPException:
        # 直接重新抛出 HTTPException，不重复包装
        raise
    except ValueError as e:
        # LLM 未配置等错误
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail={"code": "LLM_NOT_CONFIGURED", "detail": str(e)}
        )
    except Exception as e:
        logger.error(f"预览摘要失败: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={"code": "PREVIEW_FAILED", "detail": str(e)}
        )


@router.post(
    "/v1/enrichment/preview-chunk-enrichment",
    response_model=PreviewChunkEnrichmentResponse,
    summary="预览 Chunk 增强",
    description="使用 LLM 增强 Chunk 上下文的预览，不会持久化存储。"
)
async def preview_chunk_enrichment(
    payload: PreviewChunkEnrichmentRequest,
    tenant=Depends(get_tenant),
    context: APIKeyContext = Depends(require_role("admin", "write")),
):
    """
    预览 Chunk 增强效果
    
    - 最多支持 5 个 chunks 的预览
    - 调用 LLM 进行上下文增强
    - 不会持久化存储
    """
    try:
        enricher = ChunkEnricher(
            max_tokens=payload.max_tokens,
            context_chunks=1,
        )
        
        results: list[EnrichedChunkResult] = []
        succeeded = 0
        failed = 0
        
        # 构建 chunk 数据
        chunk_data = [
            {"text": text, "chunk_index": idx}
            for idx, text in enumerate(payload.chunks)
        ]
        
        # 批量增强
        try:
            enriched_results = await enricher.enrich_chunks(
                chunks=chunk_data,
                doc_title=payload.doc_title or "未命名文档",
                doc_summary=payload.doc_summary,
            )
            
            for i, (original, enriched) in enumerate(zip(payload.chunks, enriched_results)):
                enriched_text = enriched.get("enriched_text", "")
                enrichment_status = enriched.get("enrichment_status", "failed")
                
                if enrichment_status == "completed" and enriched_text:
                    succeeded += 1
                else:
                    failed += 1
                    enriched_text = original  # 失败时返回原文
                    enrichment_status = "failed"
                
                results.append(EnrichedChunkResult(
                    original_text=original,
                    enriched_text=enriched_text,
                    status=enrichment_status,
                ))
                
        except Exception as e:
            logger.warning(f"批量增强失败: {e}")
            # 回退到逐个增强
            for i, text in enumerate(payload.chunks):
                try:
                    # 构建上下文
                    preceding = payload.chunks[:i] if i > 0 else []
                    succeeding = payload.chunks[i+1:i+2] if i+1 < len(payload.chunks) else []
                    
                    enriched_text = enricher.enrich(
                        chunk_text=text,
                        doc_title=payload.doc_title or "未命名文档",
                        doc_summary=payload.doc_summary,
                        preceding_chunks=preceding[-1:],
                        succeeding_chunks=succeeding,
                    )
                    
                    if enriched_text:
                        results.append(EnrichedChunkResult(
                            original_text=text,
                            enriched_text=enriched_text,
                            status="completed",
                        ))
                        succeeded += 1
                    else:
                        results.append(EnrichedChunkResult(
                            original_text=text,
                            enriched_text=text,
                            status="skipped",
                        ))
                        failed += 1
                except Exception as chunk_err:
                    logger.warning(f"Chunk {i} 增强失败: {chunk_err}")
                    results.append(EnrichedChunkResult(
                        original_text=text,
                        enriched_text=text,
                        status="failed",
                    ))
                    failed += 1
        
        return PreviewChunkEnrichmentResponse(
            results=results,
            total=len(payload.chunks),
            succeeded=succeeded,
            failed=failed,
        )
        
    except ValueError as e:
        # LLM 未配置等错误
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail={"code": "LLM_NOT_CONFIGURED", "detail": str(e)}
        )
    except Exception as e:
        logger.error(f"预览 Chunk 增强失败: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={"code": "PREVIEW_FAILED", "detail": str(e)}
        )
