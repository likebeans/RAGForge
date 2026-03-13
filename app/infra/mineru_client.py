# MinerU PDF 解析服务客户端

import httpx
import logging
from typing import Any

logger = logging.getLogger(__name__)


class MinerUClient:
    """MinerU PDF 解析服务客户端"""
    
    def __init__(self, base_url: str, timeout: int = 300, api_key: str | None = None):
        """
        Args:
            base_url: MinerU 服务地址，如 http://localhost:8010
            timeout: 请求超时时间（秒），PDF 解析可能较慢
            api_key: API Key（可选，用于云服务认证）
        """
        self.base_url = base_url.rstrip("/")
        self.timeout = httpx.Timeout(float(timeout))
        self.api_key = api_key
    
    async def parse_pdf(
        self,
        file_bytes: bytes,
        filename: str,
        backend: str = "hybrid-auto-engine",
        parse_method: str = "auto",
        lang_list: list[str] = None,
        return_md: bool = True,
        table_enable: bool = True,
        formula_enable: bool = True,
        start_page_id: int = 0,
        end_page_id: int = 99999,
    ) -> dict[str, Any]:
        """
        调用 MinerU 解析 PDF
        
        Args:
            file_bytes: PDF 文件二进制
            filename: 文件名
            backend: 解析后端（hybrid-auto-engine/pipeline/vlm-auto-engine等）
            parse_method: 解析方法（auto/txt/ocr）
            lang_list: 语言列表，默认["ch"]
            return_md: 是否返回markdown内容
            table_enable: 是否启用表格解析
            formula_enable: 是否启用公式解析
            start_page_id: 起始页码（从0开始）
            end_page_id: 结束页码（从0开始）
        
        Returns:
            {
                "markdown": "...",          # Markdown 格式全文
                "blocks": [...],            # 分块内容
                "tables": [...],            # 表格数据
                "page_count": 10,           # 页数
            }
        """
        # 构建请求头（如果有 API Key）
        headers = {}
        if self.api_key:
            headers["Authorization"] = f"Bearer {self.api_key}"
        
        # 默认语言列表
        if lang_list is None:
            lang_list = ["ch"]
        
        async with httpx.AsyncClient(timeout=self.timeout, headers=headers) as client:
            # 使用正确的API格式 - files数组形式
            files = {"files": (filename, file_bytes, "application/pdf")}
            data = {
                "backend": backend,
                "parse_method": parse_method,
                "lang_list": lang_list,
                "return_md": str(return_md).lower(),
                "table_enable": str(table_enable).lower(),
                "formula_enable": str(formula_enable).lower(),
                "start_page_id": start_page_id,
                "end_page_id": end_page_id,
            }
            
            try:
                # 使用正确的 MinerU API 端点
                response = await client.post(
                    f"{self.base_url}/file_parse",
                    files=files,
                    data=data,
                )
                response.raise_for_status()
                result = response.json()
                
                logger.info(
                    f"MinerU 解析完成: {filename}, "
                    f"后端: {backend}, "
                    f"结果键: {list(result.keys())}"
                )
                return self._normalize_result(result, filename)
                
            except httpx.HTTPStatusError as e:
                logger.error(f"MinerU 服务返回错误: {e.response.status_code} - {e.response.text[:200]}")
                raise ValueError(f"MinerU 解析失败: HTTP {e.response.status_code}")
            
            except httpx.ConnectError:
                logger.error(f"无法连接 MinerU 服务: {self.base_url}")
                raise ValueError(f"无法连接 MinerU 服务: {self.base_url}")
            
            except httpx.TimeoutException:
                logger.error(f"MinerU 服务响应超时: {self.timeout.read}s")
                raise ValueError("MinerU 服务响应超时，请增加超时时间或减小文件大小")
    
    async def _try_alternative_api(
        self,
        client: httpx.AsyncClient,
        files: dict,
        data: dict,
        filename: str,
    ) -> dict[str, Any]:
        """尝试备用 API 路径（兼容不同版本的 MinerU）"""
        alternative_paths = [
            "/parse",
            "/api/parse",
            "/v1/parse",
            "/pdf/parse",
        ]
        
        for path in alternative_paths:
            try:
                response = await client.post(
                    f"{self.base_url}{path}",
                    files=files,
                    data=data,
                )
                if response.status_code == 200:
                    result = response.json()
                    logger.info(f"MinerU 备用 API 成功: {path}")
                    return self._normalize_result(result)
            except Exception:
                continue
        
        raise ValueError("MinerU API 不可用，已尝试所有路径")
    
    def _normalize_result(self, result: dict, filename: str = "") -> dict[str, Any]:
        """规范化 MinerU 返回结果"""
        normalized = {
            "markdown": "",
            "blocks": [],
            "tables": [],
            "page_count": 0,
        }
        
        # 处理新的 MinerU API 返回格式
        # 格式: {"backend": "...", "version": "...", "results": {"filename": {...}}}
        if "results" in result and isinstance(result["results"], dict):
            # 查找文件名对应的解析结果
            file_key = None
            for key in result["results"]:
                if filename in key or key in filename:
                    file_key = key
                    break
            
            if file_key and result["results"][file_key]:
                file_result = result["results"][file_key]
                
                # 提取markdown内容
                if "md_content" in file_result:
                    normalized["markdown"] = file_result["md_content"]
                elif "markdown" in file_result:
                    normalized["markdown"] = file_result["markdown"]
                elif "content" in file_result:
                    normalized["markdown"] = file_result["content"]
                elif "text" in file_result:
                    normalized["markdown"] = file_result["text"]
                
                # 提取blocks
                if "blocks" in file_result:
                    normalized["blocks"] = file_result["blocks"]
                elif "elements" in file_result:
                    normalized["blocks"] = [
                        {
                            "type": elem.get("type", "text"),
                            "content": elem.get("text", elem.get("content", "")),
                            "page": elem.get("page", elem.get("page_number")),
                            "bbox": elem.get("bbox", elem.get("bounding_box")),
                            "table_data": elem.get("table_data"),
                        }
                        for elem in file_result["elements"]
                    ]
                
                # 提取tables
                if "tables" in file_result:
                    normalized["tables"] = file_result["tables"]
                
                # 提取page_count
                if "page_count" in file_result:
                    normalized["page_count"] = file_result["page_count"]
                elif "pages" in file_result:
                    normalized["page_count"] = len(file_result["pages"])
                elif "num_pages" in file_result:
                    normalized["page_count"] = file_result["num_pages"]
                    
        else:
            # 兼容旧的返回格式
            if "markdown" in result:
                normalized["markdown"] = result["markdown"]
            elif "content" in result:
                normalized["markdown"] = result["content"]
            elif "text" in result:
                normalized["markdown"] = result["text"]
            
            if "blocks" in result:
                normalized["blocks"] = result["blocks"]
            elif "elements" in result:
                normalized["blocks"] = [
                    {
                        "type": elem.get("type", "text"),
                        "content": elem.get("text", elem.get("content", "")),
                        "page": elem.get("page", elem.get("page_number")),
                        "bbox": elem.get("bbox", elem.get("bounding_box")),
                        "table_data": elem.get("table_data"),
                    }
                    for elem in result["elements"]
                ]
            
            if "tables" in result:
                normalized["tables"] = result["tables"]
            
            if "page_count" in result:
                normalized["page_count"] = result["page_count"]
            elif "pages" in result:
                normalized["page_count"] = len(result["pages"])
            elif "num_pages" in result:
                normalized["page_count"] = result["num_pages"]
        
        return normalized
    
    async def health_check(self) -> bool:
        """检查 MinerU 服务是否可用"""
        async with httpx.AsyncClient(timeout=httpx.Timeout(5.0)) as client:
            try:
                # 尝试多个健康检查路径
                for path in ["/health", "/api/health", "/", "/api/v1/health"]:
                    try:
                        response = await client.get(f"{self.base_url}{path}")
                        if response.status_code == 200:
                            return True
                    except Exception:
                        continue
                return False
            except Exception:
                return False
    
    async def get_service_info(self) -> dict | None:
        """获取 MinerU 服务信息"""
        async with httpx.AsyncClient(timeout=httpx.Timeout(5.0)) as client:
            try:
                response = await client.get(f"{self.base_url}/api/v1/info")
                if response.status_code == 200:
                    return response.json()
            except Exception:
                pass
            return None
