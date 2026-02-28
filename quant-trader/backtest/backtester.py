"""
백테스트 엔진.

MockBroker 에 과거 OHLCV 데이터를 주입하고
타임스텝마다 전략 신호를 실행하여 포트폴리오 변화를 시뮬레이션한다.
"""

from __future__ import annotations

import logging
from datetime import datetime
from typing import TYPE_CHECKING

import pandas as pd

from core.broker import MockBroker
from core.data_feed import DataFeed
from core.portfolio import Portfolio
from core.risk_manager import RiskConfig, RiskManager
from backtest import metrics as m

if TYPE_CHECKING:
    from strategies.base import BaseStrategy

log = logging.getLogger(__name__)


class Backtester:
    """
    이벤트 기반 백테스터.

    사용 예:
        bt = Backtester(
            strategy=MovingAverageCrossStrategy(),
            universe=["005930", "000660"],
            ohlcv_data={"005930": df_samsung, "000660": df_sk},
            initial_cash=10_000_000,
        )
        result = bt.run()
        m.print_report(result)
    """

    def __init__(
        self,
        strategy: "BaseStrategy",
        universe: list[str],
        ohlcv_data: dict[str, pd.DataFrame],
        initial_cash: float = 10_000_000,
        commission_rate: float = 0.00015,
        slippage_pct: float = 0.001,
        risk_cfg: RiskConfig | None = None,
    ):
        self._strategy = strategy
        self._universe = universe
        self._ohlcv_data = ohlcv_data
        self._initial_cash = initial_cash
        self._commission = commission_rate
        self._slippage = slippage_pct
        self._risk_cfg = risk_cfg or RiskConfig()

        # 공통 날짜 인덱스 (모든 종목의 교집합)
        self._dates: pd.DatetimeIndex = self._build_common_index()

    def _build_common_index(self) -> pd.DatetimeIndex:
        """모든 종목 OHLCV 의 공통 날짜 인덱스."""
        if not self._ohlcv_data:
            return pd.DatetimeIndex([])
        idx = None
        for df in self._ohlcv_data.values():
            cur = df.index
            idx = cur if idx is None else idx.intersection(cur)
        return idx.sort_values()  # type: ignore

    def run(
        self,
        start_date: str | None = None,
        end_date: str | None = None,
    ) -> dict:
        """
        백테스트 실행.

        Args:
            start_date: 시작일 "YYYY-MM-DD" (None 이면 데이터 시작)
            end_date: 종료일 "YYYY-MM-DD" (None 이면 데이터 끝)

        Returns:
            성과 지표 딕셔너리 (metrics.compute_all 형식)
        """
        dates = self._dates
        if start_date:
            dates = dates[dates >= start_date]
        if end_date:
            dates = dates[dates <= end_date]

        if len(dates) == 0:
            raise ValueError("백테스트 기간 내 데이터가 없습니다.")

        broker = MockBroker(initial_cash=self._initial_cash)
        # 전체 OHLCV 주입
        for sym, df in self._ohlcv_data.items():
            broker.set_ohlcv(sym, df)

        data_feed = DataFeed(broker, cache_ttl_sec=0)  # 캐시 사용 안 함
        portfolio = Portfolio(initial_cash=self._initial_cash)
        risk_manager = RiskManager(self._risk_cfg)

        equity_series: list[float] = []
        date_index: list[datetime] = []

        log.info(
            f"[Backtest] 시작 | 전략={self._strategy.name} | "
            f"{dates[0].date()} ~ {dates[-1].date()} ({len(dates)}일)"
        )

        for i, dt in enumerate(dates):
            # 해당 날짜까지의 데이터만 보이도록 슬라이싱하여 브로커에 주입
            for sym, df in self._ohlcv_data.items():
                df_slice = df[df.index <= dt]
                broker.set_ohlcv(sym, df_slice)
                if not df_slice.empty:
                    close = float(df_slice["close"].iloc[-1])
                    # 슬리피지 적용 (매수 시 +, 매도 시 - 이나 여기선 현재가만 설정)
                    broker.set_price(sym, close)
                    portfolio.update_price(sym, close)

            # 손절 체크
            for sym in risk_manager.symbols_to_stop_loss(portfolio):
                pos = portfolio.positions.get(sym)
                if pos and pos.qty > 0:
                    price = broker.get_price(sym)
                    sell_price = price * (1 - self._slippage)
                    try:
                        broker.place_order(sym, "SELL", pos.qty, price=sell_price)
                        portfolio.record_trade(sym, "SELL", pos.qty, sell_price, strategy_tag="stop_loss")
                        # 수수료 차감
                        fee = sell_price * pos.qty * self._commission
                        broker._cash -= fee
                    except Exception as e:
                        log.debug(f"[Backtest] 손절 실패 {sym}: {e}")

            # 전략 신호 생성
            signals = self._strategy.generate_signals(self._universe, data_feed, portfolio)

            for signal in signals:
                sym = signal.symbol
                raw_price = broker.get_price(sym)
                if raw_price <= 0:
                    continue

                if signal.side == "BUY":
                    exec_price = raw_price * (1 + self._slippage)
                    # 수량 산정: 목표 비중 10% 고정 (strength 는 비중 스케일에서 제외)
                    if signal.qty <= 0:
                        equity = portfolio.total_equity()
                        target_amt = equity * 0.10  # 포지션당 10%
                        qty = int(target_amt / exec_price)
                    else:
                        qty = signal.qty

                    qty = risk_manager.validate_buy(sym, qty, exec_price, portfolio)
                    if qty <= 0:
                        continue
                    try:
                        broker.place_order(sym, "BUY", qty, price=exec_price)
                        fee = exec_price * qty * self._commission
                        broker._cash -= fee
                        portfolio.record_trade(sym, "BUY", qty, exec_price, strategy_tag=signal.strategy_name)
                        portfolio.sync_from_broker(broker)
                    except Exception as e:
                        log.debug(f"[Backtest] 매수 실패 {sym}: {e}")

                else:  # SELL
                    exec_price = raw_price * (1 - self._slippage)
                    qty = signal.qty if signal.qty > 0 else (
                        portfolio.positions.get(sym).qty
                        if portfolio.positions.get(sym) else 0
                    )
                    qty = risk_manager.validate_sell(sym, qty, portfolio)
                    if qty <= 0:
                        continue
                    try:
                        broker.place_order(sym, "SELL", qty, price=exec_price)
                        fee = exec_price * qty * self._commission
                        broker._cash -= fee
                        portfolio.record_trade(sym, "SELL", qty, exec_price, strategy_tag=signal.strategy_name)
                        portfolio.sync_from_broker(broker)
                    except Exception as e:
                        log.debug(f"[Backtest] 매도 실패 {sym}: {e}")

            equity = portfolio.total_equity()
            equity_series.append(equity)
            date_index.append(dt)

            if i % 20 == 0:
                log.info(
                    f"[Backtest] {dt.date()} | 자산={equity:,.0f} | "
                    f"수익률={((equity / self._initial_cash) - 1) * 100:+.2f}%"
                )

        equity_curve = pd.Series(equity_series, index=date_index)

        # 거래 손익 계산
        trades = portfolio.trade_history
        trade_pnl = self._compute_trade_pnl(trades)

        result = m.compute_all(equity_curve, trade_pnl)
        result["equity_curve"] = equity_curve
        result["trade_history"] = trades

        log.info(f"[Backtest] 완료 | 총 수익률={result['total_return_pct']:+.2f}%")
        return result

    def _compute_trade_pnl(self, trades) -> list[float]:
        """매도 거래 기준으로 실현 손익 계산 (FIFO)."""
        buy_queue: dict[str, list[tuple[int, float]]] = {}   # symbol -> [(qty, price), ...]
        pnl_list: list[float] = []

        for t in trades:
            sym = t.symbol
            if t.side == "BUY":
                buy_queue.setdefault(sym, []).append((t.qty, t.price))
            else:
                remaining = t.qty
                queue = buy_queue.get(sym, [])
                realized = 0.0
                new_queue = []
                for (bqty, bprice) in queue:
                    if remaining <= 0:
                        new_queue.append((bqty, bprice))
                        continue
                    matched = min(remaining, bqty)
                    realized += matched * (t.price - bprice)
                    remaining -= matched
                    if bqty - matched > 0:
                        new_queue.append((bqty - matched, bprice))
                buy_queue[sym] = new_queue
                pnl_list.append(realized)

        return pnl_list
