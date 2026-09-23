"""
服务凭证加密（阶段 2.9 P0-1）。

- 算法：Fernet（AES-128-CBC + HMAC-SHA256，authenticated encryption，来自 cryptography）。
- 密钥：环境变量 CRM_CREDENTIAL_ENCRYPTION_KEY，必须是高强度 Fernet key
  （urlsafe base64 编码的 32 字节）；不接受低强度口令派生。
- 存储格式：`enc:v1:<ciphertext>`；旧明文记录读取到即迁移（不长期保留双格式）。
- 失败语义：缺密钥 / 错密钥 / 损坏密文均抛出 CredentialError（稳定 code），
  绝不把密文静默当明文使用，也绝不在日志/异常中输出原文或密文内容。
"""
from __future__ import annotations

import logging
import os

from cryptography.fernet import Fernet, InvalidToken

logger = logging.getLogger("crm.credentials")

ENCRYPTED_PREFIX = "enc:v1:"
ENV_KEY = "CRM_CREDENTIAL_ENCRYPTION_KEY"

ERR_MISSING_KEY = "MISSING_ENCRYPTION_KEY"
ERR_INVALID_KEY = "INVALID_ENCRYPTION_KEY"
ERR_DECRYPT_FAILED = "DECRYPT_FAILED"
ERR_TOKEN_NOT_SET = "TOKEN_NOT_SET"


class CredentialError(Exception):
    """凭证加密/解密失败。code 稳定，message 不含任何敏感内容。"""

    def __init__(self, code: str, message: str):
        super().__init__(message)
        self.code = code


def is_key_configured() -> bool:
    return bool(os.getenv(ENV_KEY, "").strip())


def _load_fernet() -> Fernet:
    raw = os.getenv(ENV_KEY, "").strip()
    if not raw:
        raise CredentialError(
            ERR_MISSING_KEY,
            f"缺少环境变量 {ENV_KEY}：存在加密凭证时必须配置密钥",
        )
    try:
        return Fernet(raw.encode())
    except Exception as exc:
        raise CredentialError(
            ERR_INVALID_KEY,
            f"环境变量 {ENV_KEY} 必须是合法的 Fernet key（urlsafe base64 编码的 32 字节）",
        ) from exc


def is_encrypted(stored: str | None) -> bool:
    return bool(stored) and stored.startswith(ENCRYPTED_PREFIX)


def encrypt_secret(plain: str) -> str:
    """明文 → enc:v1: 密文。plain 为空时抛错（调用方应避免存空 token）。"""
    if not plain:
        raise CredentialError(ERR_DECRYPT_FAILED, "不允许加密空凭证")
    token = _load_fernet().encrypt(plain.encode("utf-8"))
    return ENCRYPTED_PREFIX + token.decode("ascii")


def decrypt_secret(stored: str) -> str:
    """
    enc:v1: 密文 → 明文。
    缺密钥 / 错密钥 / 损坏密文 → CredentialError（不泄露密文与原文）。
    旧明文请走 resolve_secret（带迁移语义），不要直接调用本函数。
    """
    if not is_encrypted(stored):
        raise CredentialError(ERR_DECRYPT_FAILED, "密文格式不受支持")
    fernet = _load_fernet()  # 缺密钥在此抛出 MISSING_ENCRYPTION_KEY
    try:
        return fernet.decrypt(stored[len(ENCRYPTED_PREFIX):].encode("ascii")).decode("utf-8")
    except InvalidToken as exc:
        raise CredentialError(ERR_DECRYPT_FAILED, "凭证解密失败：密钥错误或密文已损坏") from exc
    except Exception as exc:
        raise CredentialError(ERR_DECRYPT_FAILED, "凭证解密失败：密文已损坏") from exc


def resolve_secret(stored: str | None) -> tuple[str | None, bool]:
    """
    读取配置中的 token：返回 (明文或 None, 是否为待迁移的旧明文)。
    - 密文 → 解密（失败抛 CredentialError）；
    - 旧明文 → 原样返回并标记 needs_migration=True，由调用方写回密文。
    """
    if not stored:
        return None, False
    if is_encrypted(stored):
        return decrypt_secret(stored), False
    logger.warning("检测到旧格式明文凭证，将在本次写回时迁移为密文")
    return stored, True
