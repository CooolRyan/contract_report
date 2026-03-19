"""
전략 추상 기반 클래스 및 Signal 데이터 클래스.

모든 전략은 BaseStrategy 를 상속하고 generate_signals() 를 구현한다.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import TYPE_CHECKING, Literal

if TYPE_CHECKING:
    from core.data_feed import DataFeed
    from core.portfolio import Portfolio


Side = Literal["BUY", "SELL"]


@dataclass
class Signal:
    """
    전략이 생성하는 매매 신호.

    Attributes:
        symbol: 종목 코드
        side: "BUY" | "SELL"
        qty: 주문 수량 (0 이면 전량)
        price: 목표 가격 (0 이면 시장가)
        strength: 신호 강도 (0.0 ~ 1.0). 포지션 사이징에 활용 가능.
        reason: 신호 발생 이유 (로깅용)
        strategy_name: 신호를 생성한 전략 이름
    """
    symbol: str
    side: Side
    qty: int = 0
    price: float = 0.0
    strength: float = 1.0
    reason: str = ""
    strategy_name: str = ""

    def __str__(self) -> str:
        return (
            f"Signal({self.strategy_name} | {self.side} {self.symbol} "
            f"qty={self.qty} price={self.price:,.0f} str={self.strength:.2f} | {self.reason})"
        )


class BaseStrategy(ABC):
    """
    퀀트 전략 추상 기반 클래스.

    서브클래스에서 generate_signals() 를 구현한다.
    전략은 DataFeed 와 Portfolio 를 읽어 Signal 리스트를 반환한다.
    실제 주문 제출은 TradingEngine 이 담당한다 (전략은 주문하지 않는다).
    """

    def __init__(self, name: str, params: dict | None = None):
        self.name = name
        self.params = params or {}

    @abstractmethod
    def generate_signals(
        self,
        universe: list[str],
        data: "DataFeed",
        portfolio: "Portfolio",
    ) -> list[Signal]:
        """
        매매 신호 생성.

        Args:
            universe: 감시 종목 코드 리스트
            data: DataFeed 인스턴스 (가격/OHLCV 제공)
            portfolio: 현재 포트폴리오 상태

        Returns:
            Signal 리스트
        """

    def on_order_filled(self, symbol: str, side: Side, qty: int, price: float) -> None:
        """체결 이벤트 콜백 (필요 시 오버라이드)."""
        pass

    def __repr__(self) -> str:
        return f"{self.__class__.__name__}(name={self.name!r}, params={self.params})"
