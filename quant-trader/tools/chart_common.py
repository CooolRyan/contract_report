"""
차트 미리보기 / GUI 공통: 설정 로드, 브로커 준비, 후보 종목 수집, mplfinance 저장.
"""

from __future__ import annotations

import logging
from pathlib import Path

import pandas as pd

log = logging.getLogger(__name__)

_ROOT = Path(__file__).resolve().parent.parent


def setup_logging(verbose: bool) -> None:
    logging.basicConfig(
        level=logging.DEBUG if verbose else logging.INFO,
        format="%(asctime)s [%(levelname)s] %(message)s",
        datefmt="%H:%M:%S",
    )


def load_config(config_path: str) -> dict:
    import os

    import yaml

    # quant-trader/.env → os.environ (dotenv 없어도 수동 파서로 로드)
    from core.env_loader import load_quant_env

    load_quant_env()

    cfg_path = _ROOT / config_path
    with open(cfg_path, encoding="utf-8") as f:
        cfg = yaml.safe_load(f)

    kiwoom = cfg.setdefault("kiwoom", {})
    if os.environ.get("KIWOOM_APPKEY"):
        kiwoom["appkey"] = os.environ["KIWOOM_APPKEY"]
    if os.environ.get("KIWOOM_SECRETKEY"):
        kiwoom["secretkey"] = os.environ["KIWOOM_SECRETKEY"]
    account = cfg.setdefault("account", {})
    if os.environ.get("KIWOOM_ACCOUNT"):
        account["account_no"] = os.environ["KIWOOM_ACCOUNT"]
    cr = cfg.setdefault("contract_report", {})
    if os.environ.get("CONTRACT_REPORT_API_URL"):
        cr["api_base_url"] = os.environ["CONTRACT_REPORT_API_URL"]
    if os.environ.get("CONTRACT_REPORT_USER_ID"):
        cr["user_id"] = os.environ["CONTRACT_REPORT_USER_ID"]
    env_en = os.environ.get("CONTRACT_REPORT_ENABLED", "").strip().lower()
    if env_en in ("1", "true", "yes", "on"):
        cr["enabled"] = True
    return cfg


def build_strategy(cfg: dict):
    from strategies.moving_average_cross import MovingAverageCrossStrategy
    from strategies.momentum import MomentumStrategy
    from strategies.rsi_mean_reversion import RSIMeanReversionStrategy

    strategy_name = cfg.get("engine", {}).get("strategy", "moving_average_cross")
    strategy_params = cfg.get("strategies", {}).get(strategy_name, {})
    strategy_map = {
        "moving_average_cross": MovingAverageCrossStrategy,
        "rsi_mean_reversion": RSIMeanReversionStrategy,
        "momentum": MomentumStrategy,
    }
    cls = strategy_map.get(strategy_name)
    if cls is None:
        raise ValueError(f"알 수 없는 전략: {strategy_name}")
    return strategy_name, cls(params=strategy_params)


def prepare_mock_broker(cfg: dict, universe: list[str]):
    from core.broker import MockBroker
    from main import generate_sample_ohlcv

    bt = cfg.get("backtest", {})
    start = bt.get("start_date", "2024-01-01")
    end = bt.get("end_date", "2024-12-31")
    initial = cfg.get("account", {}).get("initial_cash", 10_000_000)
    broker = MockBroker(initial_cash=initial)

    for sym in universe:
        df = generate_sample_ohlcv(sym, start, end)
        broker.set_ohlcv(sym, df)
        if not df.empty and "close" in df.columns:
            broker.set_price(sym, float(df["close"].iloc[-1]))
    return broker


def momentum_rank_symbols(
    universe: list[str],
    data,
    lookback: int,
    top_n: int,
) -> list[str]:
    scores: list[tuple[str, float]] = []
    for symbol in universe:
        close = data.get_close_series(symbol, count=lookback + 5)
        if len(close) < lookback + 1:
            continue
        ret = (close.iloc[-1] - close.iloc[-(lookback + 1)]) / close.iloc[-(lookback + 1)]
        scores.append((symbol, ret))
    scores.sort(key=lambda x: x[1], reverse=True)
    return [s for s, _ in scores[:top_n]]


def collect_chart_symbols(
    cfg: dict,
    strategy,
    data,
    portfolio,
    universe: list[str],
    *,
    fallback_universe: bool,
    momentum_top_when_empty: bool,
) -> tuple[list[str], str]:
    if strategy.name == "momentum" and hasattr(strategy, "_rebalance_days"):
        rd = strategy._rebalance_days
        strategy._days_since_rebalance = max(0, rd - 1)

    signals = strategy.generate_signals(universe, data, portfolio)
    syms = list(dict.fromkeys(s.symbol for s in signals))

    note = "전략 신호가 발생한 종목"
    if not syms and strategy.name == "momentum" and momentum_top_when_empty:
        lookback = getattr(strategy, "_lookback", 20)
        top_n = getattr(strategy, "_top_n", 3)
        syms = momentum_rank_symbols(universe, data, lookback, top_n)
        note = f"모멘텀 상위 {len(syms)}종목 (신호 없음·랭킹 기준)"

    if not syms and fallback_universe:
        syms = list(universe)
        note = "신호/랭킹 없음 → 유니버스 전체 표시 (fallback)"

    return syms, note


def three_slots_for_strategy(
    strategy_name: str,
    strategy,
    signals: list,
    candidates: list[str],
    universe: list[str],
    data,
) -> tuple[list[str], list[str]]:
    """
    전략별로 3개 차트 슬롯에 넣을 종목 + 슬롯 라벨(ASCII).

    - momentum: 모멘텀 순위 1~3위 (부족하면 유니버스로 패딩)
    - moving_average_cross: BUY 신호 / SELL 신호 / 그 외 관찰 1종목
    - rsi_mean_reversion: RSI 매수(BUY) / 매도(SELL) / 그 외 관찰
    """
    from strategies.base import Signal

    def _pad_three(syms: list[str]) -> list[str]:
        out = list(syms)
        for u in universe:
            if u not in out:
                out.append(u)
            if len(out) >= 3:
                break
        while len(out) < 3 and universe:
            out.append(universe[len(out) % len(universe)])
        return out[:3]

    if strategy_name == "momentum":
        lookback = getattr(strategy, "_lookback", 20)
        ranked = momentum_rank_symbols(universe, data, lookback, 3)
        syms = _pad_three(ranked)
        labels = ["mom_R1", "mom_R2", "mom_R3"]
        return syms, labels

    if strategy_name == "moving_average_cross":
        buys = [s.symbol for s in signals if s.side == "BUY"]
        sells = [s.symbol for s in signals if s.side == "SELL"]
        s0 = buys[0] if buys else (candidates[0] if candidates else universe[0])
        s1 = sells[0] if sells else (candidates[1] if len(candidates) > 1 else universe[min(1, len(universe) - 1)])
        used = {s0, s1}
        s2 = next((c for c in candidates if c not in used), None)
        if s2 is None:
            s2 = next((u for u in universe if u not in used), universe[0])
        labels = ["MA_buy", "MA_sell", "MA_watch"]
        return [s0, s1, s2], labels

    if strategy_name == "rsi_mean_reversion":
        buys = [s.symbol for s in signals if s.side == "BUY"]
        sells = [s.symbol for s in signals if s.side == "SELL"]
        s0 = buys[0] if buys else (candidates[0] if candidates else universe[0])
        s1 = sells[0] if sells else (candidates[1] if len(candidates) > 1 else universe[min(1, len(universe) - 1)])
        used = {s0, s1}
        s2 = next((c for c in candidates if c not in used), None)
        if s2 is None:
            s2 = next((u for u in universe if u not in used), universe[0])
        labels = ["RSI_buy", "RSI_sell", "RSI_watch"]
        return [s0, s1, s2], labels

    # 알 수 없는 전략: 후보/유니버스 앞 3개
    base = candidates if candidates else universe
    syms = _pad_three(base)
    labels = [f"slot{i}" for i in range(3)]
    return syms, labels


def candidate_display_rows(
    candidates: list[str],
    signals: list,
) -> tuple[list[str], list[str]]:
    """(종목코드 순서, 리스트박스에 보일 문자열) 동일 인덱스 매칭."""
    reason: dict[str, str] = {}
    for s in signals:
        if s.symbol not in reason:
            reason[s.symbol] = f"{s.side}/{s.strategy_name}"
    displays = [f"{sym}  [{reason.get(sym, 'watch')}]" for sym in candidates]
    return candidates, displays


def plot_candles_file(
    df: pd.DataFrame,
    title: str,
    out_path: Path,
    *,
    mav: tuple[int, ...] | None = None,
) -> None:
    import matplotlib

    matplotlib.use("Agg")
    import mplfinance as mpf

    if df.empty:
        log.warning("차트 스킵 (데이터 없음): %s", title)
        return

    plot_df = df.copy()
    if not isinstance(plot_df.index, pd.DatetimeIndex):
        plot_df.index = pd.to_datetime(plot_df.index)

    kwargs: dict = {
        "type": "candle",
        "style": "yahoo",
        "title": title,
        "volume": True,
        "tight_layout": True,
        "savefig": dict(fname=str(out_path), dpi=120, bbox_inches="tight"),
    }
    if mav:
        kwargs["mav"] = mav
    mpf.plot(plot_df, **kwargs)


def plotly_candlestick_figure(
    df: pd.DataFrame,
    title: str,
    *,
    mav: tuple[int, ...] | None = None,
    height: int = 520,
    template: str = "plotly_dark",
):
    """
    Plotly 캔들 + 거래량 (+ 선택 이평). 브라우저(Streamlit 등)용.
    """
    import plotly.graph_objects as go
    from plotly.subplots import make_subplots

    if df.empty:
        fig = go.Figure()
        fig.add_annotation(
            text="데이터 없음",
            xref="paper",
            yref="paper",
            x=0.5,
            y=0.5,
            showarrow=False,
            font=dict(size=16),
        )
        fig.update_layout(title=title, height=height, template=template)
        return fig

    p = df.copy()
    if not isinstance(p.index, pd.DatetimeIndex):
        p.index = pd.to_datetime(p.index)
    x = p.index
    has_vol = "volume" in p.columns and p["volume"].notna().any()

    if has_vol:
        fig = make_subplots(
            rows=2,
            cols=1,
            shared_xaxes=True,
            vertical_spacing=0.06,
            row_heights=[0.72, 0.28],
        )
        row_candle, row_vol = 1, 2
    else:
        fig = make_subplots(rows=1, cols=1)
        row_candle, row_vol = 1, 1

    fig.add_trace(
        go.Candlestick(
            x=x,
            open=p["open"],
            high=p["high"],
            low=p["low"],
            close=p["close"],
            name="OHLC",
            increasing_line_color="#26a69a",
            decreasing_line_color="#ef5350",
        ),
        row=row_candle,
        col=1,
    )

    if mav:
        for n in mav:
            ma = p["close"].rolling(window=n, min_periods=1).mean()
            fig.add_trace(
                go.Scatter(
                    x=x,
                    y=ma,
                    name=f"MA{n}",
                    line=dict(width=1.2),
                    mode="lines",
                ),
                row=row_candle,
                col=1,
            )

    if has_vol:
        colors = ["#26a69a" if p["close"].iloc[i] >= p["open"].iloc[i] else "#ef5350" for i in range(len(p))]
        fig.add_trace(
            go.Bar(x=x, y=p["volume"], name="Volume", marker_color=colors, opacity=0.7),
            row=row_vol,
            col=1,
        )

    fig.update_layout(
        title=title,
        height=height,
        template=template,
        xaxis_rangeslider_visible=False,
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
        margin=dict(l=48, r=24, t=56, b=40),
    )
    fig.update_yaxes(title_text="가격", row=row_candle, col=1)
    if has_vol:
        fig.update_yaxes(title_text="거래량", row=row_vol, col=1)
    return fig
