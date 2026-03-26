"""
브라우저에서 OHLCV 캔들 + 거래량(+이평) 실시간 뷰 (Plotly + Streamlit).

  cd quant-trader
  pip install -r requirements.txt
  streamlit run tools/chart_web.py

기본 URL: http://localhost:8501
"""

from __future__ import annotations

import logging
import sys
from pathlib import Path

_ROOT = Path(__file__).resolve().parent.parent
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

log = logging.getLogger(__name__)

try:
    from streamlit_autorefresh import st_autorefresh

    _HAS_AUTOREFRESH = True
except ImportError:
    _HAS_AUTOREFRESH = False


def _main() -> None:
    import streamlit as st

    st.set_page_config(
        page_title="quant-trader chart",
        layout="wide",
        initial_sidebar_state="expanded",
    )

    from core.data_feed import DataFeed
    from core.portfolio import Portfolio

    from tools.chart_common import (
        build_strategy,
        candidate_display_rows,
        collect_chart_symbols,
        load_config,
        plotly_candlestick_figure,
        prepare_mock_broker,
        setup_logging,
        three_slots_for_strategy,
    )

    st.title("캔들 차트 (웹)")
    st.caption("키움 REST / Mock · Plotly 줌·팬 가능 · 사이드바에서 주기 새로고침")

    with st.sidebar:
        st.header("설정")
        config_path = st.text_input("config.yaml 경로", value="config.yaml")
        use_mock = st.checkbox("Mock (키움 없이 샘플)", value=False)
        mode = st.radio("모드", ["scan", "symbol"], horizontal=True)
        symbol_text = st.text_input(
            'symbol 모드 종목 (쉼표)',
            value="005930,000660",
            disabled=(mode != "symbol"),
        )
        period = st.text_input("주기", value="D", help='키움 REST: "D"|"W"|"M"')
        count = st.number_input("봉 개수", min_value=10, max_value=500, value=120)
        max_charts = st.number_input("스캔 시 최대 차트 수", min_value=1, max_value=24, value=8)
        show_mav = st.checkbox("이동평균 오버레이 (전략이 MA 크로스일 때)", value=True)
        no_fallback = st.checkbox("신호 없을 때 유니버스 fallback 끔", value=False)
        no_momentum_rank = st.checkbox("모멘텀 랭킹 fallback 끔", value=False)
        no_cache = st.checkbox("캐시 끄기 (매번 API)", value=False)
        layout_mode = st.radio("레이아웃", ["스캔 전체", "3슬롯 (전략)"], horizontal=False)
        verbose = st.checkbox("상세 로그", value=False)
        st.divider()
        auto_sec = st.number_input(
            "자동 새로고침(초) · 0이면 수동만",
            min_value=0,
            max_value=3600,
            value=0,
            step=10,
        )
        if _HAS_AUTOREFRESH and auto_sec > 0:
            st_autorefresh(interval=int(auto_sec) * 1000, key="quant_chart_refresh")
        elif auto_sec > 0 and not _HAS_AUTOREFRESH:
            st.warning("`pip install streamlit-autorefresh` 하면 자동 새로고침이 동작합니다.")
        st.caption("수동: 브라우저 새로고침 또는 아래 버튼")
        if st.button("지금 데이터 다시 불러오기"):
            st.rerun()

    setup_logging(verbose)

    cfg = load_config(config_path)
    engine_cfg = cfg.get("engine", {})
    universe: list[str] = list(engine_cfg.get("universe", ["005930"]))
    strategy_name, strategy = build_strategy(cfg)

    explicit: list[str] = []
    if mode == "symbol":
        explicit = [s.strip() for s in symbol_text.split(",") if s.strip()]
        if not explicit:
            st.error("symbol 모드에서는 종목코드를 입력하세요.")
            return

    if use_mock:
        mock_syms = list(dict.fromkeys(universe + explicit))
        broker = prepare_mock_broker(cfg, mock_syms)
    else:
        from core.broker import create_broker

        broker = create_broker(cfg)

    data_ttl = 0 if no_cache else engine_cfg.get("interval_sec", 60)
    data = DataFeed(broker, cache_ttl_sec=data_ttl)
    portfolio = Portfolio(initial_cash=cfg.get("account", {}).get("initial_cash", 10_000_000))

    if strategy.name == "momentum" and hasattr(strategy, "_rebalance_days"):
        strategy._days_since_rebalance = max(0, strategy._rebalance_days - 1)

    signals = strategy.generate_signals(universe, data, portfolio)

    if mode == "symbol":
        candidates = explicit
        note = "사용자 지정 종목"
    else:
        candidates, note = collect_chart_symbols(
            cfg,
            strategy,
            data,
            portfolio,
            universe,
            fallback_universe=not no_fallback,
            momentum_top_when_empty=not no_momentum_rank,
        )

    mav: tuple[int, ...] | None = None
    if show_mav and strategy_name == "moving_average_cross":
        sp = cfg.get("strategies", {}).get("moving_average_cross", {})
        mav = (sp.get("fast_period", 5), sp.get("slow_period", 20))

    st.info(f"**전략** `{strategy_name}` · **{note}** · 후보: `{candidates[:20]}{'…' if len(candidates) > 20 else ''}`")

    import plotly.io as pio

    pio.templates.default = "plotly_dark"

    if layout_mode == "스캔 전체":
        syms = list(candidates)
        if max_charts > 0:
            syms = syms[: int(max_charts)]
        if not syms:
            st.warning("표시할 종목이 없습니다.")
            return
        for sym in syms:
            df = data.get_ohlcv(sym, period=period, count=int(count), use_cache=not no_cache)
            title = f"{sym} | {strategy_name} | {period}"
            fig = plotly_candlestick_figure(df, title, mav=mav if show_mav else None)
            st.plotly_chart(fig, use_container_width=True)
            if df.empty:
                st.warning(f"{sym}: OHLCV 비어 있음")

    else:
        slot_syms, slot_labels = three_slots_for_strategy(
            strategy_name, strategy, signals, candidates, universe, data
        )
        init_key = f"slots_{','.join(slot_syms)}_{note}"
        if "slot_init_key" not in st.session_state or st.session_state.slot_init_key != init_key:
            st.session_state.slot_init_key = init_key
            st.session_state.slot_symbols = list(slot_syms)

        symbols_order, display_rows = candidate_display_rows(candidates, signals)
        col_pick, col_reset = st.columns([3, 1])
        with col_pick:
            which = st.selectbox("슬롯 선택", [0, 1, 2], format_func=lambda i: f"슬롯 {i + 1} ({slot_labels[i]})")
        with col_reset:
            st.write("")
            st.write("")
            if st.button("슬롯을 전략 기본값으로"):
                st.session_state.slot_symbols = list(slot_syms)
                st.rerun()

        sym_options = list(dict.fromkeys(symbols_order + universe))
        new_sym = st.selectbox("위 슬롯에 넣을 종목", sym_options, key="pick_symbol")
        if st.button("선택 종목으로 슬롯 반영"):
            ss = list(st.session_state.slot_symbols)
            if len(ss) < 3:
                ss = list(slot_syms)
            ss[which] = new_sym
            st.session_state.slot_symbols = ss[:3]
            st.rerun()

        slots = st.session_state.slot_symbols
        c0, c1, c2 = st.columns(3)
        for col, sym, lab in zip([c0, c1, c2], slots, slot_labels):
            with col:
                df = data.get_ohlcv(sym, period=period, count=int(count), use_cache=not no_cache)
                title = f"{sym} | {lab}"
                fig = plotly_candlestick_figure(
                    df,
                    title,
                    mav=mav if show_mav else None,
                    height=440,
                )
                st.plotly_chart(fig, use_container_width=True)
                if df.empty:
                    st.caption("데이터 없음")

        with st.expander("후보 리스트 (참고)"):
            for row in display_rows:
                st.text(row)


if __name__ == "__main__":
    _main()
