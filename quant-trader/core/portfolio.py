"""
포트폴리오 상태 관리.
브로커와 독립적으로 실시간 포지션 / 손익을 추적한다.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from datetime import datetime
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from core.broker import BaseBroker, Position

log = logging.getLogger(__name__)


@dataclass
class TradeRecord:
    """체결 기록."""
    timestamp: datetime
    symbol: str
    side: str   # "BUY" | "SELL"
    qty: int
    price: float
    order_id: str = ""
    strategy_tag: str = ""

    @property
    def amount(self) -> float:
        return self.qty * self.price


class Portfolio:
    """
    실시간 포트폴리오 추적기.

    브로커에서 포지션/잔고를 직접 동기화하거나,
    주문 체결 결과를 받아 직접 업데이트할 수 있다.
    """

    def __init__(self, initial_cash: float = 10_000_000):
        self._initial_cash = initial_cash
        self._cash = initial_cash
        self._positions: dict[str, "Position"] = {}
        self._trade_history: list[TradeRecord] = []
        self._equity_curve: list[tuple[datetime, float]] = []

    # ------------------------------------------------------------------
    # 상태 조회
    # ------------------------------------------------------------------

    @property
    def cash(self) -> float:
        return self._cash

    @property
    def positions(self) -> dict[str, "Position"]:
        return dict(self._positions)

    @property
    def trade_history(self) -> list[TradeRecord]:
        return list(self._trade_history)

    @property
    def equity_curve(self) -> list[tuple[datetime, float]]:
        return list(self._equity_curve)

    def total_market_value(self) -> float:
        """보유 주식 시가총액."""
        return sum(p.market_value for p in self._positions.values())

    def total_equity(self) -> float:
        """총 자산 = 현금 + 주식 시가."""
        return self._cash + self.total_market_value()

    def unrealized_pnl(self) -> float:
        """미실현 손익 합계."""
        return sum(p.unrealized_pnl for p in self._positions.values())

    def realized_pnl(self) -> float:
        """실현 손익 (총 자산 - 초기 자본 - 미실현 손익)."""
        return self.total_equity() - self._initial_cash - self.unrealized_pnl()

    def total_return_pct(self) -> float:
        """총 수익률 (%)."""
        return (self.total_equity() / self._initial_cash - 1) * 100

    def position_weight(self, symbol: str) -> float:
        """종목 포지션이 총 자산에서 차지하는 비중 (0 ~ 1)."""
        equity = self.total_equity()
        if equity <= 0 or symbol not in self._positions:
            return 0.0
        return self._positions[symbol].market_value / equity

    # ------------------------------------------------------------------
    # 상태 업데이트
    # ------------------------------------------------------------------

    def sync_from_broker(self, broker: "BaseBroker") -> None:
        """브로커에서 잔고·포지션 동기화."""
        balance = broker.get_balance()
        self._cash = balance.get("cash", self._cash)
        self._positions = broker.get_positions()
        self._snapshot_equity()

    def record_trade(
        self,
        symbol: str,
        side: str,
        qty: int,
        price: float,
        order_id: str = "",
        strategy_tag: str = "",
    ) -> None:
        """체결 결과 기록."""
        rec = TradeRecord(
            timestamp=datetime.now(),
            symbol=symbol,
            side=side,
            qty=qty,
            price=price,
            order_id=order_id,
            strategy_tag=strategy_tag,
        )
        self._trade_history.append(rec)
        log.info(
            f"[Portfolio] 체결: {side} {symbol} {qty}주 @ {price:,.0f} | "
            f"현금={self._cash:,.0f}"
        )

    def update_price(self, symbol: str, price: float) -> None:
        """현재가 업데이트."""
        if symbol in self._positions:
            self._positions[symbol].current_price = price

    def _snapshot_equity(self) -> None:
        """현재 시점 자산 스냅샷 기록."""
        self._equity_curve.append((datetime.now(), self.total_equity()))

    # ------------------------------------------------------------------
    # 요약 출력
    # ------------------------------------------------------------------

    def summary(self) -> str:
        lines = [
            "=== Portfolio Summary ===",
            f"총 자산    : {self.total_equity():>15,.0f} 원",
            f"현금       : {self._cash:>15,.0f} 원",
            f"주식 시가  : {self.total_market_value():>15,.0f} 원",
            f"미실현 손익: {self.unrealized_pnl():>+15,.0f} 원",
            f"실현 손익  : {self.realized_pnl():>+15,.0f} 원",
            f"총 수익률  : {self.total_return_pct():>+14.2f} %",
            "",
            "--- 보유 종목 ---",
        ]
        if not self._positions:
            lines.append("  (없음)")
        for sym, pos in self._positions.items():
            lines.append(
                f"  {sym}: {pos.qty}주 | 평균가={pos.avg_price:,.0f} | "
                f"현재가={pos.current_price:,.0f} | "
                f"손익={pos.unrealized_pnl:+,.0f}"
            )
        lines.append(f"\n체결 건수: {len(self._trade_history)}건")
        return "\n".join(lines)
