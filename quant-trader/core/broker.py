"""
키움 브로커 추상화 레이어.

지원 모드:
  - KiwoomRestBroker   : 키움 REST API (서버 환경, 조회 중심)
  - KiwoomOpenApiBroker: 키움 OpenAPI+ COM 인터페이스 (Windows 로컬, 실제 주문 가능)
  - MockBroker         : 백테스트 / 개발용 가상 브로커

키움 REST API 참고:
  - 운영: https://api.kiwoom.com
  - 모의: https://mockapi.kiwoom.com
  - OAuth2 Client Credentials → 24시간 토큰
"""

from __future__ import annotations

import logging
import os
import threading
import time
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Literal

import pandas as pd
import requests

log = logging.getLogger(__name__)

Side = Literal["BUY", "SELL"]
OrderType = Literal["LIMIT", "MARKET"]


# ---------------------------------------------------------------------------
# 공통 데이터 클래스
# ---------------------------------------------------------------------------

@dataclass
class OrderResult:
    order_id: str
    symbol: str
    side: Side
    qty: int
    price: float
    status: str = "SUBMITTED"   # SUBMITTED | FILLED | CANCELLED | REJECTED


@dataclass
class Position:
    symbol: str
    qty: int
    avg_price: float
    current_price: float = 0.0

    @property
    def market_value(self) -> float:
        return self.qty * (self.current_price or self.avg_price)

    @property
    def unrealized_pnl(self) -> float:
        return self.qty * (self.current_price - self.avg_price)


# ---------------------------------------------------------------------------
# 추상 브로커
# ---------------------------------------------------------------------------

class BaseBroker(ABC):
    """브로커 인터페이스. 모든 구현체가 이 클래스를 상속."""

    @abstractmethod
    def get_price(self, symbol: str) -> float:
        """현재가 조회."""

    @abstractmethod
    def get_ohlcv(self, symbol: str, period: str = "D", count: int = 200) -> pd.DataFrame:
        """OHLCV 데이터 조회.

        Args:
            symbol: 종목코드 (예: "005930")
            period: "D"(일봉) | "W"(주봉) | "M"(월봉)
            count: 조회할 봉 수

        Returns:
            DataFrame with columns: [open, high, low, close, volume]
            index: datetime (최신 데이터가 마지막 행)
        """

    @abstractmethod
    def get_balance(self) -> dict:
        """예수금 / 주문가능금액 조회.

        Returns:
            {"cash": float, "orderable": float, "total_asset": float}
        """

    @abstractmethod
    def get_positions(self) -> dict[str, Position]:
        """보유 종목 조회. symbol -> Position"""

    @abstractmethod
    def place_order(
        self,
        symbol: str,
        side: Side,
        qty: int,
        order_type: OrderType = "MARKET",
        price: float = 0,
    ) -> OrderResult:
        """주문 제출."""

    @abstractmethod
    def cancel_order(self, order_id: str) -> bool:
        """주문 취소. 성공 시 True."""


# ---------------------------------------------------------------------------
# 키움 REST 브로커
# ---------------------------------------------------------------------------

class KiwoomRestBroker(BaseBroker):
    """
    키움 REST API 기반 브로커.

    조회 기능 위주 (체결 조회, 현재가, 일봉 등).
    주문 기능은 REST API 지원 범위 내에서 구현 (TR 코드 확인 필요).

    환경변수:
        KIWOOM_APPKEY, KIWOOM_SECRETKEY, KIWOOM_ACCOUNT
    """

    def __init__(self, appkey: str = "", secretkey: str = "", base_url: str = "", account_no: str = ""):
        self._appkey = appkey or os.environ.get("KIWOOM_APPKEY", "")
        self._secretkey = secretkey or os.environ.get("KIWOOM_SECRETKEY", "")
        self._base_url = base_url or "https://mockapi.kiwoom.com"
        self._account_no = account_no or os.environ.get("KIWOOM_ACCOUNT", "")

        self._token: str = ""
        self._token_expires_at: datetime = datetime.min
        self._token_lock = threading.Lock()

    # ------------------------------------------------------------------
    # 토큰 관리
    # ------------------------------------------------------------------

    def _ensure_token(self) -> str:
        """토큰이 없거나 만료 5분 전이면 재발급."""
        with self._token_lock:
            if datetime.now() < self._token_expires_at - timedelta(minutes=5):
                return self._token
            self._token = self._issue_token()
            self._token_expires_at = datetime.now() + timedelta(hours=24)
            log.info("키움 REST API 토큰 발급 완료.")
            return self._token

    def _issue_token(self) -> str:
        resp = requests.post(
            f"{self._base_url}/oauth2/token",
            json={
                "grant_type": "client_credentials",
                "appkey": self._appkey,
                "secretkey": self._secretkey,
            },
            timeout=10,
        )
        resp.raise_for_status()
        return resp.json()["token"]

    def _headers(self) -> dict:
        return {
            "Authorization": f"Bearer {self._ensure_token()}",
            "Content-Type": "application/json;charset=UTF-8",
        }

    def _tr_request(self, url: str, body: dict) -> dict:
        resp = requests.post(url, headers=self._headers(), json=body, timeout=10)
        resp.raise_for_status()
        return resp.json()

    # ------------------------------------------------------------------
    # 시장 데이터
    # ------------------------------------------------------------------

    def get_price(self, symbol: str) -> float:
        """
        TR: ka10001 (주식현재가조회)
        실제 TR 필드명은 키움 REST API 가이드 참고.
        """
        body = {"stk_cd": symbol}
        data = self._tr_request(f"{self._base_url}/api/dostk/stkbasicinfo", body)
        # TODO: 실제 응답 필드명으로 교체 (키움 가이드 참고)
        return float(data.get("cur_prc", 0))

    def get_ohlcv(self, symbol: str, period: str = "D", count: int = 200) -> pd.DataFrame:
        """
        TR: ka20001 (주식일봉차트조회) - 정확한 TR 코드는 키움 가이드 확인 필요.
        period 매핑: D -> 일봉, W -> 주봉, M -> 월봉
        """
        period_map = {"D": "1", "W": "2", "M": "3"}
        body = {
            "stk_cd": symbol,
            "period": period_map.get(period, "1"),
            "cnt": str(count),
        }
        data = self._tr_request(f"{self._base_url}/api/dostk/chart", body)
        rows = data.get("output2", [])  # TODO: 실제 응답 키 확인

        df = pd.DataFrame(rows)
        if df.empty:
            return pd.DataFrame(columns=["open", "high", "low", "close", "volume"])

        # TODO: 실제 필드명 매핑 (키움 가이드 참고)
        rename = {
            "stck_bsop_date": "date",
            "stck_oprc": "open",
            "stck_hgpr": "high",
            "stck_lwpr": "low",
            "stck_clpr": "close",
            "acml_vol": "volume",
        }
        df = df.rename(columns={k: v for k, v in rename.items() if k in df.columns})
        df["date"] = pd.to_datetime(df["date"])
        df = df.set_index("date").sort_index()
        for col in ["open", "high", "low", "close", "volume"]:
            if col in df.columns:
                df[col] = pd.to_numeric(df[col], errors="coerce")
        return df[["open", "high", "low", "close", "volume"]]

    def get_balance(self) -> dict:
        """TR: kt00001 계좌 예수금 조회 (정확한 TR 코드 키움 가이드 참고)."""
        body = {"acnt_no": self._account_no}
        data = self._tr_request(f"{self._base_url}/api/dostk/acnt", body)
        return {
            "cash": float(data.get("dnca_tot_amt", 0)),
            "orderable": float(data.get("nxdy_excc_amt", 0)),
            "total_asset": float(data.get("tot_evlu_amt", 0)),
        }

    def get_positions(self) -> dict[str, Position]:
        """TR: kt00018 보유 종목 조회 (정확한 TR 코드 키움 가이드 참고)."""
        body = {"acnt_no": self._account_no}
        data = self._tr_request(f"{self._base_url}/api/dostk/acnt", body)
        positions = {}
        for item in data.get("output1", []):
            symbol = item.get("stk_cd", "")
            if symbol:
                positions[symbol] = Position(
                    symbol=symbol,
                    qty=int(item.get("hldg_qty", 0)),
                    avg_price=float(item.get("pchs_avg_pric", 0)),
                    current_price=float(item.get("prpr", 0)),
                )
        return positions

    def place_order(
        self,
        symbol: str,
        side: Side,
        qty: int,
        order_type: OrderType = "MARKET",
        price: float = 0,
    ) -> OrderResult:
        """
        주식 주문 제출.
        TR: kt10000 계열 (정확한 TR 코드 및 필드는 키움 REST API 가이드 참고)
        """
        ord_dvsn = "01" if order_type == "MARKET" else "00"   # 00: 지정가, 01: 시장가
        buy_sell = "02" if side == "BUY" else "01"

        body = {
            "acnt_no": self._account_no,
            "stk_cd": symbol,
            "ord_qty": str(qty),
            "ord_unpr": str(int(price)),
            "ord_dvsn": ord_dvsn,
            "buy_sell_gb": buy_sell,
        }
        data = self._tr_request(f"{self._base_url}/api/dostk/ordr", body)
        order_id = data.get("ord_no", "")
        log.info(f"주문 제출: {side} {symbol} {qty}주 @ {price} → order_id={order_id}")
        return OrderResult(order_id=order_id, symbol=symbol, side=side, qty=qty, price=price)

    def cancel_order(self, order_id: str) -> bool:
        body = {"ord_no": order_id, "acnt_no": self._account_no}
        try:
            self._tr_request(f"{self._base_url}/api/dostk/ordr/cancel", body)
            return True
        except Exception as e:
            log.warning(f"주문 취소 실패 order_id={order_id}: {e}")
            return False


# ---------------------------------------------------------------------------
# 키움 OpenAPI+ (COM) 브로커 — Windows 전용
# ---------------------------------------------------------------------------

class KiwoomOpenApiBroker(BaseBroker):
    """
    키움 OpenAPI+ COM 인터페이스 기반 브로커 (Windows 로컬 전용).

    - pywin32 와 키움 HTS + OpenAPI+ 설치 필요
    - 실제 주문 / 체결 이벤트 수신 가능
    - COM 이벤트 처리는 QApplication 루프가 필요하므로 별도 스레드 or PyQt 환경에서 실행

    사용법:
        broker = KiwoomOpenApiBroker(account_no="12345678")
        broker.connect()   # 로그인 팝업 → 수동 입력
    """

    def __init__(self, account_no: str = ""):
        self._account_no = account_no or os.environ.get("KIWOOM_ACCOUNT", "")
        self._kiwoom = None   # COM 객체 (connect() 후 초기화)

    def connect(self):
        """키움 HTS 로그인 (COM 연결). Windows + pywin32 필요."""
        try:
            import win32com.client
            self._kiwoom = win32com.client.Dispatch("KHOPENAPI.KHOpenAPICtrl.1")
            self._kiwoom.CommConnect()
            log.info("키움 OpenAPI+ 연결 요청 완료 (로그인 팝업 확인 필요).")
        except ImportError:
            raise RuntimeError("pywin32 가 설치되지 않았습니다. pip install pywin32")
        except Exception as e:
            raise RuntimeError(f"키움 OpenAPI+ 연결 실패: {e}")

    def _check_connected(self):
        if self._kiwoom is None:
            raise RuntimeError("connect() 를 먼저 호출하세요.")

    # ------------------------------------------------------------------
    # TR 조회 헬퍼
    # ------------------------------------------------------------------

    def _set_and_request(self, tr_code: str, inputs: dict, screen_no: str = "1000") -> None:
        """SetInputValue + CommRqData 조합."""
        self._check_connected()
        for key, val in inputs.items():
            self._kiwoom.SetInputValue(key, val)
        self._kiwoom.CommRqData(tr_code, tr_code, 0, screen_no)

    # ------------------------------------------------------------------
    # BaseBroker 구현
    # ------------------------------------------------------------------

    def get_price(self, symbol: str) -> float:
        """opt10001 TR 로 현재가 조회."""
        self._check_connected()
        # TODO: TR 조회 후 GetCommData 로 현재가 파싱
        # 실제 구현 시 이벤트 수신(OnReceiveTrData) 처리 필요
        raise NotImplementedError("get_price: COM 이벤트 핸들러 연결 후 구현하세요.")

    def get_ohlcv(self, symbol: str, period: str = "D", count: int = 200) -> pd.DataFrame:
        """opt10081 (일봉) / opt10082 (주봉) / opt10083 (월봉) TR."""
        self._check_connected()
        tr_map = {"D": "opt10081", "W": "opt10082", "M": "opt10083"}
        tr_code = tr_map.get(period, "opt10081")
        # TODO: SetInputValue → CommRqData → OnReceiveTrData 이벤트에서 GetCommData 파싱
        raise NotImplementedError(f"get_ohlcv (TR={tr_code}): COM 이벤트 핸들러 구현 필요.")

    def get_balance(self) -> dict:
        """opw00001 (예수금) TR."""
        self._check_connected()
        raise NotImplementedError("get_balance: COM 이벤트 핸들러 구현 필요.")

    def get_positions(self) -> dict[str, Position]:
        """opw00018 (보유종목) TR."""
        self._check_connected()
        raise NotImplementedError("get_positions: COM 이벤트 핸들러 구현 필요.")

    def place_order(
        self,
        symbol: str,
        side: Side,
        qty: int,
        order_type: OrderType = "MARKET",
        price: float = 0,
    ) -> OrderResult:
        """
        SendOrder 로 주문 제출.

        주문유형:
            1: 지정가, 2: 시장가, 3: 조건부지정가, 5: 장전 시간외, 6: 장후 시간외
        매도수구분:
            1: 매도, 2: 매수
        """
        self._check_connected()
        order_type_code = 2 if order_type == "MARKET" else 1
        side_code = 2 if side == "BUY" else 1

        ret = self._kiwoom.SendOrder(
            "주문",            # 사용자 구분 명
            "0101",            # 화면번호
            self._account_no, # 계좌번호
            side_code,        # 주문유형 (1:매도, 2:매수)
            symbol,           # 종목코드
            qty,              # 주문수량
            int(price),       # 주문가격
            order_type_code,  # 거래구분 (1:지정가, 2:시장가 ...)
            "",               # 원주문번호 (신규: "")
        )
        if ret != 0:
            raise RuntimeError(f"SendOrder 실패 (ret={ret})")
        log.info(f"주문 제출 (COM): {side} {symbol} {qty}주 @ {price}")
        return OrderResult(order_id="", symbol=symbol, side=side, qty=qty, price=price)

    def cancel_order(self, order_id: str) -> bool:
        """SendOrder 취소 주문 (원주문번호 전달)."""
        self._check_connected()
        ret = self._kiwoom.SendOrder(
            "취소주문", "0102", self._account_no,
            3,       # 3: 취소
            "",      # 종목코드 (취소 시 불필요)
            0, 0, 3, # 수량/가격/거래구분
            order_id,
        )
        return ret == 0


# ---------------------------------------------------------------------------
# Mock 브로커 (백테스트 / 개발)
# ---------------------------------------------------------------------------

class MockBroker(BaseBroker):
    """
    실제 API 없이 동작하는 가상 브로커.
    백테스트 엔진 또는 로컬 개발 시 사용.
    OHLCV 데이터는 외부에서 주입(set_ohlcv)하거나 랜덤 생성.
    """

    def __init__(self, initial_cash: float = 10_000_000):
        self._cash = initial_cash
        self._positions: dict[str, Position] = {}
        self._ohlcv_store: dict[str, pd.DataFrame] = {}
        self._price_store: dict[str, float] = {}
        self._order_counter = 0
        self._orders: dict[str, OrderResult] = {}

    # ------------------------------------------------------------------
    # 데이터 주입 (백테스터에서 호출)
    # ------------------------------------------------------------------

    def set_ohlcv(self, symbol: str, df: pd.DataFrame) -> None:
        """백테스트용 OHLCV 데이터 주입."""
        self._ohlcv_store[symbol] = df

    def set_price(self, symbol: str, price: float) -> None:
        """현재가 수동 설정 (백테스트 타임스텝마다 호출)."""
        self._price_store[symbol] = price
        if symbol in self._positions:
            self._positions[symbol].current_price = price

    # ------------------------------------------------------------------
    # BaseBroker 구현
    # ------------------------------------------------------------------

    def get_price(self, symbol: str) -> float:
        return self._price_store.get(symbol, 0.0)

    def get_ohlcv(self, symbol: str, period: str = "D", count: int = 200) -> pd.DataFrame:
        df = self._ohlcv_store.get(symbol, pd.DataFrame())
        return df.tail(count) if not df.empty else df

    def get_balance(self) -> dict:
        total_asset = self._cash + sum(p.market_value for p in self._positions.values())
        return {"cash": self._cash, "orderable": self._cash, "total_asset": total_asset}

    def get_positions(self) -> dict[str, Position]:
        return dict(self._positions)

    def place_order(
        self,
        symbol: str,
        side: Side,
        qty: int,
        order_type: OrderType = "MARKET",
        price: float = 0,
    ) -> OrderResult:
        exec_price = price if price > 0 else self.get_price(symbol)
        cost = exec_price * qty

        if side == "BUY":
            if cost > self._cash:
                raise ValueError(f"잔액 부족: 필요={cost:,.0f} 보유={self._cash:,.0f}")
            self._cash -= cost
            if symbol in self._positions:
                pos = self._positions[symbol]
                total_qty = pos.qty + qty
                pos.avg_price = (pos.avg_price * pos.qty + cost) / total_qty
                pos.qty = total_qty
            else:
                self._positions[symbol] = Position(
                    symbol=symbol, qty=qty, avg_price=exec_price, current_price=exec_price
                )
        else:  # SELL
            pos = self._positions.get(symbol)
            if pos is None or pos.qty < qty:
                raise ValueError(f"보유 수량 부족: {symbol}")
            self._cash += exec_price * qty
            pos.qty -= qty
            if pos.qty == 0:
                del self._positions[symbol]

        self._order_counter += 1
        order_id = f"mock-{self._order_counter}"
        result = OrderResult(
            order_id=order_id, symbol=symbol, side=side,
            qty=qty, price=exec_price, status="FILLED"
        )
        self._orders[order_id] = result
        log.debug(f"[MockBroker] {side} {symbol} {qty}주 @ {exec_price:,.0f} | cash={self._cash:,.0f}")
        return result

    def cancel_order(self, order_id: str) -> bool:
        if order_id in self._orders:
            self._orders[order_id].status = "CANCELLED"
            return True
        return False


# ---------------------------------------------------------------------------
# 팩토리
# ---------------------------------------------------------------------------

def create_broker(cfg: dict) -> BaseBroker:
    """config.yaml 설정을 기반으로 적절한 브로커 인스턴스 반환."""
    mode = cfg.get("broker_mode", "mock")

    if mode == "rest":
        kiwoom_cfg = cfg.get("kiwoom", {})
        account_no = cfg.get("account", {}).get("account_no", "")
        return KiwoomRestBroker(
            appkey=kiwoom_cfg.get("appkey", ""),
            secretkey=kiwoom_cfg.get("secretkey", ""),
            base_url=kiwoom_cfg.get("base_url", "https://mockapi.kiwoom.com"),
            account_no=account_no,
        )
    elif mode == "openapi":
        account_no = cfg.get("account", {}).get("account_no", "")
        broker = KiwoomOpenApiBroker(account_no=account_no)
        broker.connect()
        return broker
    else:  # mock
        initial_cash = cfg.get("account", {}).get("initial_cash", 10_000_000)
        return MockBroker(initial_cash=initial_cash)
