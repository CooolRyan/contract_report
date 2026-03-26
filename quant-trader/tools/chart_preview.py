"""
OHLCV 캔들 차트 미리보기 (테스트·검증용).

공통 로직은 chart_common 참고.
사용 예:
  cd quant-trader
  python tools/chart_preview.py --mock --mode scan
  python tools/chart_preview.py --mode symbol --symbol 005930
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

from tools.chart_common import (  # noqa: E402
    build_strategy,
    collect_chart_symbols,
    load_config,
    plot_candles_file,
    prepare_mock_broker,
    setup_logging,
)


def plot_candles(
    df,
    title: str,
    out_path: Path,
    *,
    mav: tuple[int, ...] | None = None,
    show: bool,
) -> None:
    if show:
        import matplotlib

        matplotlib.use("TkAgg")
        import mplfinance as mpf
        import pandas as pd

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
        }
        if mav:
            kwargs["mav"] = mav
        mpf.plot(plot_df, **kwargs)
    else:
        plot_candles_file(df, title, out_path, mav=mav)


def run(args: argparse.Namespace) -> None:
    cfg = load_config(args.config)
    engine_cfg = cfg.get("engine", {})
    universe: list[str] = list(engine_cfg.get("universe", ["005930"]))
    strategy_name, strategy = build_strategy(cfg)
    period = args.period
    count = args.count

    explicit_symbols: list[str] = []
    if args.mode == "symbol":
        explicit_symbols = [s.strip() for s in args.symbol.split(",") if s.strip()]
        if not explicit_symbols:
            raise SystemExit("--mode symbol 일 때 --symbol 종목코드 필요 (쉼표 구분)")

    if args.mock:
        mock_syms = list(dict.fromkeys(universe + explicit_symbols))
        broker = prepare_mock_broker(cfg, mock_syms)
        log.info("[chart] MockBroker + 샘플 OHLCV 사용 (종목 수=%s)", len(mock_syms))
    else:
        from core.broker import create_broker

        broker = create_broker(cfg)
        log.info("[chart] broker_mode=%s", cfg.get("broker_mode"))

    data_ttl = 0 if args.no_cache else engine_cfg.get("interval_sec", 60)
    from core.data_feed import DataFeed
    from core.portfolio import Portfolio

    data = DataFeed(broker, cache_ttl_sec=data_ttl)

    initial_cash = cfg.get("account", {}).get("initial_cash", 10_000_000)
    portfolio = Portfolio(initial_cash=initial_cash)

    if args.mode == "symbol":
        symbols = explicit_symbols
        note = "사용자 지정 종목"
    else:
        symbols, note = collect_chart_symbols(
            cfg,
            strategy,
            data,
            portfolio,
            universe,
            fallback_universe=args.fallback_universe,
            momentum_top_when_empty=not args.no_momentum_rank,
        )

    if args.max_charts > 0:
        symbols = symbols[: args.max_charts]

    log.info("[chart] 모드=%s 전략=%s | %s | 종목=%s", args.mode, strategy_name, note, symbols)

    out_dir = Path(args.output_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    mav: tuple[int, ...] | None = None
    if args.mav and strategy_name == "moving_average_cross":
        sp = cfg.get("strategies", {}).get("moving_average_cross", {})
        fast = sp.get("fast_period", 5)
        slow = sp.get("slow_period", 20)
        mav = (fast, slow)

    for sym in symbols:
        df = data.get_ohlcv(sym, period=period, count=count, use_cache=not args.no_cache)
        if df.empty:
            log.warning("%s: OHLCV 비어 있음 (API/목 데이터 확인)", sym)
            continue
        title = f"{sym} | {strategy_name} | {period}"
        safe = sym.replace("/", "_")
        out_path = out_dir / f"chart_{safe}_{period}.png"
        plot_candles(
            df,
            title,
            out_path,
            mav=mav if args.mav else None,
            show=args.show,
        )
        if not args.show:
            log.info("저장: %s", out_path)


def main() -> None:
    parser = argparse.ArgumentParser(
        description="퀀트 트레이더 OHLCV 캔들 차트 미리보기 (mplfinance)"
    )
    parser.add_argument("--config", default="config.yaml", help="설정 파일")
    parser.add_argument(
        "--mode",
        choices=["scan", "symbol"],
        default="scan",
        help="scan=전략 조건 우선 종목 | symbol=종목코드 직접 지정",
    )
    parser.add_argument(
        "--symbol",
        default="",
        help='symbol 모드일 때 종목코드 (예: 005930 또는 "005930,000660")',
    )
    parser.add_argument(
        "--mock",
        action="store_true",
        help="키움 없이 MockBroker + 샘플 데이터로 차트 (로컬 테스트)",
    )
    parser.add_argument(
        "--period",
        default="D",
        help='OHLCV 주기 (브로커 지원 시). 키움 REST 구현: "D"|"W"|"M"',
    )
    parser.add_argument("--count", type=int, default=120, help="봉 개수")
    parser.add_argument(
        "--output-dir",
        default="chart_out",
        help="PNG 저장 디렉터리 (show 미사용 시)",
    )
    parser.add_argument(
        "--show",
        action="store_true",
        help="matplotlib 윈도우로 표시 (저장 대신)",
    )
    parser.add_argument(
        "--mav",
        action="store_true",
        help="이동평균 크로스 전략일 때 봉 위에 MA(단기/장기) 오버레이",
    )
    parser.add_argument(
        "--max-charts",
        type=int,
        default=8,
        help="scan 모드에서 저장할 최대 종목 수 (0=무제한)",
    )
    parser.add_argument(
        "--no-fallback-universe",
        action="store_true",
        help="신호가 없을 때 유니버스 전체 차트 안 함 (기본은 신호 없으면 유니버스 표시)",
    )
    parser.add_argument(
        "--no-momentum-rank",
        action="store_true",
        help="모멘텀 전략에서 신호 없을 때 상위 N 랭킹 대신 건너뜀",
    )
    parser.add_argument(
        "--no-cache",
        action="store_true",
        help="DataFeed 캐시 끄고 매번 조회",
    )
    parser.add_argument("-v", "--verbose", action="store_true")
    args = parser.parse_args()
    args.fallback_universe = not args.no_fallback_universe

    setup_logging(args.verbose)

    try:
        run(args)
    except ImportError as e:
        if "mplfinance" in str(e):
            log.error("mplfinance 가 필요합니다: pip install mplfinance")
            raise SystemExit(1) from e
        raise


if __name__ == "__main__":
    main()
