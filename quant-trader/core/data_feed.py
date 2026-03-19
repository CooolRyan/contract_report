"""
시장 데이터 피드.

브로커의 OHLCV / 현재가 조회를 캐싱하고 정규화한다.
전략에서 직접 브로커를 호출하지 않고 DataFeed 를 통해 데이터를 사용한다.
"""

from __future__ import annotations

import logging
import time
from typing import TYPE_CHECKING

import pandas as pd

if TYPE_CHECKING:
    from core.broker import BaseBroker

log = logging.getLogger(__name__)


class DataFeed:
    """
    시장 데이터 캐싱 레이어.

    Args:
        broker: 브로커 인스턴스
        cache_ttl_sec: 가격/OHLCV 캐시 유효 시간 (초). 0 이면 캐시 사용 안 함.
    """

    def __init__(self, broker: "BaseBroker", cache_ttl_sec: int = 60):
        self._broker = broker
        self._ttl = cache_ttl_sec
        self._price_cache: dict[str, tuple[float, float]] = {}   # symbol -> (price, ts)
        self._ohlcv_cache: dict[str, tuple[pd.DataFrame, float]] = {}   # key -> (df, ts)

    # ------------------------------------------------------------------
    # 현재가
    # ------------------------------------------------------------------

    def get_price(self, symbol: str, use_cache: bool = True) -> float:
        """현재가 조회 (캐싱 적용)."""
        if use_cache and self._ttl > 0 and symbol in self._price_cache:
            price, ts = self._price_cache[symbol]
            if time.time() - ts < self._ttl:
                return price

        price = self._broker.get_price(symbol)
        self._price_cache[symbol] = (price, time.time())
        return price

    def get_prices(self, symbols: list[str]) -> dict[str, float]:
        """여러 종목 현재가 일괄 조회."""
        return {sym: self.get_price(sym) for sym in symbols}

    # ------------------------------------------------------------------
    # OHLCV
    # ------------------------------------------------------------------

    def get_ohlcv(
        self,
        symbol: str,
        period: str = "D",
        count: int = 200,
        use_cache: bool = True,
    ) -> pd.DataFrame:
        """OHLCV 조회 (캐싱 적용)."""
        cache_key = f"{symbol}:{period}:{count}"
        if use_cache and self._ttl > 0 and cache_key in self._ohlcv_cache:
            df, ts = self._ohlcv_cache[cache_key]
            if time.time() - ts < self._ttl:
                return df

        df = self._broker.get_ohlcv(symbol, period, count)
        self._ohlcv_cache[cache_key] = (df, time.time())
        return df

    def invalidate(self, symbol: str | None = None) -> None:
        """캐시 무효화. symbol=None 이면 전체 초기화."""
        if symbol is None:
            self._price_cache.clear()
            self._ohlcv_cache.clear()
        else:
            self._price_cache.pop(symbol, None)
            keys = [k for k in self._ohlcv_cache if k.startswith(symbol + ":")]
            for k in keys:
                del self._ohlcv_cache[k]

    # ------------------------------------------------------------------
    # 편의 메서드 (전략에서 자주 쓰는 값 계산)
    # ------------------------------------------------------------------

    def get_close_series(self, symbol: str, count: int = 200) -> pd.Series:
        """종가 시리즈 반환."""
        df = self.get_ohlcv(symbol, count=count)
        return df["close"] if "close" in df.columns else pd.Series(dtype=float)

    def get_returns(self, symbol: str, count: int = 200) -> pd.Series:
        """일별 수익률 시리즈 반환."""
        close = self.get_close_series(symbol, count=count)
        return close.pct_change().dropna()
