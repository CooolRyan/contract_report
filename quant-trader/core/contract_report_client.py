"""
Spring Backend(contract-report) 연동: 계좌 연동, 체결 등록, 성과 온체인 커밋.

quant-trader 가 체결 후 자동으로 POST /api/kiwoom/register 하고,
Cron 등으로 POST /api/performance/commit 을 호출할 수 있다.

our_account_id 는 Java String.hashCode() 와 Python hash() 가 달라서
반드시 POST /api/kiwoom/link 응답의 ourAccountId 를 사용한다.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from datetime import datetime
from typing import Any

import requests

from core.portfolio import TradeRecord

log = logging.getLogger(__name__)


@dataclass
class ContractReportClient:
    """백엔드 base URL + 사용자 식별자."""

    base_url: str
    user_id: str
    kiwoom_account_no: str
    timeout_sec: float = 30.0
    _our_account_id: str | None = None

    def __post_init__(self) -> None:
        self.base_url = self.base_url.rstrip("/")

    def ensure_link(self) -> str:
        """POST /api/kiwoom/link → ourAccountId 캐시 후 반환."""
        if self._our_account_id:
            return self._our_account_id
        url = f"{self.base_url}/api/kiwoom/link"
        payload = {"userId": self.user_id, "kiwoomAccountNo": self.kiwoom_account_no}
        r = requests.post(url, json=payload, timeout=self.timeout_sec)
        r.raise_for_status()
        data = r.json()
        self._our_account_id = data.get("ourAccountId") or data.get("our_account_id")
        if not self._our_account_id:
            raise RuntimeError(f"link 응답에 ourAccountId 없음: {data}")
        log.info("[ContractReport] 연동됨 ourAccountId=%s", self._our_account_id)
        return self._our_account_id

    def register_trade_record(self, rec: TradeRecord) -> None:
        """체결 한 건을 trades 테이블에 등록 (전략 태그 포함)."""
        self.ensure_link()
        trade_json = _trade_record_to_kiwoom_body(rec, self.kiwoom_account_no)
        url = f"{self.base_url}/api/kiwoom/register"
        payload = {
            "userId": self.user_id,
            "kiwoomAccountNo": self.kiwoom_account_no,
            "trades": [trade_json],
        }
        r = requests.post(url, json=payload, timeout=self.timeout_sec)
        if not r.ok:
            log.error(
                "[ContractReport] register 실패 %s %s",
                r.status_code,
                r.text[:500],
            )
            r.raise_for_status()
        data = r.json()
        log.debug("[ContractReport] register 응답: %s", data)

    def commit_performance(
        self,
        start: datetime,
        end: datetime,
        strategy_tag: str | None = None,
    ) -> dict[str, Any]:
        """POST /api/performance/commit — 기간·전략별 성과 해시 온체인 커밋."""
        account_id = self.ensure_link()
        url = f"{self.base_url}/api/performance/commit"
        body: dict[str, Any] = {
            "accountId": account_id,
            "start": _iso_local(start),
            "end": _iso_local(end),
        }
        if strategy_tag:
            body["strategyTag"] = strategy_tag
        r = requests.post(url, json=body, timeout=self.timeout_sec)
        if not r.ok:
            log.error(
                "[ContractReport] commit 실패 %s %s",
                r.status_code,
                r.text[:500],
            )
            r.raise_for_status()
        return r.json()


def _iso_local(dt: datetime) -> str:
    """Spring @DateTimeFormat ISO.DATE_TIME 과 호환되도록."""
    if dt.tzinfo is not None:
        dt = dt.replace(tzinfo=None)
    return dt.isoformat()


def _trade_record_to_kiwoom_body(rec: TradeRecord, account_no: str) -> dict[str, Any]:
    """KiwoomTradeDto JSON (camelCase) 필드."""
    t = rec.timestamp
    trade_dt = t.isoformat(sep="T", timespec="seconds")
    exec_id = rec.order_id + "_fill" if rec.order_id else f"local_{int(t.timestamp())}"
    tag = (rec.strategy_tag or "").strip()
    out: dict[str, Any] = {
        "accountNo": account_no,
        "symbol": rec.symbol,
        "side": rec.side,
        "qty": str(rec.qty),
        "price": str(rec.price),
        "orderId": rec.order_id or "",
        "execId": exec_id,
        "tradeDateTime": trade_dt,
        "fee": "0",
    }
    if tag:
        out["strategyTag"] = tag
    return out


def client_from_config(cfg: dict) -> ContractReportClient | None:
    """config['contract_report'] + 환경변수로 클라이언트 생성. disabled 이면 None."""
    cr = cfg.get("contract_report") or {}
    if not cr.get("enabled", False):
        return None
    import os

    base = os.environ.get("CONTRACT_REPORT_API_URL") or cr.get("api_base_url") or ""
    user = os.environ.get("CONTRACT_REPORT_USER_ID") or cr.get("user_id") or ""
    acc = os.environ.get("KIWOOM_ACCOUNT") or (cfg.get("account") or {}).get("account_no") or ""
    if not base or not user or not acc:
        log.warning(
            "[ContractReport] enabled 이지만 api_base_url / user_id / account 가 비어 있음 → 동기화 생략"
        )
        return None
    timeout = float(cr.get("timeout_sec", 30))
    return ContractReportClient(
        base_url=base,
        user_id=user,
        kiwoom_account_no=acc,
        timeout_sec=timeout,
    )
