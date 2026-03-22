"""
트레이딩 엔진.

주기적으로 전략에서 신호를 받아 리스크 검증 후 주문을 제출하는 메인 루프.
"""

from __future__ import annotations

import logging
import time
from datetime import datetime, time as dt_time

from core.broker import BaseBroker, MockBroker
from core.contract_report_client import ContractReportClient
from core.data_feed import DataFeed
from core.portfolio import Portfolio
from core.risk_manager import RiskConfig, RiskManager
from strategies.base import BaseStrategy, Signal

log = logging.getLogger(__name__)


def _parse_time(t_str: str) -> dt_time:
    """'HH:MM' 문자열 → datetime.time."""
    h, m = map(int, t_str.split(":"))
    return dt_time(h, m)


class TradingEngine:
    """
    트레이딩 엔진.

    실전 / 모의 모두 동일하게 동작.
    broker_mode=mock 이면 MockBroker 로 즉시 체결.
    """

    def __init__(
        self,
        broker: BaseBroker,
        strategy: BaseStrategy,
        universe: list[str],
        risk_cfg: RiskConfig | None = None,
        interval_sec: int = 60,
        market_open: str = "09:00",
        market_close: str = "15:20",
        initial_cash: float = 10_000_000,
        contract_report_client: ContractReportClient | None = None,
    ):
        self._broker = broker
        self._strategy = strategy
        self._universe = universe
        self._risk = RiskManager(risk_cfg or RiskConfig())
        self._interval = interval_sec
        self._market_open = _parse_time(market_open)
        self._market_close = _parse_time(market_close)

        self._data = DataFeed(broker, cache_ttl_sec=interval_sec)
        self._portfolio = Portfolio(initial_cash=initial_cash)
        self._running = False
        self._contract_report_client = contract_report_client

    # ------------------------------------------------------------------
    # 시장 시간 체크
    # ------------------------------------------------------------------

    def _is_market_open(self) -> bool:
        now = datetime.now().time()
        return self._market_open <= now <= self._market_close

    # ------------------------------------------------------------------
    # 주문 실행
    # ------------------------------------------------------------------

    def _execute_signal(self, signal: Signal) -> None:
        """신호 → 리스크 검증 → 주문 제출 → 포트폴리오 기록."""
        symbol = signal.symbol
        price = signal.price if signal.price > 0 else self._data.get_price(symbol)

        if price <= 0:
            log.warning(f"[Engine] 가격 조회 실패: {symbol}")
            return

        if signal.side == "BUY":
            # 수량이 지정되지 않은 경우 포지션 비중으로 산출
            if signal.qty <= 0:
                equity = self._portfolio.total_equity()
                target_amount = equity * 0.10  # 포지션당 10% 고정
                qty = int(target_amount / price)
            else:
                qty = signal.qty

            qty = self._risk.validate_buy(symbol, qty, price, self._portfolio)
            if qty <= 0:
                return

            try:
                result = self._broker.place_order(symbol, "BUY", qty, price=price)
                self._portfolio.record_trade(
                    symbol, "BUY", qty, result.price,
                    order_id=result.order_id,
                    strategy_tag=signal.strategy_name,
                )
                self._push_contract_report()
                self._portfolio.sync_from_broker(self._broker)
            except Exception as e:
                log.error(f"[Engine] 매수 주문 실패 {symbol}: {e}")

        else:  # SELL
            qty = signal.qty if signal.qty > 0 else (
                self._portfolio.positions.get(symbol).qty
                if self._portfolio.positions.get(symbol) else 0
            )
            qty = self._risk.validate_sell(symbol, qty, self._portfolio)
            if qty <= 0:
                return

            try:
                result = self._broker.place_order(symbol, "SELL", qty, price=price)
                self._portfolio.record_trade(
                    symbol, "SELL", qty, result.price,
                    order_id=result.order_id,
                    strategy_tag=signal.strategy_name,
                )
                self._push_contract_report()
                self._portfolio.sync_from_broker(self._broker)
            except Exception as e:
                log.error(f"[Engine] 매도 주문 실패 {symbol}: {e}")

    def _push_contract_report(self) -> None:
        """체결 직후 Spring DB(trades)에 전략 태그와 함께 등록."""
        if not self._contract_report_client or not self._portfolio.trade_history:
            return
        rec = self._portfolio.trade_history[-1]
        try:
            self._contract_report_client.register_trade_record(rec)
        except Exception as e:
            log.warning("[Engine] ContractReport 등록 실패 (매매는 계속): %s", e)

    # ------------------------------------------------------------------
    # 손절 체크
    # ------------------------------------------------------------------

    def _check_stop_loss(self) -> None:
        """손절 조건 충족 종목 전량 매도."""
        for symbol in self._risk.symbols_to_stop_loss(self._portfolio):
            pos = self._portfolio.positions.get(symbol)
            if pos and pos.qty > 0:
                log.warning(f"[Engine] 손절 실행: {symbol}")
                self._execute_signal(Signal(
                    symbol=symbol, side="SELL", qty=pos.qty,
                    reason="손절(stop-loss)", strategy_name="risk_manager"
                ))

    # ------------------------------------------------------------------
    # 메인 루프
    # ------------------------------------------------------------------

    def run_once(self) -> list[Signal]:
        """단일 사이클 실행 (백테스트 / 테스트용)."""
        # 현재가 업데이트
        for symbol in self._universe:
            price = self._data.get_price(symbol, use_cache=False)
            self._portfolio.update_price(symbol, price)

        # 손절 체크
        self._check_stop_loss()

        # 일일 손실 한도 체크
        if self._risk.is_daily_loss_exceeded(self._portfolio.total_equity()):
            log.warning("[Engine] 일일 손실 한도 초과 → 신호 무시")
            return []

        # 전략 신호 생성
        signals = self._strategy.generate_signals(
            self._universe, self._data, self._portfolio
        )

        for signal in signals:
            log.info(f"[Engine] 신호 수신: {signal}")
            self._execute_signal(signal)

        return signals

    def start(self) -> None:
        """실전 트레이딩 루프 시작 (Ctrl+C 로 종료)."""
        log.info(
            f"[Engine] 시작 | 전략={self._strategy.name} | "
            f"유니버스={self._universe} | 주기={self._interval}초"
        )
        self._running = True
        self._risk.mark_day_start(self._portfolio.total_equity())

        try:
            while self._running:
                if not self._is_market_open():
                    log.debug("[Engine] 장 외 시간 → 대기")
                    time.sleep(30)
                    continue

                log.info(f"[Engine] 사이클 실행 | {datetime.now().strftime('%H:%M:%S')}")
                self.run_once()
                time.sleep(self._interval)

        except KeyboardInterrupt:
            log.info("[Engine] 사용자 종료")
        finally:
            self._running = False
            log.info(self._portfolio.summary())

    def stop(self) -> None:
        self._running = False

    @property
    def portfolio(self) -> Portfolio:
        return self._portfolio


# ---------------------------------------------------------------------------
# 팩토리
# ---------------------------------------------------------------------------

def build_engine_from_config(cfg: dict) -> TradingEngine:
    """config.yaml 딕셔너리로 TradingEngine 생성."""
    from core.broker import create_broker
    from core.contract_report_client import client_from_config
    from strategies.moving_average_cross import MovingAverageCrossStrategy
    from strategies.rsi_mean_reversion import RSIMeanReversionStrategy
    from strategies.momentum import MomentumStrategy

    broker = create_broker(cfg)

    strategy_name = cfg.get("engine", {}).get("strategy", "moving_average_cross")
    strategy_params = cfg.get("strategies", {}).get(strategy_name, {})

    strategy_map = {
        "moving_average_cross": MovingAverageCrossStrategy,
        "rsi_mean_reversion": RSIMeanReversionStrategy,
        "momentum": MomentumStrategy,
    }

    strategy_cls = strategy_map.get(strategy_name)
    if strategy_cls is None:
        raise ValueError(f"알 수 없는 전략: {strategy_name}. 가능: {list(strategy_map)}")

    strategy = strategy_cls(params=strategy_params)

    engine_cfg = cfg.get("engine", {})
    account_cfg = cfg.get("account", {})
    cr_client = client_from_config(cfg)

    return TradingEngine(
        broker=broker,
        strategy=strategy,
        universe=engine_cfg.get("universe", []),
        risk_cfg=RiskConfig.from_cfg(cfg),
        interval_sec=engine_cfg.get("interval_sec", 60),
        market_open=engine_cfg.get("market_open", "09:00"),
        market_close=engine_cfg.get("market_close", "15:20"),
        initial_cash=account_cfg.get("initial_cash", 10_000_000),
        contract_report_client=cr_client,
    )
