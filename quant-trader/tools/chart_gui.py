"""
3슬롯 캔들 차트 + 우측 후보 종목 리스트 (클릭 시 선택 슬롯에 반영).

- 슬롯 3개 배치는 전략별 규칙 (chart_common.three_slots_for_strategy).
- 좌측 하단 라디오로 «어느 슬롯을 바꿀지» 선택 후, 우측 리스트에서 종목 클릭.

실행:
  cd quant-trader
  python tools/chart_gui.py --mock
"""

from __future__ import annotations

import argparse
import logging
import sys
from pathlib import Path

_ROOT = Path(__file__).resolve().parent.parent
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

log = logging.getLogger(__name__)


def _draw_candle_on_ax(ax, df, title: str, mav: tuple[int, ...] | None) -> None:
    import pandas as pd
    import mplfinance as mpf

    ax.clear()
    if df.empty:
        ax.set_title(f"{title} (no data)")
        return
    plot_df = df.copy()
    if not isinstance(plot_df.index, pd.DatetimeIndex):
        plot_df.index = pd.to_datetime(plot_df.index)

    kwargs: dict = {
        "type": "candle",
        "style": "yahoo",
        "ax": ax,
        "volume": False,
        "title": title,
    }
    if mav:
        kwargs["mav"] = mav
    mpf.plot(plot_df, **kwargs)


def run_gui(args: argparse.Namespace) -> None:
    import matplotlib

    matplotlib.use("TkAgg")
    import matplotlib.pyplot as plt
    import tkinter as tk
    from tkinter import ttk
    from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg

    from core.data_feed import DataFeed
    from core.portfolio import Portfolio

    from tools.chart_common import (
        build_strategy,
        candidate_display_rows,
        collect_chart_symbols,
        load_config,
        prepare_mock_broker,
        setup_logging,
        three_slots_for_strategy,
    )

    setup_logging(args.verbose)
    cfg = load_config(args.config)
    engine_cfg = cfg.get("engine", {})
    universe: list[str] = list(engine_cfg.get("universe", ["005930"]))
    strategy_name, strategy = build_strategy(cfg)

    explicit: list[str] = []
    if args.mode == "symbol":
        explicit = [s.strip() for s in args.symbol.split(",") if s.strip()]
        if not explicit:
            raise SystemExit("--mode symbol 일 때 --symbol 필요")

    if args.mock:
        mock_syms = list(dict.fromkeys(universe + explicit))
        broker = prepare_mock_broker(cfg, mock_syms)
        log.info("[gui] MockBroker, symbols=%s", len(mock_syms))
    else:
        from core.broker import create_broker

        broker = create_broker(cfg)

    data_ttl = 0 if args.no_cache else engine_cfg.get("interval_sec", 60)
    data = DataFeed(broker, cache_ttl_sec=data_ttl)
    portfolio = Portfolio(initial_cash=cfg.get("account", {}).get("initial_cash", 10_000_000))

    # 모멘텀: 신호 유도
    if strategy.name == "momentum" and hasattr(strategy, "_rebalance_days"):
        strategy._days_since_rebalance = max(0, strategy._rebalance_days - 1)

    signals = strategy.generate_signals(universe, data, portfolio)

    if args.mode == "symbol":
        candidates = explicit
    else:
        candidates, _note = collect_chart_symbols(
            cfg,
            strategy,
            data,
            portfolio,
            universe,
            fallback_universe=not args.no_fallback_universe,
            momentum_top_when_empty=not args.no_momentum_rank,
        )

    slot_symbols, slot_labels = three_slots_for_strategy(
        strategy_name, strategy, signals, candidates, universe, data
    )

    mav: tuple[int, ...] | None = None
    if args.mav and strategy_name == "moving_average_cross":
        sp = cfg.get("strategies", {}).get("moving_average_cross", {})
        mav = (sp.get("fast_period", 5), sp.get("slow_period", 20))

    symbols_order, display_rows = candidate_display_rows(candidates, signals)

    # --- Tk ---
    root = tk.Tk()
    root.title("quant-trader chart (3 slots + list)")
    root.geometry("1200x520")

    main = ttk.PanedWindow(root, orient=tk.HORIZONTAL)
    main.pack(fill=tk.BOTH, expand=True)

    left = ttk.Frame(main)
    right = ttk.Frame(main, width=280)
    main.add(left, weight=3)
    main.add(right, weight=1)

    plt.style.use("default")
    fig, axes = plt.subplots(1, 3, figsize=(12, 3.8))
    fig.tight_layout(pad=1.2)
    canvas = FigureCanvasTkAgg(fig, master=left)
    canvas.get_tk_widget().pack(fill=tk.BOTH, expand=True)

    slot_var = tk.IntVar(value=0)
    rf = ttk.LabelFrame(left, text="Replace slot (then click list)")
    rf.pack(fill=tk.X)
    for i in range(3):
        ttk.Radiobutton(
            rf,
            text=f"Slot {i + 1} ({slot_labels[i]})",
            variable=slot_var,
            value=i,
        ).pack(side=tk.LEFT, padx=6, pady=4)

    ttk.Label(right, text="Candidates (strategy filter)", font=("Segoe UI", 10, "bold")).pack(anchor=tk.W)
    list_frame = ttk.Frame(right)
    list_frame.pack(fill=tk.BOTH, expand=True)
    scrollbar = ttk.Scrollbar(list_frame)
    scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
    lb = tk.Listbox(list_frame, height=18, yscrollcommand=scrollbar.set, font=("Consolas", 10))
    lb.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
    scrollbar.config(command=lb.yview)

    for row in display_rows:
        lb.insert(tk.END, row)

    status = ttk.Label(right, text=f"strategy={strategy_name} | period={args.period}")
    status.pack(anchor=tk.W, pady=4)

    period = args.period
    count = args.count
    use_cache = not args.no_cache

    def refresh_slot(i: int) -> None:
        sym = slot_symbols[i]
        df = data.get_ohlcv(sym, period=period, count=count, use_cache=use_cache)
        title = f"{sym} | {slot_labels[i]}"
        _draw_candle_on_ax(axes[i], df, title, mav if args.mav else None)
        canvas.draw_idle()

    def on_list_select(_event=None) -> None:
        sel = lb.curselection()
        if not sel:
            return
        idx = sel[0]
        if idx >= len(symbols_order):
            return
        sym = symbols_order[idx]
        which = slot_var.get()
        slot_symbols[which] = sym
        refresh_slot(which)
        status.config(
            text=f"strategy={strategy_name} | slot{which+1} <- {sym}",
        )

    lb.bind("<<ListboxSelect>>", on_list_select)

    def redraw_all() -> None:
        for i in range(3):
            refresh_slot(i)

    ttk.Button(right, text="Redraw all slots", command=redraw_all).pack(anchor=tk.W, pady=4)

    redraw_all()
    root.mainloop()
    plt.close(fig)


def main() -> None:
    p = argparse.ArgumentParser(description="3-slot candle GUI + candidate list")
    p.add_argument("--config", default="config.yaml")
    p.add_argument("--mode", choices=["scan", "symbol"], default="scan")
    p.add_argument("--symbol", default="", help="symbol 모드: 쉼표 구분 종목코드")
    p.add_argument("--mock", action="store_true")
    p.add_argument("--period", default="D")
    p.add_argument("--count", type=int, default=120)
    p.add_argument("--mav", action="store_true", help="MA 전략 시 이평 오버레이")
    p.add_argument("--no-fallback-universe", action="store_true")
    p.add_argument("--no-momentum-rank", action="store_true")
    p.add_argument("--no-cache", action="store_true")
    p.add_argument("-v", "--verbose", action="store_true")
    args = p.parse_args()
    args.fallback_universe = not args.no_fallback_universe
    run_gui(args)


if __name__ == "__main__":
    main()
