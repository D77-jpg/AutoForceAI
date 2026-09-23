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

DEFAULT_TIMEOUT = (5, 15)  # (connect, read) 秒


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
        self.base_url = base_url.rstrip("/") + "/integrations/v1"
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

    def _request(self, method: str, path: str, *, params: dict | None = None,
                 json_body: dict | None = None, headers: dict | None = None) -> dict:
        url = f"{self.base_url}{path}"
        try:
            resp = self._session.request(
                method, url, params=params, json=json_body,
                headers=headers, timeout=self.timeout,
            )
        except (requests.ConnectionError, requests.Timeout) as exc:
            raise CrmApiError(f"CRM 不可达: {exc.__class__.__name__}", retryable=True) from exc

        request_id = resp.headers.get("X-Request-Id")
        try:
            payload = resp.json()
        except ValueError as exc:
            raise CrmApiError(
                f"CRM 返回非 JSON（HTTP {resp.status_code}）",
                http_status=resp.status_code,
                retryable=resp.status_code >= 500,
                request_id=request_id,
            ) from exc

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
