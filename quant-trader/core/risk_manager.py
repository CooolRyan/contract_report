"""
리스크 관리 모듈.

주문 전 다음 항목을 검증한다:
  - 종목당 최대 포지션 비중
  - 전체 주식 편입 비중 상한
  - 일일 손실 한도
  - 손절 조건 (stop-loss)
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from datetime import date
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from core.broker import Side
    from core.portfolio import Portfolio

log = logging.getLogger(__name__)


@dataclass
class RiskConfig:
    max_position_pct: float = 0.20        # 종목당 최대 비중
    max_total_exposure_pct: float = 0.80  # 전체 주식 최대 비중
    stop_loss_pct: float = 0.05           # 손절률 (매입가 대비)
    daily_loss_limit_pct: float = 0.03    # 일일 최대 손실 한도

    @classmethod
    def from_cfg(cls, cfg: dict) -> "RiskConfig":
        r = cfg.get("risk", {})
        return cls(
            max_position_pct=r.get("max_position_pct", 0.20),
            max_total_exposure_pct=r.get("max_total_exposure_pct", 0.80),
            stop_loss_pct=r.get("stop_loss_pct", 0.05),
            daily_loss_limit_pct=r.get("daily_loss_limit_pct", 0.03),
        )


class RiskManager:
    """
    주문 전 리스크 검증 및 주문 수량 조정.
    """

    def __init__(self, config: RiskConfig):
        self._cfg = config
        self._daily_start_equity: float | None = None
        self._daily_start_date: date | None = None

    # ------------------------------------------------------------------
    # 일일 손실 추적
    # ------------------------------------------------------------------

    def mark_day_start(self, equity: float) -> None:
        """장 시작 시 자산 기록 (일일 손실 한도 기준)."""
        today = date.today()
        if self._daily_start_date != today:
            self._daily_start_equity = equity
            self._daily_start_date = today
            log.info(f"[Risk] 일일 기준 자산 설정: {equity:,.0f} 원 ({today})")

    def is_daily_loss_exceeded(self, current_equity: float) -> bool:
        """일일 손실 한도 초과 여부."""
        if self._daily_start_equity is None:
            return False
        loss_pct = (self._daily_start_equity - current_equity) / self._daily_start_equity
        if loss_pct >= self._cfg.daily_loss_limit_pct:
            log.warning(
                f"[Risk] 일일 손실 한도 초과: {loss_pct:.2%} >= {self._cfg.daily_loss_limit_pct:.2%}"
            )
            return True
        return False

    # ------------------------------------------------------------------
    # 손절 체크
    # ------------------------------------------------------------------

    def symbols_to_stop_loss(self, portfolio: "Portfolio") -> list[str]:
        """손절 조건에 해당하는 종목 리스트 반환."""
        result = []
        for symbol, pos in portfolio.positions.items():
            if pos.avg_price <= 0:
                continue
            loss_pct = (pos.avg_price - pos.current_price) / pos.avg_price
            if loss_pct >= self._cfg.stop_loss_pct:
                log.warning(
                    f"[Risk] 손절 조건 충족: {symbol} | "
                    f"손실={loss_pct:.2%} >= 한도={self._cfg.stop_loss_pct:.2%}"
                )
                result.append(symbol)
        return result

    # ------------------------------------------------------------------
    # 주문 수량 검증 / 조정
    # ------------------------------------------------------------------

    def validate_buy(
        self,
        symbol: str,
        qty: int,
        price: float,
        portfolio: "Portfolio",
    ) -> int:
        """
        매수 주문 수량 검증 및 조정.

        Returns:
            조정된 주문 수량 (0 이면 주문 금지)
        """
        equity = portfolio.total_equity()
        if equity <= 0:
            return 0

        # 일일 손실 한도 초과
        if self.is_daily_loss_exceeded(portfolio.total_equity()):
            log.warning(f"[Risk] 매수 거부 ({symbol}): 일일 손실 한도 초과")
            return 0

        # 전체 주식 편입 비중 검사
        current_exposure = portfolio.total_market_value() / equity
        if current_exposure >= self._cfg.max_total_exposure_pct:
            log.warning(
                f"[Risk] 매수 거부 ({symbol}): 전체 편입 비중 {current_exposure:.2%} >= "
                f"한도 {self._cfg.max_total_exposure_pct:.2%}"
            )
            return 0

        # 종목당 최대 비중
        max_amount = equity * self._cfg.max_position_pct
        current_amount = portfolio.positions.get(symbol, None)
        current_value = current_amount.market_value if current_amount else 0.0
        available_amount = max(0, max_amount - current_value)

        if price <= 0:
            return 0

        max_qty_by_risk = int(available_amount / price)
        max_qty_by_cash = int(portfolio.cash / price)
        adjusted_qty = min(qty, max_qty_by_risk, max_qty_by_cash)

        if adjusted_qty <= 0:
            log.info(f"[Risk] 매수 불가 ({symbol}): 비중 한도 또는 현금 부족")
            return 0

        if adjusted_qty < qty:
            log.info(f"[Risk] 매수 수량 조정 ({symbol}): {qty} → {adjusted_qty}")

        return adjusted_qty

    def validate_sell(
        self,
        symbol: str,
        qty: int,
        portfolio: "Portfolio",
    ) -> int:
        """
        매도 주문 수량 검증.

        Returns:
            조정된 주문 수량 (0 이면 주문 금지)
        """
        pos = portfolio.positions.get(symbol)
        if pos is None or pos.qty <= 0:
            log.warning(f"[Risk] 매도 거부 ({symbol}): 보유 수량 없음")
            return 0
        adjusted_qty = min(qty, pos.qty)
        if adjusted_qty < qty:
            log.info(f"[Risk] 매도 수량 조정 ({symbol}): {qty} → {adjusted_qty}")
        return adjusted_qty
