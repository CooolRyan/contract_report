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


def _kiwoom_chart_base_dt() -> str:
    """
    차트 TR base_dt: YYYYMMDD (KST).
    주말이면 직전 금요일로 맞춤(빈 응답 완화). 공휴일은 미처리.
    """
    try:
        from zoneinfo import ZoneInfo

        d = datetime.now(ZoneInfo("Asia/Seoul")).date()
    except Exception:
        d = datetime.now().date()
    while d.weekday() >= 5:  # 토·일 → 금요일
        d -= timedelta(days=1)
    return d.strftime("%Y%m%d")


# 분봉 ka10080: tic_scope (가이드) — 1,3,5,10,15,30,45,60 분
_KIWOOM_MINUTE_TIC: dict[str, str] = {
    "1m": "1",
    "3m": "3",
    "5m": "5",
    "10m": "10",
    "15m": "15",
    "30m": "30",
    "45m": "45",
    "60m": "60",
}


def _kiwoom_abs_num(val) -> float:
    """키움 시세 문자열(앞에 '-' 부호만 있는 경우) → 양의 실수."""
    if val is None:
        return float("nan")
    s = str(val).strip().replace(",", "")
    if not s or s == "-":
        return float("nan")
    try:
        return abs(float(s))
    except ValueError:
        return float("nan")


def _coerce_chart_rows(v) -> list:
    """리스트 / 단일 dict / 중첩 dict 에서 봉 배열 추출."""
    if v is None:
        return []
    if isinstance(v, list):
        return v if v else []
    if isinstance(v, dict):
        sample = v
        if any(
            k in sample
            for k in ("stck_clpr", "cur_prc", "open_pric", "stck_oprc", "cntr_tm", "stck_bsop_date")
        ):
            return [sample]
        for sub in v.values():
            if isinstance(sub, list) and sub:
                return sub
    return []


def _chart_rows_from_response(data: dict) -> list:
    """일봉·주봉·월봉·분봉 응답에서 OHLCV 행 배열 추출 (키움 가이드·실응답 변형 대응)."""
    if not isinstance(data, dict):
        return []
    priority = (
        "stk_min_pole_chart_qry",  # ka10080 분봉
        "stk_day_pole_chart_qry",  # ka10081 일봉(가이드 명칭 예시)
        "stk_bsop_chart_qry",
        "stk_daly_chart_qry",
        "stk_chart_qry",
        "output2",
        "output1",
        "output",
    )
    for key in priority:
        rows = _coerce_chart_rows(data.get(key))
        if rows:
            return rows
    skip_top = {"return_code", "return_msg", "return_msg_cd", "stk_cd"}
    for k, v in data.items():
        if k in skip_top:
            continue
        rows = _coerce_chart_rows(v)
        if not rows or not isinstance(rows[0], dict):
            continue
        row0 = rows[0]
        if any(
            x in row0
            for x in (
                "stck_clpr",
                "cur_prc",
                "open_pric",
                "stck_oprc",
                "cntr_tm",
                "stck_bsop_date",
                "stck_hgpr",
                "dt",
            )
        ):
            return rows
    return []


def _dataframe_to_ohlcv_standard(df: pd.DataFrame) -> pd.DataFrame:
    """표준 컬럼 open,high,low,close,volume + DatetimeIndex."""
    if df.empty:
        return pd.DataFrame(columns=["open", "high", "low", "close", "volume"])

    # 분봉(ka10080): cntr_tm, open_pric, high_pric, low_pric, cur_prc, trde_qty (가이드 응답)
    if "cntr_tm" in df.columns:
        out = pd.DataFrame()
        for dst, src in [
            ("open", "open_pric"),
            ("high", "high_pric"),
            ("low", "low_pric"),
            ("close", "cur_prc"),
        ]:
            out[dst] = df[src].map(_kiwoom_abs_num) if src in df.columns else float("nan")
        if "trde_qty" in df.columns:
            out["volume"] = pd.to_numeric(
                df["trde_qty"].astype(str).str.replace(",", "").str.lstrip("-"),
                errors="coerce",
            )
        else:
            out["volume"] = float("nan")
        out.index = pd.to_datetime(df["cntr_tm"].astype(str), format="%Y%m%d%H%M%S", errors="coerce")
        out = out.sort_index()
        return out

    # 일/주/월(ka10081~83): stck_* 또는 실응답 필드 (dt=일자, cur_prc=종가 등)
    rename = {
        "stck_bsop_date": "date",
        "bsop_date": "date",
        "date": "date",
        "dt": "date",  # REST 일봉 응답에서 흔함
        "stck_oprc": "open",
        "open_pric": "open",
        "stck_hgpr": "high",
        "high_pric": "high",
        "stck_lwpr": "low",
        "low_pric": "low",
        "stck_clpr": "close",
        "cur_prc": "close",
        "acml_vol": "volume",
        "trde_qty": "volume",
    }
    df = df.rename(columns={k: v for k, v in rename.items() if k in df.columns})
    if "date" not in df.columns:
        return pd.DataFrame(columns=["open", "high", "low", "close", "volume"])
    # dt 가 YYYYMMDD 문자열인 경우
    raw_dt = df["date"].astype(str).str.strip()
    if raw_dt.str.match(r"^\d{8}$").all():
        df["date"] = pd.to_datetime(raw_dt, format="%Y%m%d", errors="coerce")
    else:
        df["date"] = pd.to_datetime(df["date"], errors="coerce")
    df = df.set_index("date").sort_index()
    for col in ["open", "high", "low", "close", "volume"]:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col].astype(str).str.replace(",", ""), errors="coerce")
    return df[["open", "high", "low", "close", "volume"]]


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
            period: ``D``/``W``/``M``(일·주·월봉, Kiwoom REST) 또는 ``1m``~``60m``(분봉, ka10080)
            count: 조회할 봉 수 (일봉 등; 분봉 TR은 API·연속조회에 따름)

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
            now = datetime.now()
            # 토큰이 있고, 만료 시각이 유효하며, 만료 5분 전이 아니면 기존 토큰 사용
            if (
                self._token
                and self._token_expires_at > datetime.min
                and now < self._token_expires_at - timedelta(minutes=5)
            ):
                return self._token
            self._token = self._issue_token()
            self._token_expires_at = now + timedelta(hours=24)
            log.info("키움 REST API 토큰 발급 완료.")
            return self._token

    def _issue_token(self) -> str:
        if not (self._appkey and self._secretkey):
            raise RuntimeError(
                "KIWOOM_APPKEY / KIWOOM_SECRETKEY 가 비어 있습니다. "
                "config.yaml 의 kiwoom 또는 .env 를 확인하세요."
            )
        base = (self._base_url or "").rstrip("/")
        url = f"{base}/oauth2/token"
        headers = {"Content-Type": "application/json;charset=UTF-8"}
        body = {
            "grant_type": "client_credentials",
            "appkey": self._appkey,
            "secretkey": self._secretkey,
        }
        resp = requests.post(url, headers=headers, json=body, timeout=15)
        resp.raise_for_status()

        try:
            data = resp.json()
        except ValueError as e:
            log.error("OAuth 응답이 JSON이 아님: %s", resp.text[:500])
            raise RuntimeError("키움 OAuth 응답 파싱 실패 (본문이 JSON 아님)") from e

        # 실패 시 token 없이 return_code / return_msg 만 오는 경우가 많음
        rc = data.get("return_code")
        if rc is not None and int(rc) != 0:
            msg = data.get("return_msg", data.get("message", str(data)))
            raise RuntimeError(f"키움 OAuth 실패 return_code={rc}: {msg}")

        token = data.get("token") or data.get("access_token")
        if not token:
            log.error(
                "OAuth 응답에 token/access_token 없음. keys=%s body=%s",
                list(data.keys()),
                data,
            )
            raise RuntimeError(
                "키움 OAuth 응답에 토큰 필드가 없습니다. "
                "appkey/secretkey·모의/실전 URL·IP 등록을 확인하세요."
            )
        return str(token).strip()

    def _headers(self, api_id: str = "") -> dict:
        h = {
            "Authorization": f"Bearer {self._ensure_token()}",
            "Content-Type": "application/json;charset=UTF-8",
        }
        if api_id:
            h["api-id"] = api_id
        return h

    # URI 는 API ID 마다 다름. 국내주식 «차트» TR 은 /api/dostk/chart (가이드 목차 기준)
    # ka10079~83: 틱/분/일/주/월봉 — ka20001 은 업종 등 다른 중분류용이므로 일봉에 쓰면 안 됨
    _TR_PATH: dict[str, str] = {
        "kt00003": "/api/dostk/acnt",
        "kt00007": "/api/dostk/acnt",
        "kt00018": "/api/dostk/acnt",
        "kt10000": "/api/dostk/ordr",
        "kt10001": "/api/dostk/ordr",
        "ka10001": "/api/dostk/mrkcond",
        "ka10004": "/api/dostk/mrkcond",
        "ka10079": "/api/dostk/chart",
        "ka10080": "/api/dostk/chart",
        "ka10081": "/api/dostk/chart",
        "ka10082": "/api/dostk/chart",
        "ka10083": "/api/dostk/chart",
    }

    def _tr_request(self, api_id: str, body: dict, path: str | None = None) -> dict:
        """TR 호출. api_id(TR코드) 필수. path 없으면 _TR_PATH 또는 kt*->acnt, ka*->ordr."""
        if path is None:
            path = self._TR_PATH.get(api_id)
            if not path:
                path = "/api/dostk/acnt" if api_id.startswith("kt") else "/api/dostk/ordr"
        url = f"{self._base_url.rstrip('/')}{path}"
        headers = self._headers(api_id)
        payload = body or {}
        log.debug("TR 요청: api_id=%s url=%s body=%s", api_id, url, payload)
        resp = requests.post(url, headers=headers, json=payload, timeout=10)
        resp.raise_for_status()
        data = resp.json()
        if data.get("return_code") and int(data.get("return_code", 0)) != 0:
            err_msg = data.get("return_msg", "TR error")
            log.error("TR 실패 api_id=%s path=%s: %s", api_id, path, data)
            raise RuntimeError(f"{err_msg} (api_id={api_id})")
        return data

    # ------------------------------------------------------------------
    # 시장 데이터
    # ------------------------------------------------------------------

    def get_price(self, symbol: str) -> float:
        """TR: ka10004 (주식호가요청, mrkcond). 1차 매도호가(sel_fpr_bid)를 현재가로 사용."""
        body = {"stk_cd": symbol}
        data = self._tr_request("ka10004", body)
        # 호가 응답: sel_fpr_bid=1차매도호가, buy_fpr_bid=1차매수호가 (음수로 오면 절댓값)
        sel = data.get("sel_fpr_bid") or data.get("buy_fpr_bid") or 0
        try:
            return abs(int(sel))
        except (TypeError, ValueError):
            return 0.0

    def get_ohlcv(self, symbol: str, period: str = "D", count: int = 200) -> pd.DataFrame:
        """
        국내주식 차트 (POST /api/dostk/chart).

        - 일/주/월: ``D`` / ``W`` / ``M`` → ka10081 / ka10082 / ka10083, 응답은 ``output1``·``output2`` 등
        - 분봉: ``1m`` ``3m`` ``5m`` … ``60m`` → ka10080, 필수 ``tic_scope``, 응답 ``stk_min_pole_chart_qry`` (가이드)
        """
        base_dt = _kiwoom_chart_base_dt()

        # 분봉 ka10080 (주식분봉차트조회요청)
        if period in _KIWOOM_MINUTE_TIC:
            api_id = "ka10080"
            body = {
                "stk_cd": symbol,
                "tic_scope": _KIWOOM_MINUTE_TIC[period],
                "upd_stkpc_tp": "1",
                "base_dt": base_dt,  # 가이드 Request 예시에 포함 (선택일 수 있으나 동일 형식 유지)
            }
        else:
            period_to_api = {"D": "ka10081", "W": "ka10082", "M": "ka10083"}
            api_id = period_to_api.get(period, "ka10081")
            body = {
                "stk_cd": symbol,
                "base_dt": base_dt,
                "cnt": str(count),
                "upd_stkpc_tp": "1",
            }
        data = self._tr_request(api_id, body)

        rows = _chart_rows_from_response(data)
        if not rows:
            log.warning(
                "OHLCV: parsed row list empty. api_id=%s symbol=%s base_dt=%s response_keys=%s",
                api_id,
                symbol,
                base_dt,
                list(data.keys()),
            )
            return pd.DataFrame(columns=["open", "high", "low", "close", "volume"])

        df = pd.DataFrame(rows)
        if df.empty:
            return pd.DataFrame(columns=["open", "high", "low", "close", "volume"])

        out = _dataframe_to_ohlcv_standard(df)
        if out.empty:
            log.warning(
                "OHLCV: 매핑 후 데이터 없음. api_id=%s symbol=%s df_columns=%s",
                api_id,
                symbol,
                list(df.columns),
            )
        return out

    def get_balance(self) -> dict:
        """TR: kt00003 (추정자산조회). Body: qry_tp (0=전체, 1=상장폐지제외). 응답: prsm_dpst_aset_amt."""
        data = self._tr_request("kt00003", {"qry_tp": "0"})
        amt = data.get("prsm_dpst_aset_amt") or data.get("output", {}).get("prsm_dpst_aset_amt") or "0"
        try:
            total = float(str(amt).strip())
        except (TypeError, ValueError):
            total = 0.0
        return {"cash": total, "orderable": total, "total_asset": total}

    def get_positions(self) -> dict[str, Position]:
        """TR: 보유 종목 조회. 정확한 TR 코드·필드는 키움 가이드 참고."""
        body = {"acnt_no": self._account_no}
        data = self._tr_request("kt00018", body)
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
        data = self._tr_request("kt10000", body)  # 주문 TR (가이드 확인)
        order_id = data.get("ord_no", data.get("output", {}).get("ord_no", ""))
        log.info(f"주문 제출: {side} {symbol} {qty}주 @ {price} → order_id={order_id}")
        return OrderResult(order_id=order_id, symbol=symbol, side=side, qty=qty, price=price)

    def cancel_order(self, order_id: str) -> bool:
        body = {"ord_no": order_id, "acnt_no": self._account_no}
        try:
            self._tr_request("kt10001", body)  # 취소 TR (가이드 확인)
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
