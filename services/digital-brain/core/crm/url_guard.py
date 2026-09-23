"""
CRM 地址安全校验（阶段 2.9 P0-3）：SSRF 防护。

规则：
- 仅 http/https；拒绝 userinfo、fragment、非预期端口；
- 生产（APP_ENV=production）只允许 HTTPS；开发环境允许 localhost/127.0.0.1/::1 的 http；
- 非 localhost 主机必须在 CRM_ALLOWED_HOSTS（逗号分隔 host[:port]）中显式列出；
- DNS 解析后的所有 IP 必须是公网地址（拦截私网/回环/链路本地/云元数据 169.254.169.254），
  除非该主机已显式列入 allowlist 或为开发环境 localhost；
- 重定向目标按同一套规则逐跳校验。

所有拒绝都抛出 UrlGuardError（稳定 code），不泄露解析细节之外的敏感信息。
"""
from __future__ import annotations

import ipaddress
import logging
import os
import socket
from urllib.parse import urljoin, urlsplit

logger = logging.getLogger("crm.url_guard")

ALLOWED_HOSTS_ENV = "CRM_ALLOWED_HOSTS"
APP_ENV_ENV = "APP_ENV"

LOCALHOST_NAMES = {"localhost", "localhost.localdomain"}
DEFAULT_PORTS = {"http": 80, "https": 443}


class UrlGuardError(ValueError):
    """URL 未通过安全校验。code 稳定，message 面向管理员。"""

    def __init__(self, code: str, message: str):
        super().__init__(message)
        self.code = code


def _is_production() -> bool:
    return os.getenv(APP_ENV_ENV, "development").strip().lower() == "production"


def _allowlist() -> dict[str, int | None]:
    """CRM_ALLOWED_HOSTS → {host: port|None}（小写）。"""
    raw = os.getenv(ALLOWED_HOSTS_ENV, "")
    entries: dict[str, int | None] = {}
    for item in raw.split(","):
        item = item.strip().lower()
        if not item:
            continue
        if ":" in item and not item.startswith("["):  # host:port
            host, _, port = item.rpartition(":")
            try:
                entries[host] = int(port)
            except ValueError:
                entries[item] = None
        else:
            entries[item.strip("[]")] = None
    return entries


def _is_localhost(host: str) -> bool:
    if host in LOCALHOST_NAMES:
        return True
    try:
        return ipaddress.ip_address(host.strip("[]")).is_loopback
    except ValueError:
        return False


def _resolve_ips(host: str) -> list[ipaddress._BaseAddress]:
    try:
        infos = socket.getaddrinfo(host, None)
    except socket.gaierror as exc:
        raise UrlGuardError("URL_DNS", f"主机名无法解析: {host}") from exc
    ips = []
    for info in infos:
        try:
            ips.append(ipaddress.ip_address(info[4][0]))
        except ValueError:
            continue
    return ips


def _check_resolved_ips(host: str, *, trusted: bool, literal_ip_allowed: bool, dev_local: bool) -> None:
    """
    解析 IP 检查：
    - 回环/链路本地（含云元数据 169.254.169.254）/未指定/组播/保留地址：一律拒绝，
      除非该字面 IP 被显式列入 allowlist，或为开发环境 localhost；
    - 其它非公网地址（私网 10/8 等）：仅显式 allowlist（trusted）可放行；
    - DNS 解析失败：trusted 主机放行（连接阶段自然失败），非 trusted 拒绝。
    """
    if dev_local:
        return
    try:
        ips = [ipaddress.ip_address(host.strip("[]"))]
    except ValueError:
        try:
            ips = _resolve_ips(host)
        except UrlGuardError:
            if trusted:
                return
            raise
    if not ips:
        if trusted:
            return
        raise UrlGuardError("URL_DNS", f"主机名无可用解析结果: {host}")
    for ip in ips:
        hard_bad = ip.is_loopback or ip.is_link_local or ip.is_unspecified or ip.is_multicast or ip.is_reserved
        if hard_bad and not literal_ip_allowed:
            raise UrlGuardError(
                "URL_PRIVATE_IP",
                f"目标主机解析到回环/链路本地/保留地址（{host}）：云元数据与本地服务地址未获授权",
            )
        if not ip.is_global and not trusted:
            raise UrlGuardError(
                "URL_PRIVATE_IP",
                f"目标主机解析到非公网地址（{host}）：私网地址需显式列入 {ALLOWED_HOSTS_ENV}",
            )


def validate_crm_url(url: str) -> str:
    """校验并规范化 CRM 地址；失败抛 UrlGuardError。"""
    raw = (url or "").strip()
    if not raw:
        raise UrlGuardError("URL_EMPTY", "地址不能为空")
    try:
        parts = urlsplit(raw)
    except ValueError as exc:
        raise UrlGuardError("URL_INVALID", f"地址无法解析: {exc}") from exc

    scheme = parts.scheme.lower()
    if scheme not in ("http", "https"):
        raise UrlGuardError("URL_SCHEME", "仅允许 http/https（file:// 等协议被拒绝）")
    if parts.username or parts.password:
        raise UrlGuardError("URL_USERINFO", "地址不允许携带用户名/口令")
    if parts.fragment:
        raise UrlGuardError("URL_INVALID", "地址不允许携带 fragment")

    host = (parts.hostname or "").lower()
    if not host:
        raise UrlGuardError("URL_HOST", "地址缺少主机名")
    try:
        port = parts.port or DEFAULT_PORTS[scheme]
    except ValueError as exc:
        raise UrlGuardError("URL_PORT", f"非法端口: {exc}") from exc

    prod = _is_production()
    localhost = _is_localhost(host)
    allowlist = _allowlist()
    allowed_port = allowlist.get(host)
    explicitly_allowed = host in allowlist

    if prod and scheme != "https":
        raise UrlGuardError("URL_SCHEME", "生产环境仅允许 HTTPS 地址")

    if localhost:
        if prod and not explicitly_allowed:
            raise UrlGuardError("URL_NOT_ALLOWED", "生产环境不允许 localhost/回环地址（除非显式列入 allowlist 且使用 HTTPS）")
        # 开发环境 localhost：端口不限（本地服务端口多变）
    else:
        if not explicitly_allowed:
            raise UrlGuardError(
                "URL_NOT_ALLOWED",
                f"主机 {host} 不在 {ALLOWED_HOSTS_ENV} 白名单中",
            )
        if allowed_port is not None and port != allowed_port:
            raise UrlGuardError("URL_PORT", f"端口 {port} 与白名单条目（:{allowed_port}）不符")
        if allowed_port is None and port != DEFAULT_PORTS[scheme]:
            raise UrlGuardError("URL_PORT", f"非标准端口 {port} 未获授权（白名单可写 host:port 显式放行）")

    # 字面 IP 显式列入 allowlist = 运维对该确切地址的显式授权
    literal_ip_allowed = False
    try:
        literal_ip_allowed = ipaddress.ip_address(host.strip("[]")) and explicitly_allowed
    except ValueError:
        literal_ip_allowed = False

    _check_resolved_ips(
        host,
        trusted=explicitly_allowed,
        literal_ip_allowed=bool(literal_ip_allowed),
        dev_local=localhost and not prod,
    )

    # 规范化：小写 scheme/host，IPv6 加方括号，去掉末尾斜杠，保留 path/query
    display_host = f"[{host}]" if ":" in host else host
    netloc = display_host
    if port != DEFAULT_PORTS[scheme]:
        netloc = f"{display_host}:{port}"
    normalized = f"{scheme}://{netloc}{parts.path.rstrip('/')}"
    if parts.query:
        normalized += f"?{parts.query}"
    return normalized


def validate_redirect_location(current_url: str, location: str) -> str:
    """校验 3xx Location（支持相对跳转）；返回规范化后的绝对地址。"""
    if not location:
        raise UrlGuardError("URL_REDIRECT", "重定向缺少 Location")
    absolute = urljoin(current_url, location)
    try:
        return validate_crm_url(absolute)
    except UrlGuardError as exc:
        raise UrlGuardError(exc.code, f"重定向目标被拒绝：{exc}") from exc
