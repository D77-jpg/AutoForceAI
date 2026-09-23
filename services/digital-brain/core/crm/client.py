"""
GenesisCRMClient —— Genesis Integration API v1 客户端（阶段 2 Wave B）。

- 只做 HTTP 调用与契约校验（pydantic），不做重试决策；
  重试/退避/死信由投递器（Wave C 的 crm dispatcher）依据 CrmApiError.retryable 决定。
- 永不记录 token；日志与异常信息只包含稳定错误码与 requestId。
"""
from __future__ import annotations

from typing import Optional

import requests

from core.crm.contract import (
    CONTRACT_VERSION,
    ApiErrorResponse,
    CustomerQuotationsResponse,
    CustomerStatusResponse,
    CustomerUpsertRequest,
    CustomerUpsertResponse,
    HealthResponse,
    OutcomeFeedResponse,
    StatsOverviewResponse,
)
from core.crm.url_guard import UrlGuardError, validate_crm_url, validate_redirect_location

DEFAULT_TIMEOUT = (5, 15)  # (connect, read) 秒
MAX_REDIRECTS = 5
MAX_RESPONSE_BYTES = 2 * 1024 * 1024  # 2MB 响应体上限（防内存耗尽）
_REDIRECT_STATUSES = {301, 302, 303, 307, 308}


class CrmApiError(Exception):
    """CRM API 调用失败。retryable 供投递器分类：True 可退避重试，False 直接死信/停投。"""

    def __init__(
        self,
        message: str,
        *,
        code: Optional[str] = None,
        http_status: Optional[int] = None,
        retryable: bool = False,
        auth_invalid: bool = False,
        request_id: Optional[str] = None,
    ):
        super().__init__(message)
        self.code = code
        self.http_status = http_status
        self.retryable = retryable
        self.auth_invalid = auth_invalid  # 401/403：配置失效，暂停该组织新投递
        self.request_id = request_id


class GenesisCRMClient:
    """契约版本固定 v1.0；base_url 例如 http://localhost:5000/api"""
    def __init__(
        self,
        base_url: str,
        service_token: str,
        project_id: str,
        *,
        timeout: tuple[int, int] = DEFAULT_TIMEOUT,
        session: Optional[requests.Session] = None,
    ):
        # SSRF 防护（P0-3）：base_url 必须先过 allowlist/HTTPS/私网校验
        self.base_url = validate_crm_url(base_url) + "/integrations/v1"
        self.project_id = project_id
        self.timeout = timeout
        self._session = session or requests.Session()
        self._session.headers.update(
            {
                "Authorization": f"Bearer {service_token}",
                "X-Project-Id": project_id,
                "Content-Type": "application/json",
            }
        )

    # ---------- 内部 ----------

    def _send_once(self, method: str, url: str, *, params, json_body, headers) -> requests.Response:
        return self._session.request(
            method, url, params=params, json=json_body,
            headers=headers, timeout=self.timeout, allow_redirects=False, stream=True,
        )

    def _read_limited(self, resp: requests.Response) -> bytes:
        """限制响应体大小，防止异常对端耗尽内存。"""
        chunks, size = [], 0
        for chunk in resp.iter_content(chunk_size=65536):
            size += len(chunk)
            if size > MAX_RESPONSE_BYTES:
                resp.close()
                raise CrmApiError(
                    "CRM 响应体超过大小上限",
                    http_status=resp.status_code, retryable=False,
                )
            chunks.append(chunk)
        return b"".join(chunks)

    def _request(self, method: str, path: str, *, params: dict | None = None,
                 json_body: dict | None = None, headers: dict | None = None) -> dict:
        url = f"{self.base_url}{path}"
        # 手动跟随重定向：每一跳都过 SSRF 校验（防 302 跳转到内网/元数据地址）
        for _ in range(MAX_REDIRECTS + 1):
            try:
                resp = self._send_once(method, url, params=params, json_body=json_body, headers=headers)
            except (requests.ConnectionError, requests.Timeout) as exc:
                raise CrmApiError(f"CRM 不可达: {exc.__class__.__name__}", retryable=True) from exc
            if resp.status_code not in _REDIRECT_STATUSES:
                break
            try:
                location = resp.headers.get("Location")
                url = validate_redirect_location(url, location or "")
            except UrlGuardError as exc:
                resp.close()
                raise CrmApiError(str(exc), code=exc.code, retryable=False) from exc
            finally:
                resp.close()
            # 301/302/303 语义上转 GET（去掉 body）；307/308 保持原方法与载荷
            if resp.status_code in (301, 302, 303) and method != "GET":
                method, json_body = "GET", None
        else:
            raise CrmApiError("CRM 重定向次数过多", code="TOO_MANY_REDIRECTS", retryable=False)

        request_id = resp.headers.get("X-Request-Id")
        try:
            import json as _json
            payload = _json.loads(self._read_limited(resp))
        except CrmApiError:
            raise
        except ValueError as exc:
            raise CrmApiError(
                f"CRM 返回非 JSON（HTTP {resp.status_code}）",
                http_status=resp.status_code,
                retryable=resp.status_code >= 500,
                request_id=request_id,
            ) from exc
        finally:
            resp.close()

        if resp.status_code >= 400:
            code, message = None, f"HTTP {resp.status_code}"
            parsed_err = ApiErrorResponse.model_validate(payload) if isinstance(payload, dict) and "error" in payload else None
            if parsed_err:
                code = parsed_err.error.code
                message = parsed_err.error.message
                request_id = request_id or parsed_err.error.requestId
            retryable = (
                resp.status_code in (408, 429) or resp.status_code >= 500
            )
            raise CrmApiError(
                message,
                code=code,
                http_status=resp.status_code,
                retryable=retryable,
                auth_invalid=resp.status_code in (401, 403),
                request_id=request_id,
            )

        if not isinstance(payload, dict) or payload.get("success") is not True:
            raise CrmApiError("CRM 响应缺少 success:true 包装", http_status=resp.status_code,
                              retryable=False, request_id=request_id)
        return payload["data"]

    # ---------- v1 端点 ----------

    def health(self) -> HealthResponse:
        data = self._request("GET", "/health")
        resp = HealthResponse.model_validate(data)
        if resp.contractVersion != CONTRACT_VERSION:
            raise CrmApiError(
                f"契约版本不匹配: CRM={resp.contractVersion}, 本地={CONTRACT_VERSION}",
                code="UNSUPPORTED_CONTRACT_VERSION",
            )
        if resp.projectId != self.project_id:
            raise CrmApiError("health 返回的项目与配置不一致", code="PROJECT_MISMATCH")
        return resp

    def upsert_customer(self, body: CustomerUpsertRequest, idempotency_key: str) -> CustomerUpsertResponse:
        if body.schemaVersion != CONTRACT_VERSION:
            raise ValueError(f"schemaVersion 必须为 {CONTRACT_VERSION}")
        data = self._request(
            "POST", "/customers/upsert",
            json_body=body.model_dump(exclude_none=True),
            headers={"Idempotency-Key": idempotency_key},
        )
        return CustomerUpsertResponse.model_validate(data)

    def fetch_outcomes(self, cursor: Optional[str] = None, limit: int = 50) -> OutcomeFeedResponse:
        params: dict = {"limit": limit}
        if cursor:
            params["cursor"] = cursor
        data = self._request("GET", "/outcomes", params=params)
        return OutcomeFeedResponse.model_validate(data)

    def stats_overview(self) -> StatsOverviewResponse:
        return StatsOverviewResponse.model_validate(self._request("GET", "/stats/overview"))

    def get_customer_status(self, external_ref: str) -> CustomerStatusResponse:
        return CustomerStatusResponse.model_validate(
            self._request("GET", f"/customers/{requests.utils.quote(external_ref, safe='')}")
        )

    def get_customer_quotations(self, external_ref: str) -> CustomerQuotationsResponse:
        return CustomerQuotationsResponse.model_validate(
            self._request("GET", f"/customers/{requests.utils.quote(external_ref, safe='')}/quotations")
        )


def client_from_config(cfg, *, session: Optional[requests.Session] = None,
                       db=None) -> GenesisCRMClient:
    """
    从集成配置构建客户端（唯一入口）：解密 token，必要时把旧明文迁移为密文。
    - 缺密钥 / 错密钥 / 损坏密文 → 抛 core.credentials.CredentialError；
    - 传入 db 时，旧明文会在本次事务中迁移为密文（由调用方 commit）。
    """
    from core.credentials import ERR_TOKEN_NOT_SET, CredentialError

    if db is not None:
        cfg.migrate_token_if_legacy()
    token = cfg.get_service_token()
    if not token:
        raise CredentialError(ERR_TOKEN_NOT_SET, "尚未配置服务凭证")
    try:
        return GenesisCRMClient(cfg.base_url, token, cfg.project_id, session=session)
    except UrlGuardError as exc:
        # URL 未通过安全校验：按配置不可用处理（暂停投递/回流，等管理员修正）
        raise CredentialError(exc.code, f"CRM 地址未通过安全校验：{exc}") from exc
