"""
Portfolio 단위 테스트.
"""
import pytest
from datetime import datetime

from core.broker import MockBroker, Position
from core.portfolio import Portfolio, TradeRecord


class TestPortfolio:
    """Portfolio 상태 및 sync/record 검증."""

    def test_initial_state(self, portfolio):
        assert portfolio.cash == 10_000_000
        assert portfolio.total_equity() == 10_000_000
        assert portfolio.total_market_value() == 0
        assert portfolio.unrealized_pnl() == 0
        assert portfolio.realized_pnl() == 0
        assert portfolio.total_return_pct() == 0.0

    def test_sync_from_broker(self, portfolio, mock_broker):
        mock_broker.set_price("005930", 70_000)
        mock_broker.place_order("005930", "BUY", 100, "MARKET", 0)
        portfolio.sync_from_broker(mock_broker)
        assert portfolio.cash == mock_broker.get_balance()["cash"]
        assert "005930" in portfolio.positions
        assert portfolio.positions["005930"].qty == 100
        assert len(portfolio.equity_curve) == 1

    def test_record_trade(self, portfolio):
        portfolio.record_trade("005930", "BUY", 50, 71_000, order_id="ord-1", strategy_tag="ma_cross")
        assert len(portfolio.trade_history) == 1
        rec = portfolio.trade_history[0]
        assert rec.symbol == "005930"
        assert rec.side == "BUY"
        assert rec.qty == 50
        assert rec.price == 71_000
        assert rec.order_id == "ord-1"
        assert rec.amount == 50 * 71_000

    def test_position_weight(self, portfolio, mock_broker):
        mock_broker.set_price("005930", 70_000)
        mock_broker.place_order("005930", "BUY", 100, "MARKET", 0)
        portfolio.sync_from_broker(mock_broker)
        w = portfolio.position_weight("005930")
        assert 0 < w <= 1.0
        assert portfolio.position_weight("999999") == 0.0

    def test_summary_contains_key_fields(self, portfolio, mock_broker):
        mock_broker.set_price("005930", 70_000)
        mock_broker.place_order("005930", "BUY", 10, "MARKET", 0)
        portfolio.sync_from_broker(mock_broker)
        s = portfolio.summary()
        assert "총 자산" in s
        assert "현금" in s
        assert "005930" in s
        assert "체결 건수" in s


class TestTradeRecord:
    """TradeRecord 데이터 클래스."""

    def test_amount_property(self):
        rec = TradeRecord(datetime.now(), "005930", "BUY", 100, 70_000)
        assert rec.amount == 7_000_000
