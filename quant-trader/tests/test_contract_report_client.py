"""ContractReportClient 단위 테스트 (HTTP 모킹)."""

from __future__ import annotations

from datetime import datetime
from unittest.mock import MagicMock, patch

from core.contract_report_client import (
    ContractReportClient,
    _trade_record_to_kiwoom_body,
    client_from_config,
)
from core.portfolio import TradeRecord


def test_trade_record_to_kiwoom_body_strategy_tag():
    rec = TradeRecord(
        timestamp=datetime(2026, 2, 2, 15, 30, 0),
        symbol="005930",
        side="BUY",
        qty=10,
        price=70000.0,
        order_id="ord-1",
        strategy_tag="moving_average_cross",
    )
    body = _trade_record_to_kiwoom_body(rec, "12345678")
    assert body["symbol"] == "005930"
    assert body["strategyTag"] == "moving_average_cross"
    assert body["execId"] == "ord-1_fill"


def test_client_from_config_disabled():
    assert client_from_config({"contract_report": {"enabled": False}}) is None


def test_client_from_config_enabled_missing_url():
    assert (
        client_from_config(
            {"contract_report": {"enabled": True, "api_base_url": ""}, "account": {}}
        )
        is None
    )


@patch("core.contract_report_client.requests.post")
def test_ensure_link_caches_our_account(mock_post: MagicMock):
    mock_post.return_value.status_code = 200
    mock_post.return_value.json.return_value = {
        "ourAccountId": "kiwoom_test_acc",
        "userId": "u1",
        "kiwoomAccountNo": "acc",
        "id": 1,
        "createdAt": "2026-01-01",
    }

    c = ContractReportClient("http://localhost:8080", "u1", "acc")
    assert c.ensure_link() == "kiwoom_test_acc"
    assert c.ensure_link() == "kiwoom_test_acc"
    assert mock_post.call_count == 1
