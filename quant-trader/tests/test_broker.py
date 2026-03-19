"""
브로커 단위 테스트.
- MockBroker: 실제 API 없이 로직 검증
- KiwoomRestBroker: requests 모킹으로 REST 호출 검증
"""
import pytest
import pandas as pd
from unittest.mock import patch, MagicMock

from core.broker import (
    MockBroker,
    KiwoomRestBroker,
    create_broker,
    OrderResult,
    Position,
)


# ---------------------------------------------------------------------------
# MockBroker
# ---------------------------------------------------------------------------

class TestMockBroker:
    """MockBroker 단위 테스트."""

    def test_get_balance_initial(self, mock_broker):
        mock_broker.set_price("005930", 70_000)
        bal = mock_broker.get_balance()
        assert bal["cash"] == 10_000_000
        assert bal["total_asset"] == 10_000_000

    def test_set_ohlcv_and_get_ohlcv(self, mock_broker, sample_ohlcv):
        mock_broker.set_ohlcv("005930", sample_ohlcv)
        df = mock_broker.get_ohlcv("005930", period="D", count=10)
        assert len(df) == 5
        assert list(df.columns) == ["open", "high", "low", "close", "volume"]
        assert df["close"].iloc[-1] == 72100

    def test_get_price_default_zero(self, mock_broker):
        assert mock_broker.get_price("005930") == 0.0

    def test_set_price_and_get_price(self, mock_broker):
        mock_broker.set_price("005930", 71_500)
        assert mock_broker.get_price("005930") == 71_500

    def test_place_order_buy(self, mock_broker):
        mock_broker.set_price("005930", 70_000)
        res = mock_broker.place_order("005930", "BUY", 100, "MARKET", 0)
        assert res.symbol == "005930"
        assert res.side == "BUY"
        assert res.qty == 100
        assert res.status == "FILLED"
        assert res.price == 70_000

        bal = mock_broker.get_balance()
        assert bal["cash"] == 10_000_000 - 70_000 * 100
        pos = mock_broker.get_positions()
        assert "005930" in pos
        assert pos["005930"].qty == 100
        assert pos["005930"].avg_price == 70_000

    def test_place_order_buy_insufficient_cash(self, mock_broker):
        mock_broker.set_price("005930", 70_000)
        with pytest.raises(ValueError, match="잔액 부족"):
            mock_broker.place_order("005930", "BUY", 200, "MARKET", 0)

    def test_place_order_sell(self, mock_broker):
        mock_broker.set_price("005930", 70_000)
        mock_broker.place_order("005930", "BUY", 100, "MARKET", 0)
        mock_broker.set_price("005930", 72_000)
        res = mock_broker.place_order("005930", "SELL", 50, "MARKET", 0)
        assert res.side == "SELL"
        assert res.qty == 50
        assert res.price == 72_000

        pos = mock_broker.get_positions()
        assert pos["005930"].qty == 50
        bal = mock_broker.get_balance()
        assert bal["cash"] == 10_000_000 - 70_000 * 100 + 72_000 * 50

    def test_place_order_sell_insufficient_position(self, mock_broker):
        mock_broker.set_price("005930", 70_000)
        with pytest.raises(ValueError, match="보유 수량 부족"):
            mock_broker.place_order("005930", "SELL", 10, "MARKET", 0)

    def test_cancel_order(self, mock_broker):
        mock_broker.set_price("005930", 70_000)
        res = mock_broker.place_order("005930", "BUY", 10, "LIMIT", 69_000)
        assert mock_broker.cancel_order(res.order_id) is True
        assert mock_broker.cancel_order("nonexistent") is False


# ---------------------------------------------------------------------------
# KiwoomRestBroker (mocked HTTP)
# ---------------------------------------------------------------------------

class TestKiwoomRestBroker:
    """KiwoomRestBroker: requests 모킹으로 토큰/TR 호출 검증."""

    @pytest.fixture
    def rest_broker(self):
        return KiwoomRestBroker(
            appkey="test-appkey",
            secretkey="test-secret",
            base_url="https://mockapi.kiwoom.com",
            account_no="12345678",
        )

    @patch("core.broker.requests.post")
    def test_issue_token(self, mock_post, rest_broker):
        mock_post.return_value.json.return_value = {"token": "fake-token-123"}
        mock_post.return_value.raise_for_status = MagicMock()
        token = rest_broker._issue_token()
        assert token == "fake-token-123"
        mock_post.assert_called_once()
        call_kw = mock_post.call_args.kwargs
        assert call_kw["json"]["grant_type"] == "client_credentials"
        assert call_kw["json"]["appkey"] == "test-appkey"

    @patch("core.broker.KiwoomRestBroker._ensure_token", return_value="fake-token")
    @patch("core.broker.requests.post")
    def test_get_balance_mocked(self, mock_post, _ensure_token, rest_broker):
        mock_post.return_value.json.return_value = {
            "dnca_tot_amt": "5000000",
            "nxdy_excc_amt": "4800000",
            "tot_evlu_amt": "5200000",
        }
        mock_post.return_value.raise_for_status = MagicMock()
        bal = rest_broker.get_balance()
        assert bal["cash"] == 5000000.0
        assert bal["orderable"] == 4800000.0
        assert bal["total_asset"] == 5200000.0

    @patch("core.broker.KiwoomRestBroker._ensure_token", return_value="fake-token")
    @patch("core.broker.requests.post")
    def test_get_price_mocked(self, mock_post, _ensure_token, rest_broker):
        mock_post.return_value.json.return_value = {"cur_prc": "71500"}
        mock_post.return_value.raise_for_status = MagicMock()
        price = rest_broker.get_price("005930")
        assert price == 71500.0


# ---------------------------------------------------------------------------
# create_broker
# ---------------------------------------------------------------------------

class TestCreateBroker:
    """create_broker 팩토리 테스트."""

    def test_create_mock_broker(self):
        cfg = {"broker_mode": "mock", "account": {"initial_cash": 5_000_000}}
        broker = create_broker(cfg)
        assert isinstance(broker, MockBroker)
        assert broker.get_balance()["cash"] == 5_000_000

    def test_create_rest_broker(self):
        cfg = {
            "broker_mode": "rest",
            "kiwoom": {"appkey": "a", "secretkey": "s", "base_url": "https://mockapi.kiwoom.com"},
            "account": {"account_no": "123"},
        }
        broker = create_broker(cfg)
        assert isinstance(broker, KiwoomRestBroker)
        assert broker._account_no == "123"

    @pytest.mark.skip(reason="OpenAPI는 Windows + pywin32 필요")
    def test_create_openapi_broker(self):
        cfg = {"broker_mode": "openapi", "account": {"account_no": "123"}}
        broker = create_broker(cfg)
        assert broker is not None
