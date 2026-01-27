"""API Key 加密工具"""

import base64
import os
from cryptography.fernet import Fernet
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC

from app.config import get_settings

settings = get_settings()


def _get_fernet() -> Fernet:
    """获取 Fernet 加密器"""
    encryption_key = settings.api_key_encryption_key
    if not encryption_key:
        raise ValueError("API_KEY_ENCRYPTION_KEY not configured")
    
    # 使用 PBKDF2 从密码派生密钥
    salt = b'yaoyan_api_key_salt'  # 固定 salt，生产环境建议存储随机 salt
    kdf = PBKDF2HMAC(
        algorithm=hashes.SHA256(),
        length=32,
        salt=salt,
        iterations=100000,
    )
    key = base64.urlsafe_b64encode(kdf.derive(encryption_key.encode()))
    return Fernet(key)


def encrypt_api_key(api_key: str) -> str:
    """加密 API Key"""
    fernet = _get_fernet()
    encrypted = fernet.encrypt(api_key.encode())
    return base64.urlsafe_b64encode(encrypted).decode()


def decrypt_api_key(encrypted_key: str) -> str:
    """解密 API Key"""
    fernet = _get_fernet()
    encrypted = base64.urlsafe_b64decode(encrypted_key.encode())
    decrypted = fernet.decrypt(encrypted)
    return decrypted.decode()
