"""
가격 모멘텀 전략.

유니버스 종목들의 N일 수익률을 계산하여 상위 종목을 매수, 하위 종목을 매도한다.
주기적으로 포트폴리오를 리밸런싱한다.
"""

from __future__ import annotations

import logging
from datetime import date
from typing import TYPE_CHECKING

import pandas as pd

from strategies.base import BaseStrategy, Signal

if TYPE_CHECKING:
    from core.data_feed import DataFeed
    from core.portfolio import Portfolio

log = logging.getLogger(__name__)


class MomentumStrategy(BaseStrategy):
    """
    N일 가격 모멘텀 전략.

    Params (config.yaml strategies.momentum):
        lookback_days  : 모멘텀 계산 기간 (기본 20일)
        top_n          : 상위 N개 매수 대상 (기본 3)
        rebalance_days : 리밸런싱 주기 영업일 수 (기본 5)
    """

    def __init__(self, params: dict | None = None):
        super().__init__(name="momentum", params=params or {})
        self._lookback = self.params.get("lookback_days", 20)
        self._top_n = self.params.get("top_n", 3)
        self._rebalance_days = self.params.get("rebalance_days", 5)
        self._last_rebalance: date | None = None
        self._days_since_rebalance: int = 0

    def _should_rebalance(self) -> bool:
        """리밸런싱 필요 여부 (주기 도달 시 True)."""
        self._days_since_rebalance += 1
        if self._days_since_rebalance >= self._rebalance_days:
            self._days_since_rebalance = 0
            return True
        return False

    def generate_signals(
        self,
        universe: list[str],
        data: "DataFeed",
        portfolio: "Portfolio",
    ) -> list[Signal]:
        if not self._should_rebalance():
            return []

        # 각 종목의 N일 수익률 계산
        momentum_scores: dict[str, float] = {}
        for symbol in universe:
            close = data.get_close_series(symbol, count=self._lookback + 5)
            if len(close) < self._lookback + 1:
                log.debug(f"[Momentum] {symbol}: 데이터 부족 ({len(close)}봉)")
                continue
            ret = (close.iloc[-1] - close.iloc[-(self._lookback + 1)]) / close.iloc[-(self._lookback + 1)]
            momentum_scores[symbol] = ret

        if not momentum_scores:
            return []

        # 수익률 기준 정렬
        ranked = sorted(momentum_scores.items(), key=lambda x: x[1], reverse=True)
        top_symbols = [sym for sym, _ in ranked[: self._top_n]]
        bottom_symbols = [sym for sym, _ in ranked[-self._top_n:] if sym not in top_symbols]

        log.info(
            f"[Momentum] 리밸런싱 | "
            f"TOP: {[f'{s}({v:.2%})' for s, v in ranked[:self._top_n]]} | "
            f"BOTTOM: {[f'{s}({v:.2%})' for s, v in ranked[-self._top_n:]]}"
        )

        signals: list[Signal] = []

        # 하위 종목 중 보유하고 있으면 매도
        for symbol in bottom_symbols:
            pos = portfolio.positions.get(symbol)
            if pos and pos.qty > 0:
                price = data.get_price(symbol)
                score = momentum_scores.get(symbol, 0)
                signals.append(Signal(
                    symbol=symbol,
                    side="SELL",
                    qty=pos.qty,
                    price=price,
                    strength=abs(score),
                    reason=f"모멘텀 하위 ({score:.2%})",
                    strategy_name=self.name,
                ))
                log.info(f"[Momentum] SELL {symbol} (수익률={score:.2%})")

        # 상위 종목 매수 (미보유 종목만)
        for symbol in top_symbols:
            pos = portfolio.positions.get(symbol)
            if pos and pos.qty > 0:
                continue   # 이미 보유 중 → 스킵 (리밸런싱 시 비중 조정은 추후 구현)
            price = data.get_price(symbol)
            if price <= 0:
                continue
            score = momentum_scores.get(symbol, 0)
            # strength 를 이용해 엔진에서 수량 결정
            signals.append(Signal(
                symbol=symbol,
                side="BUY",
                price=price,
                strength=min(score * 5, 1.0),  # 수익률 20% = strength 1.0
                reason=f"모멘텀 상위 ({score:.2%})",
                strategy_name=self.name,
            ))
            log.info(f"[Momentum] BUY {symbol} (수익률={score:.2%})")

        return signals
