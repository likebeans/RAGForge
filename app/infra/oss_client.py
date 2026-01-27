# OSS 对象存储客户端
# 支持 MinIO / 阿里云 OSS / AWS S3

import logging
from abc import ABC, abstractmethod
from typing import BinaryIO
from io import BytesIO

logger = logging.getLogger(__name__)


class OSSClient(ABC):
    """OSS 客户端抽象基类"""
    
    @abstractmethod
    async def upload(self, key: str, data: bytes | BinaryIO, content_type: str | None = None) -> str:
        """
        上传文件
        
        Args:
            key: 对象键（路径）
            data: 文件内容
            content_type: MIME 类型
        
        Returns:
            OSS 路径（oss://bucket/key）
        """
        pass
    
    @abstractmethod
    async def download(self, key: str) -> bytes:
        """下载文件"""
        pass
    
    @abstractmethod
    async def delete(self, key: str) -> bool:
        """删除文件"""
        pass
    
    @abstractmethod
    async def exists(self, key: str) -> bool:
        """检查文件是否存在"""
        pass
    
    @abstractmethod
    async def get_url(self, key: str, expires: int = 3600) -> str:
        """获取预签名 URL"""
        pass
    
    @abstractmethod
    async def list_objects(self, prefix: str, max_keys: int = 100) -> list[str]:
        """列出对象"""
        pass


class MinioClient(OSSClient):
    """MinIO / S3 兼容客户端"""
    
    def __init__(self, endpoint: str, access_key: str, secret_key: str, bucket: str, secure: bool = False):
        """
        Args:
            endpoint: MinIO 服务地址（不含协议）
            access_key: Access Key
            secret_key: Secret Key
            bucket: 存储桶名称
            secure: 是否使用 HTTPS
        """
        from minio import Minio
        
        # 移除协议前缀
        endpoint_clean = endpoint.replace("http://", "").replace("https://", "")
        
        self.client = Minio(
            endpoint_clean,
            access_key=access_key,
            secret_key=secret_key,
            secure=secure or endpoint.startswith("https"),
        )
        self.bucket = bucket
        self._ensure_bucket()
        logger.info(f"MinIO 客户端初始化完成: {endpoint_clean}, bucket={bucket}")
    
    def _ensure_bucket(self):
        """确保存储桶存在"""
        try:
            if not self.client.bucket_exists(self.bucket):
                self.client.make_bucket(self.bucket)
                logger.info(f"创建存储桶: {self.bucket}")
        except Exception as e:
            logger.warning(f"检查/创建存储桶失败: {e}")
    
    async def upload(self, key: str, data: bytes | BinaryIO, content_type: str | None = None) -> str:
        """上传文件到 MinIO"""
        if isinstance(data, bytes):
            stream = BytesIO(data)
            length = len(data)
        else:
            # BinaryIO
            data.seek(0, 2)  # 移到末尾
            length = data.tell()
            data.seek(0)  # 移回开头
            stream = data
        
        self.client.put_object(
            self.bucket,
            key,
            stream,
            length,
            content_type=content_type or "application/octet-stream",
        )
        
        oss_path = f"oss://{self.bucket}/{key}"
        logger.debug(f"文件上传成功: {oss_path}")
        return oss_path
    
    async def download(self, key: str) -> bytes:
        """从 MinIO 下载文件"""
        response = self.client.get_object(self.bucket, key)
        try:
            return response.read()
        finally:
            response.close()
            response.release_conn()
    
    async def delete(self, key: str) -> bool:
        """删除 MinIO 对象"""
        try:
            self.client.remove_object(self.bucket, key)
            logger.debug(f"文件删除成功: {key}")
            return True
        except Exception as e:
            logger.warning(f"文件删除失败: {key}, {e}")
            return False
    
    async def exists(self, key: str) -> bool:
        """检查对象是否存在"""
        try:
            self.client.stat_object(self.bucket, key)
            return True
        except Exception:
            return False
    
    async def get_url(self, key: str, expires: int = 3600) -> str:
        """获取预签名下载 URL"""
        from datetime import timedelta
        return self.client.presigned_get_object(
            self.bucket,
            key,
            expires=timedelta(seconds=expires),
        )
    
    async def list_objects(self, prefix: str, max_keys: int = 100) -> list[str]:
        """列出指定前缀的对象"""
        objects = self.client.list_objects(self.bucket, prefix=prefix)
        result = []
        for obj in objects:
            result.append(obj.object_name)
            if len(result) >= max_keys:
                break
        return result


class AliyunOSSClient(OSSClient):
    """阿里云 OSS 客户端"""
    
    def __init__(self, endpoint: str, access_key: str, secret_key: str, bucket: str):
        """
        Args:
            endpoint: OSS 端点，如 https://oss-cn-hangzhou.aliyuncs.com
            access_key: Access Key ID
            secret_key: Access Key Secret
            bucket: 存储桶名称
        """
        try:
            import oss2
        except ImportError:
            raise ImportError("请安装 oss2: uv add oss2")
        
        self.auth = oss2.Auth(access_key, secret_key)
        self.bucket_client = oss2.Bucket(self.auth, endpoint, bucket)
        self.bucket_name = bucket
        logger.info(f"阿里云 OSS 客户端初始化完成: {endpoint}, bucket={bucket}")
    
    async def upload(self, key: str, data: bytes | BinaryIO, content_type: str | None = None) -> str:
        """上传文件到阿里云 OSS"""
        headers = {"Content-Type": content_type} if content_type else None
        self.bucket_client.put_object(key, data, headers=headers)
        return f"oss://{self.bucket_name}/{key}"
    
    async def download(self, key: str) -> bytes:
        """从阿里云 OSS 下载文件"""
        return self.bucket_client.get_object(key).read()
    
    async def delete(self, key: str) -> bool:
        """删除阿里云 OSS 对象"""
        try:
            self.bucket_client.delete_object(key)
            return True
        except Exception as e:
            logger.warning(f"文件删除失败: {key}, {e}")
            return False
    
    async def exists(self, key: str) -> bool:
        """检查对象是否存在"""
        return self.bucket_client.object_exists(key)
    
    async def get_url(self, key: str, expires: int = 3600) -> str:
        """获取预签名下载 URL"""
        return self.bucket_client.sign_url("GET", key, expires)
    
    async def list_objects(self, prefix: str, max_keys: int = 100) -> list[str]:
        """列出指定前缀的对象"""
        result = []
        for obj in self.bucket_client.list_objects(prefix=prefix, max_keys=max_keys).object_list:
            result.append(obj.key)
        return result


# 全局单例
_oss_client: OSSClient | None = None


def get_oss_client() -> OSSClient | None:
    """
    获取 OSS 客户端（单例模式）
    
    Returns:
        OSSClient 实例，如果 OSS 未启用则返回 None
    """
    global _oss_client
    
    if _oss_client is not None:
        return _oss_client
    
    from app.config import get_settings
    settings = get_settings()
    
    if not settings.oss_enabled:
        logger.debug("OSS 存储未启用")
        return None
    
    if not settings.oss_access_key or not settings.oss_secret_key:
        logger.warning("OSS Access Key 或 Secret Key 未配置")
        return None
    
    provider = settings.oss_provider.lower()
    
    if provider == "minio":
        _oss_client = MinioClient(
            endpoint=settings.oss_endpoint,
            access_key=settings.oss_access_key,
            secret_key=settings.oss_secret_key,
            bucket=settings.oss_bucket,
        )
    elif provider == "aliyun":
        _oss_client = AliyunOSSClient(
            endpoint=settings.oss_endpoint,
            access_key=settings.oss_access_key,
            secret_key=settings.oss_secret_key,
            bucket=settings.oss_bucket,
        )
    else:
        raise ValueError(f"不支持的 OSS 提供商: {provider}，支持: minio, aliyun")
    
    return _oss_client


def reset_oss_client():
    """重置 OSS 客户端（用于测试）"""
    global _oss_client
    _oss_client = None
