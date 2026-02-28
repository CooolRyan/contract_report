"""
백테스트 성과 지표 계산.

- 총 수익률
- 연환산 수익률 (CAGR)
- 샤프 비율
- 최대 낙폭 (MDD)
- 승률
- 손익비
"""

from __future__ import annotations

import math

import pandas as pd


def total_return(equity_curve: pd.Series) -> float:
    """총 수익률 (0.15 = 15%)."""
    if equity_curve.empty or equity_curve.iloc[0] == 0:
        return 0.0
    return equity_curve.iloc[-1] / equity_curve.iloc[0] - 1


def cagr(equity_curve: pd.Series, trading_days_per_year: int = 252) -> float:
    """연환산 수익률 (CAGR)."""
    n = len(equity_curve)
    if n < 2 or equity_curve.iloc[0] == 0:
        return 0.0
    years = n / trading_days_per_year
    return (equity_curve.iloc[-1] / equity_curve.iloc[0]) ** (1 / years) - 1


def sharpe_ratio(
    daily_returns: pd.Series,
    risk_free_rate: float = 0.03,
    trading_days: int = 252,
) -> float:
    """샤프 비율 (연환산)."""
    if daily_returns.empty or daily_returns.std() == 0:
        return 0.0
    excess = daily_returns - risk_free_rate / trading_days
    return excess.mean() / excess.std() * math.sqrt(trading_days)


def max_drawdown(equity_curve: pd.Series) -> float:
    """최대 낙폭 MDD (0.20 = 20% 하락)."""
    if equity_curve.empty:
        return 0.0
    cummax = equity_curve.cummax()
    dd = (equity_curve - cummax) / cummax
    return abs(dd.min())


def win_rate(trade_pnl: list[float]) -> float:
    """승률 (수익 거래 / 전체 거래)."""
    if not trade_pnl:
        return 0.0
    wins = sum(1 for p in trade_pnl if p > 0)
    return wins / len(trade_pnl)


def profit_factor(trade_pnl: list[float]) -> float:
    """손익비 (총 수익 / 총 손실)."""
    gross_profit = sum(p for p in trade_pnl if p > 0)
    gross_loss = sum(abs(p) for p in trade_pnl if p < 0)
    return gross_profit / gross_loss if gross_loss > 0 else float("inf")


def compute_all(
    equity_curve: pd.Series,
    trade_pnl: list[float] | None = None,
    risk_free_rate: float = 0.03,
) -> dict:
    """모든 지표를 계산하여 딕셔너리로 반환."""
    daily_returns = equity_curve.pct_change().dropna()
    trade_pnl = trade_pnl or []

    return {
        "total_return_pct": total_return(equity_curve) * 100,
        "cagr_pct": cagr(equity_curve) * 100,
        "sharpe_ratio": sharpe_ratio(daily_returns, risk_free_rate),
        "max_drawdown_pct": max_drawdown(equity_curve) * 100,
        "win_rate_pct": win_rate(trade_pnl) * 100,
        "profit_factor": profit_factor(trade_pnl),
        "total_trades": len(trade_pnl),
    }


def print_report(metrics: dict) -> None:
    """성과 요약 출력."""
    print("=" * 40)
    print("       백테스트 성과 요약")
    print("=" * 40)
    print(f"총 수익률     : {metrics.get('total_return_pct', 0):>+8.2f} %")
    print(f"연환산 수익률 : {metrics.get('cagr_pct', 0):>+8.2f} %")
    print(f"샤프 비율     : {metrics.get('sharpe_ratio', 0):>+8.2f}")
    print(f"최대 낙폭     : {metrics.get('max_drawdown_pct', 0):>8.2f} %")
    print(f"승률          : {metrics.get('win_rate_pct', 0):>8.2f} %")
    print(f"손익비        : {metrics.get('profit_factor', 0):>8.2f}")
    print(f"총 거래 건수  : {metrics.get('total_trades', 0):>8d} 건")
    print("=" * 40)
