"""
퀀트 트레이더 진입점.

사용법:
  # 실전/모의 트레이딩 (config.yaml 의 broker_mode 에 따라)
  python main.py trade

  # 백테스트 (MockBroker + 랜덤/샘플 데이터)
  python main.py backtest

  # 백테스트 (CSV 데이터 파일 지정)
  python main.py backtest --data-dir ./data

환경변수 (실전 시):
  KIWOOM_APPKEY, KIWOOM_SECRETKEY, KIWOOM_ACCOUNT
"""

from __future__ import annotations

import argparse
import logging
import os
import random
from pathlib import Path

import pandas as pd
import yaml
from dotenv import load_dotenv

# 로컬 API 키: quant-trader/.env 파일에서 로드 (Git 제외, .env.example 참고)
load_dotenv(Path(__file__).parent / ".env")

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    datefmt="%H:%M:%S",
)
log = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# 설정 로드
# ---------------------------------------------------------------------------

def load_config(path: str = "config.yaml") -> dict:
    cfg_path = Path(__file__).parent / path
    with open(cfg_path, encoding="utf-8") as f:
        cfg = yaml.safe_load(f)

    # 환경변수 오버라이드
    kiwoom = cfg.setdefault("kiwoom", {})
    if os.environ.get("KIWOOM_APPKEY"):
        kiwoom["appkey"] = os.environ["KIWOOM_APPKEY"]
    if os.environ.get("KIWOOM_SECRETKEY"):
        kiwoom["secretkey"] = os.environ["KIWOOM_SECRETKEY"]
    account = cfg.setdefault("account", {})
    if os.environ.get("KIWOOM_ACCOUNT"):
        account["account_no"] = os.environ["KIWOOM_ACCOUNT"]

<<<<<<< HEAD
    cr = cfg.setdefault("contract_report", {})
    if os.environ.get("CONTRACT_REPORT_API_URL"):
        cr["api_base_url"] = os.environ["CONTRACT_REPORT_API_URL"]
    if os.environ.get("CONTRACT_REPORT_USER_ID"):
        cr["user_id"] = os.environ["CONTRACT_REPORT_USER_ID"]
    env_en = os.environ.get("CONTRACT_REPORT_ENABLED", "").strip().lower()
    if env_en in ("1", "true", "yes", "on"):
        cr["enabled"] = True

=======
>>>>>>> feat/unit-tests
    return cfg


# ---------------------------------------------------------------------------
# 샘플 OHLCV 생성 (백테스트용, 실제 데이터 없을 때)
# ---------------------------------------------------------------------------

def generate_sample_ohlcv(
    symbol: str,
    start: str = "2024-01-01",
    end: str = "2024-12-31",
    start_price: float | None = None,
) -> pd.DataFrame:
    """
    랜덤 워크 기반 샘플 OHLCV 생성.
    실제 백테스트 시 이 함수 대신 CSV/API 에서 데이터를 로드하세요.
    """
    seed_map = {"005930": 42, "000660": 7, "035420": 13}
    random.seed(seed_map.get(symbol, hash(symbol) % 100))

    dates = pd.bdate_range(start=start, end=end)  # 영업일
    prices = []
    price = start_price or (50_000 + random.randint(-10_000, 30_000))

    for _ in dates:
        change = random.gauss(0, 0.015)   # 일일 변동률 평균 0, 표준편차 1.5%
        price = max(price * (1 + change), 1000)
        open_ = price * (1 + random.gauss(0, 0.003))
        high = max(price, open_) * (1 + abs(random.gauss(0, 0.005)))
        low = min(price, open_) * (1 - abs(random.gauss(0, 0.005)))
        volume = int(random.randint(100_000, 5_000_000))
        prices.append({
            "open": round(open_),
            "high": round(high),
            "low": round(low),
            "close": round(price),
            "volume": volume,
        })

    return pd.DataFrame(prices, index=dates)


def load_ohlcv_from_csv(data_dir: str, symbol: str) -> pd.DataFrame | None:
    """
    CSV 파일에서 OHLCV 로드.
    파일 형식: {symbol}.csv, 컬럼: date,open,high,low,close,volume
    """
    csv_path = Path(data_dir) / f"{symbol}.csv"
    if not csv_path.exists():
        return None
    df = pd.read_csv(csv_path, parse_dates=["date"], index_col="date")
    df = df[["open", "high", "low", "close", "volume"]].sort_index()
    return df


# ---------------------------------------------------------------------------
# 실전 트레이딩
# ---------------------------------------------------------------------------

def run_trade(cfg: dict) -> None:
    from core.engine import build_engine_from_config

    log.info(f"[Main] 트레이딩 모드: broker={cfg.get('broker_mode')}")
<<<<<<< HEAD
    cr = cfg.get("contract_report") or {}
    if cr.get("enabled"):
        log.info(
            "[Main] ContractReport 동기화: enabled (백엔드에 체결 등록)"
        )
=======
>>>>>>> feat/unit-tests
    engine = build_engine_from_config(cfg)
    engine.start()


# ---------------------------------------------------------------------------
# 백테스트
# ---------------------------------------------------------------------------

def run_backtest(cfg: dict, data_dir: str | None = None) -> None:
    from strategies.moving_average_cross import MovingAverageCrossStrategy
    from strategies.rsi_mean_reversion import RSIMeanReversionStrategy
    from strategies.momentum import MomentumStrategy
    from backtest.backtester import Backtester
    from backtest import metrics as m
    from core.risk_manager import RiskConfig

    strategy_name = cfg.get("engine", {}).get("strategy", "moving_average_cross")
    strategy_params = cfg.get("strategies", {}).get(strategy_name, {})
    strategy_map = {
        "moving_average_cross": MovingAverageCrossStrategy,
        "rsi_mean_reversion": RSIMeanReversionStrategy,
        "momentum": MomentumStrategy,
    }
    strategy = strategy_map[strategy_name](params=strategy_params)

    universe = cfg.get("engine", {}).get("universe", ["005930"])
    bt_cfg = cfg.get("backtest", {})
    start_date = bt_cfg.get("start_date", "2024-01-01")
    end_date = bt_cfg.get("end_date", "2024-12-31")
    initial_cash = cfg.get("account", {}).get("initial_cash", 10_000_000)

    # OHLCV 데이터 로드
    ohlcv_data: dict[str, pd.DataFrame] = {}
    for symbol in universe:
        df = None
        if data_dir:
            df = load_ohlcv_from_csv(data_dir, symbol)
        if df is None:
            log.info(f"[Main] {symbol}: CSV 없음 → 샘플 데이터 사용")
            df = generate_sample_ohlcv(symbol, start_date, end_date)
        ohlcv_data[symbol] = df

    bt = Backtester(
        strategy=strategy,
        universe=universe,
        ohlcv_data=ohlcv_data,
        initial_cash=initial_cash,
        commission_rate=bt_cfg.get("commission_rate", 0.00015),
        slippage_pct=bt_cfg.get("slippage_pct", 0.001),
        risk_cfg=RiskConfig.from_cfg(cfg),
    )

    result = bt.run(start_date=start_date, end_date=end_date)
    m.print_report(result)

    # 자산 곡선 CSV 저장
    equity_curve: pd.Series = result.get("equity_curve")
    if equity_curve is not None:
        out_path = Path(__file__).parent / "backtest_result.csv"
        equity_curve.to_csv(out_path, header=["equity"])
        log.info(f"[Main] 자산 곡선 저장: {out_path}")


<<<<<<< HEAD
def run_commit(
    cfg: dict,
    date_str: str | None,
    start_s: str | None,
    end_s: str | None,
    strategy_tag: str | None,
) -> None:
    """등록된 trades 기준으로 성과 요약을 온체인 커밋 (백엔드가 트랜잭션 전송)."""
    from datetime import datetime
    from zoneinfo import ZoneInfo

    from core.contract_report_client import client_from_config

    # commit 은 trade 동기화와 별개로 켤 수 있게 enabled 강제
    ccfg = {
        **cfg,
        "contract_report": {**(cfg.get("contract_report") or {}), "enabled": True},
    }
    client = client_from_config(ccfg)
    if not client:
        log.error(
            "[Main] commit 실패: contract_report.enabled 와 "
            "CONTRACT_REPORT_API_URL, CONTRACT_REPORT_USER_ID, KIWOOM_ACCOUNT 필요"
        )
        raise SystemExit(1)

    kst = ZoneInfo("Asia/Seoul")
    if date_str:
        d = datetime.strptime(date_str, "%Y-%m-%d").date()
        start = datetime(d.year, d.month, d.day, 0, 0, 0, tzinfo=kst)
        end = datetime(d.year, d.month, d.day, 23, 59, 59, tzinfo=kst)
    elif start_s and end_s:
        start = datetime.fromisoformat(start_s.replace("Z", "+00:00"))
        end = datetime.fromisoformat(end_s.replace("Z", "+00:00"))
    else:
        log.error("[Main] --date YYYY-MM-DD 또는 --start / --end 필요")
        raise SystemExit(2)

    # Spring 은 보통 로컬 DateTime; 타임존 있으면 naive 로 변환 (서버 TZ 와 맞출 것)
    start_naive = start.replace(tzinfo=None) if start.tzinfo else start
    end_naive = end.replace(tzinfo=None) if end.tzinfo else end

    log.info("[Main] performance commit 요청: %s ~ %s", start_naive, end_naive)
    out = client.commit_performance(start_naive, end_naive, strategy_tag)
    log.info("[Main] commit 응답: hashHex=%s txHash=%s", out.get("hashHex"), out.get("txHash"))


=======
>>>>>>> feat/unit-tests
# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def main() -> None:
    parser = argparse.ArgumentParser(description="퀀트 트레이더")
    parser.add_argument(
        "mode",
<<<<<<< HEAD
        choices=["trade", "backtest", "commit"],
        help="실행 모드: trade | backtest | commit (성과 온체인 커밋, 백엔드 호출)",
=======
        choices=["trade", "backtest"],
        help="실행 모드: trade (실전/모의) | backtest (백테스트)",
>>>>>>> feat/unit-tests
    )
    parser.add_argument(
        "--config", default="config.yaml", help="설정 파일 경로 (기본: config.yaml)"
    )
    parser.add_argument(
        "--data-dir",
        default=None,
        help="백테스트용 CSV 데이터 디렉토리 (없으면 샘플 데이터 사용)",
    )
<<<<<<< HEAD
    parser.add_argument(
        "--date",
        default=None,
        help="commit 모드: 기준일 YYYY-MM-DD (KST 하루 구간)",
    )
    parser.add_argument(
        "--start",
        default=None,
        help="commit 모드: 기간 시작 ISO (예: 2026-02-01T00:00:00)",
    )
    parser.add_argument(
        "--end",
        default=None,
        help="commit 모드: 기간 종료 ISO",
    )
    parser.add_argument(
        "--strategy-tag",
        default=None,
        help="commit 시 strategyTag 필터 (백엔드 PerformanceCommit 과 동일)",
    )
=======
>>>>>>> feat/unit-tests
    args = parser.parse_args()

    cfg = load_config(args.config)

    if args.mode == "trade":
        run_trade(cfg)
<<<<<<< HEAD
    elif args.mode == "backtest":
        run_backtest(cfg, data_dir=args.data_dir)
    else:
        run_commit(
            cfg,
            date_str=args.date,
            start_s=args.start,
            end_s=args.end,
            strategy_tag=args.strategy_tag,
        )
=======
    else:
        run_backtest(cfg, data_dir=args.data_dir)
>>>>>>> feat/unit-tests


if __name__ == "__main__":
    main()
