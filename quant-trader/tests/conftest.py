"""
테스트 전용 픽스처.
"""
import pytest
import pandas as pd
from datetime import datetime

# conftest.py가 로드될 때 이미 루트 conftest에서 path가 설정됨
from core.broker import MockBroker, Position, OrderResult
from core.portfolio import Portfolio, TradeRecord


@pytest.fixture
def mock_broker():
    """초기 현금 1천만 원 MockBroker."""
    return MockBroker(initial_cash=10_000_000)


@pytest.fixture
def sample_ohlcv():
    """테스트용 OHLCV DataFrame (일봉 5일)."""
    dates = pd.bdate_range(start="2024-01-02", periods=5, freq="B")
    return pd.DataFrame(
        {
            "open": [70000, 71000, 70500, 72000, 71800],
            "high": [71500, 72000, 71000, 72500, 72200],
            "low": [69500, 70500, 70000, 71500, 71200],
            "close": [71000, 70500, 72000, 71800, 72100],
            "volume": [1000000, 1200000, 900000, 1100000, 950000],
        },
        index=dates,
    )


@pytest.fixture
def portfolio():
    """초기 현금 1천만 원 Portfolio."""
    return Portfolio(initial_cash=10_000_000)
