"""
Kiwoom OpenAPI+로 계좌/기간별 매매 내역을 조회하여 PostgreSQL(trades)에 저장하는 미니 에이전트.
Spring Backend와 동일 DB를 사용하면, Backend에서 해당 데이터를 읽어 성과 계산·온체인 커밋을 수행한다.

실행 예:
  python fetch_trades.py --account 12345678 --start 2025-01-01 --end 2025-01-31
  python fetch_trades.py --account 12345678 --start 2025-01-01 --end 2025-01-31 --db-url "postgresql://user:pass@localhost:5432/performance"

환경변수: DB_URL (postgresql://...) 로 연결 문자열 지정 가능.
의존성: pywin32 (COM), psycopg2-binary. 키움 OpenAPI+ 설치 및 로그인 필요.
"""

import argparse
import os
from pathlib import Path

try:
    import psycopg2
except ImportError:
    psycopg2 = None  # type: ignore

DEFAULT_DB_URL = os.environ.get("DB_URL", "postgresql://postgres:postgres@localhost:5432/performance")


def ensure_table(conn) -> None:
    cur = conn.cursor()
    schema_path = Path(__file__).parent / "schema.sql"
    with open(schema_path) as f:
        content = f.read()
    for stmt in content.split(";"):
        stmt = stmt.strip()
        if stmt and not stmt.startswith("--"):
            cur.execute(stmt)
    conn.commit()
    cur.close()


def fetch_trades_from_kiwoom(account_id: str, start_date: str, end_date: str) -> list[dict]:
    """
    키움 OpenAPI+로 체결 내역 조회.
    실제 구현 시: OCX TrCondition 조회 또는 GetChejanData/GetOrderList 등으로
    해당 기간 체결 건을 수집해 아래 포맷으로 반환.
    """
    return [
        {
            "account_id": account_id,
            "trade_date": "2025-01-15 09:30:00",
            "symbol": "005930",
            "side": "BUY",
            "qty": 10.0,
            "price": 70000.0,
            "fee": 0.0,
            "order_id": "ord1",
            "exec_id": "exec1",
            "strategy_tag": "",
        },
        {
            "account_id": account_id,
            "trade_date": "2025-01-16 14:00:00",
            "symbol": "005930",
            "side": "SELL",
            "qty": 10.0,
            "price": 72000.0,
            "fee": 0.0,
            "order_id": "ord2",
            "exec_id": "exec2",
            "strategy_tag": "",
        },
    ]


def save_trades(conn, trades: list[dict]) -> int:
    cur = conn.cursor()
    count = 0
    for t in trades:
        cur.execute(
            """INSERT INTO trades (account_id, trade_date, symbol, side, qty, price, fee, order_id, exec_id, strategy_tag)
               VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)""",
            (
                t["account_id"],
                t["trade_date"],
                t["symbol"],
                t["side"],
                t["qty"],
                t["price"],
                t.get("fee", 0),
                t.get("order_id"),
                t.get("exec_id"),
                t.get("strategy_tag") or "",
            ),
        )
        count += 1
    conn.commit()
    cur.close()
    return count


def main() -> None:
    if psycopg2 is None:
        raise RuntimeError("psycopg2 required. pip install psycopg2-binary")

    parser = argparse.ArgumentParser(description="Kiwoom 매매 내역 조회 → PostgreSQL 저장")
    parser.add_argument("--account", required=True, help="계좌번호(앞 8자 등)")
    parser.add_argument("--start", required=True, help="시작일 (YYYY-MM-DD)")
    parser.add_argument("--end", required=True, help="종료일 (YYYY-MM-DD)")
    parser.add_argument("--db-url", default=DEFAULT_DB_URL, help="PostgreSQL 연결 URL (또는 환경변수 DB_URL)")
    args = parser.parse_args()

    conn = psycopg2.connect(args.db_url)
    ensure_table(conn)
    trades = fetch_trades_from_kiwoom(args.account, args.start, args.end)
    n = save_trades(conn, trades)
    conn.close()
    print(f"Saved {n} trades to PostgreSQL ({args.db_url.split('@')[-1]})")


if __name__ == "__main__":
    main()
