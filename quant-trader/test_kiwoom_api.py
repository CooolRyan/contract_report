"""키움 REST API 연결 테스트. .env + config.yaml 사용. --debug: raw 응답 출력, -v: 로그 상세."""
from pathlib import Path
import sys
import json
import logging

# quant-trader 루트를 path에 추가
_root = Path(__file__).resolve().parent
sys.path.insert(0, str(_root))

from dotenv import load_dotenv
load_dotenv(_root / ".env")

import os
import yaml

def load_config():
    with open(_root / "config.yaml", encoding="utf-8") as f:
        cfg = yaml.safe_load(f)
    kiwoom = cfg.setdefault("kiwoom", {})
    if os.environ.get("KIWOOM_APPKEY"):
        kiwoom["appkey"] = os.environ["KIWOOM_APPKEY"]
    if os.environ.get("KIWOOM_SECRETKEY"):
        kiwoom["secretkey"] = os.environ["KIWOOM_SECRETKEY"]
    account = cfg.setdefault("account", {})
    if os.environ.get("KIWOOM_ACCOUNT"):
        account["account_no"] = os.environ["KIWOOM_ACCOUNT"]
    return cfg

def main():
    import argparse as _argparse
    parser = _argparse.ArgumentParser()
    parser.add_argument("--debug", action="store_true", help="Print raw API response JSON for balance/price")
    parser.add_argument("--verbose", "-v", action="store_true", help="Show detailed request/response on error (logging DEBUG)")
    args = parser.parse_args()
    debug = args.debug
    if args.verbose:
        logging.basicConfig(level=logging.DEBUG, format="%(levelname)s %(name)s: %(message)s")
        logging.getLogger("core.broker").setLevel(logging.DEBUG)

    cfg = load_config()
    if cfg.get("broker_mode") != "rest":
        print("config.yaml 에서 broker_mode: rest 로 설정한 뒤 다시 실행하세요.")
        return

    appkey = cfg.get("kiwoom", {}).get("appkey") or os.environ.get("KIWOOM_APPKEY")
    secretkey = cfg.get("kiwoom", {}).get("secretkey") or os.environ.get("KIWOOM_SECRETKEY")
    account_no = cfg.get("account", {}).get("account_no") or os.environ.get("KIWOOM_ACCOUNT")
    base_url = cfg.get("kiwoom", {}).get("base_url", "https://mockapi.kiwoom.com")

    if not appkey or not secretkey:
        print("KIWOOM_APPKEY, KIWOOM_SECRETKEY 가 .env 또는 config.yaml 에 필요합니다.")
        return

    print("키움 REST API 테스트")
    print("  base_url:", base_url)
    print("  account_no:", account_no or "(미설정)")
    print()

    from core.broker import KiwoomRestBroker

    broker = KiwoomRestBroker(
        appkey=appkey,
        secretkey=secretkey,
        base_url=base_url,
        account_no=account_no or "",
    )

    # 1) 토큰 발급
    print("[1] 토큰 발급 ...")
    try:
        token = broker._issue_token()
        print("    OK. token (앞 20자):", (token or "")[:20] + "...")
    except Exception as e:
        print("    실패:", e)
        return

    if account_no:
        print("[2] 잔고 조회 ...")
        try:
            if debug:
                raw = broker._tr_request("kt00003", {"qry_tp": "0"})
                print("    [DEBUG] raw response:", json.dumps(raw, ensure_ascii=False, indent=2))
            bal = broker.get_balance()
            print("    OK. cash:", bal.get("cash"), "| orderable:", bal.get("orderable"), "| total_asset:", bal.get("total_asset"))
        except Exception as e:
            print("    실패:", e)
    else:
        print("[2] 잔고 조회 건너뜀 (KIWOOM_ACCOUNT 미설정)")

    print("[3] 현재가 조회 (005930) ...")
    try:
        if debug:
            raw = broker._tr_request("ka10004", {"stk_cd": "005930"})
            print("    [DEBUG] raw response:", json.dumps(raw, ensure_ascii=False, indent=2))
        price = broker.get_price("005930")
        print("    OK. 005930 현재가:", price)
    except Exception as e:
        print("    실패:", e)

    print()
    print("테스트 끝.")

if __name__ == "__main__":
    main()
