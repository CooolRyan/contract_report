"""
RSI 기반 평균 회귀 전략.

- RSI < 과매도 기준 (기본 30) → BUY
- RSI > 과매수 기준 (기본 70) → SELL
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


def calc_rsi(close: pd.Series, period: int = 14) -> pd.Series:
    """RSI 계산 (Wilder's smoothing)."""
    delta = close.diff()
    gain = delta.clip(lower=0)
    loss = -delta.clip(upper=0)
    avg_gain = gain.ewm(alpha=1 / period, adjust=False).mean()
    avg_loss = loss.ewm(alpha=1 / period, adjust=False).mean()
    rs = avg_gain / avg_loss.replace(0, float("nan"))
    return 100 - (100 / (1 + rs))


class RSIMeanReversionStrategy(BaseStrategy):
    """
    RSI 평균 회귀 전략.

    Params (config.yaml strategies.rsi_mean_reversion):
        period     : RSI 기간 (기본 14)
        oversold   : 과매도 기준 (기본 30)
        overbought : 과매수 기준 (기본 70)
        ohlcv_count: 조회 봉 수 (기본 100)
    """

    def __init__(self, params: dict | None = None):
        super().__init__(name="rsi_mean_reversion", params=params or {})
        self._period = self.params.get("period", 14)
        self._oversold = self.params.get("oversold", 30)
        self._overbought = self.params.get("overbought", 70)
        self._count = self.params.get("ohlcv_count", 100)
        # 직전 RSI 존 (연속 신호 방지)
        self._prev_zone: dict[str, str] = {}   # symbol -> "oversold" | "overbought" | "neutral"

    def generate_signals(
        self,
        universe: list[str],
        data: "DataFeed",
        portfolio: "Portfolio",
    ) -> list[Signal]:
        signals: list[Signal] = []

        for symbol in universe:
            close = data.get_close_series(symbol, count=self._count)
            if len(close) < self._period + 5:
                log.debug(f"[RSI] {symbol}: 데이터 부족 ({len(close)}봉)")
                continue

            rsi = calc_rsi(close, self._period)
            current_rsi = rsi.iloc[-1]
            prev_zone = self._prev_zone.get(symbol, "neutral")

            if current_rsi < self._oversold:
                zone = "oversold"
                # 과매도 진입 시 매수 (이미 과매도 구간이면 중복 신호 방지)
                if prev_zone != "oversold":
                    price = data.get_price(symbol)
                    # 신호 강도: RSI 가 낮을수록 강함 (0 → 1)
                    strength = (self._oversold - current_rsi) / self._oversold
                    signals.append(Signal(
                        symbol=symbol,
                        side="BUY",
                        price=price,
                        strength=min(strength, 1.0),
                        reason=f"RSI 과매도 ({current_rsi:.1f} < {self._oversold})",
                        strategy_name=self.name,
                    ))
                    log.info(f"[RSI] 과매도 → BUY {symbol} (RSI={current_rsi:.1f})")

            elif current_rsi > self._overbought:
                zone = "overbought"
                if prev_zone != "overbought":
                    pos = portfolio.positions.get(symbol)
                    if pos and pos.qty > 0:
                        price = data.get_price(symbol)
                        strength = (current_rsi - self._overbought) / (100 - self._overbought)
                        signals.append(Signal(
                            symbol=symbol,
                            side="SELL",
                            qty=pos.qty,
                            price=price,
                            strength=min(strength, 1.0),
                            reason=f"RSI 과매수 ({current_rsi:.1f} > {self._overbought})",
                            strategy_name=self.name,
                        ))
                        log.info(f"[RSI] 과매수 → SELL {symbol} (RSI={current_rsi:.1f})")
            else:
                zone = "neutral"

            self._prev_zone[symbol] = zone

        return signals
