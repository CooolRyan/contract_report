"""
이동평균 골든/데드 크로스 전략.

- 골든 크로스 (단기 MA > 장기 MA 상향 돌파) → BUY
- 데드 크로스  (단기 MA < 장기 MA 하향 이탈) → SELL
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

import pandas as pd

from strategies.base import BaseStrategy, Signal

if TYPE_CHECKING:
    from core.data_feed import DataFeed
    from core.portfolio import Portfolio

log = logging.getLogger(__name__)


class MovingAverageCrossStrategy(BaseStrategy):
    """
    이동평균 크로스 전략.

    Params (config.yaml strategies.moving_average_cross):
        fast_period: 단기 MA 기간 (기본 5)
        slow_period: 장기 MA 기간 (기본 20)
        ma_type: "SMA" | "EMA"
    """

    def __init__(self, params: dict | None = None):
        super().__init__(name="moving_average_cross", params=params or {})
        self._fast = self.params.get("fast_period", 5)
        self._slow = self.params.get("slow_period", 20)
        self._ma_type = self.params.get("ma_type", "EMA").upper()
        # 직전 신호 상태 (크로스 중복 발생 방지)
        self._prev_state: dict[str, str] = {}   # symbol -> "GOLDEN" | "DEAD" | ""

    def _calc_ma(self, series: pd.Series, period: int) -> pd.Series:
        if self._ma_type == "EMA":
            return series.ewm(span=period, adjust=False).mean()
        return series.rolling(period).mean()

    def generate_signals(
        self,
        universe: list[str],
        data: "DataFeed",
        portfolio: "Portfolio",
    ) -> list[Signal]:
        signals: list[Signal] = []

        for symbol in universe:
            close = data.get_close_series(symbol, count=self._slow + 10)
            if len(close) < self._slow + 2:
                log.debug(f"[MA] {symbol}: 데이터 부족 ({len(close)}봉)")
                continue

            fast_ma = self._calc_ma(close, self._fast)
            slow_ma = self._calc_ma(close, self._slow)

            # 현재와 직전 시점
            prev_fast, cur_fast = fast_ma.iloc[-2], fast_ma.iloc[-1]
            prev_slow, cur_slow = slow_ma.iloc[-2], slow_ma.iloc[-1]

            prev_above = prev_fast > prev_slow
            cur_above = cur_fast > cur_slow

            prev_state = self._prev_state.get(symbol, "")

            if not prev_above and cur_above:
                # 골든 크로스
                if prev_state != "GOLDEN":
                    self._prev_state[symbol] = "GOLDEN"
                    price = data.get_price(symbol)
                    signals.append(Signal(
                        symbol=symbol,
                        side="BUY",
                        price=price,
                        strength=min(abs(cur_fast - cur_slow) / cur_slow * 10, 1.0),
                        reason=f"골든크로스 ({self._ma_type}{self._fast} > {self._ma_type}{self._slow})",
                        strategy_name=self.name,
                    ))
                    log.info(f"[MA] 골든크로스 → BUY {symbol}")

            elif prev_above and not cur_above:
                # 데드 크로스
                if prev_state != "DEAD":
                    self._prev_state[symbol] = "DEAD"
                    pos = portfolio.positions.get(symbol)
                    if pos and pos.qty > 0:
                        price = data.get_price(symbol)
                        signals.append(Signal(
                            symbol=symbol,
                            side="SELL",
                            qty=pos.qty,
                            price=price,
                            strength=1.0,
                            reason=f"데드크로스 ({self._ma_type}{self._fast} < {self._ma_type}{self._slow})",
                            strategy_name=self.name,
                        ))
                        log.info(f"[MA] 데드크로스 → SELL {symbol}")

        return signals
