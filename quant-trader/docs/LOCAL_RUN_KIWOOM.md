# 로컬에서 키움 API 기반 매매 프로그램 실행하기

quant-trader는 **세 가지 브로커 모드**를 지원합니다. 로컬에서 키움 API로 실행하려면 **REST** 또는 **OpenAPI** 중 하나를 선택해 설정하면 됩니다.

---

## 1. 실행 모드 요약

| 모드 | 설명 | 로컬 실행 시 필요 조건 |
|------|------|------------------------|
| **mock** | API 없이 가상 브로커 (백테스트/개발) | 설정 없이 바로 실행 가능 |
| **rest** | 키움 REST API (OAuth2, 서버/모의투자) | APPKEY·SECRETKEY·계좌번호, Python + requests |
| **openapi** | 키움 OpenAPI+ COM (Windows, 실제 주문) | Windows + 키움 HTS + OpenAPI+ 설치 + pywin32 |

---

## 2. 공통 준비 (모든 모드)

### 2.1 Python 환경

- **Python 3.10+** 권장
- 프로젝트 루트: `quant-trader/`

```powershell
cd quant-trader
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

### 2.2 실행 명령

- **실전/모의 트레이딩** (엔진이 주기적으로 신호 체크 후 주문):  
  `python main.py trade`
- **백테스트** (API 없이 과거 데이터로 전략 검증):  
  `python main.py backtest`  
  또는 `python main.py backtest --data-dir ./data` (CSV 사용 시)

---

## 3. 모드별 로컬 실행 과정

### 3.1 mock (바로 실행)

- **config.yaml**에서 `broker_mode: mock` 이면 이미 동작 가능.
- 키움 API/계좌 없이 **가상 자금**으로 전략·엔진만 테스트할 때 사용.

```powershell
python main.py trade
# 또는
python main.py backtest
```

---

### 3.2 rest (키움 REST API)

**목적:** 모의투자/실전 서버용 REST API로 조회·주문 (OAuth2, 24시간 토큰).

#### 필요 사항

1. **키움 REST API 발급**  
   - 키움증권에서 REST API APPKEY·SECRETKEY 발급 (모의/실전 구분).
2. **계좌번호**  
   - 사용할 키움 계좌 하나.
3. **base_url**  
   - 모의: `https://mockapi.kiwoom.com`  
   - 실전: `https://api.kiwoom.com`

#### 설정 방법

**방법 A: config.yaml**

`quant-trader/config.yaml` 예시:

```yaml
broker_mode: rest

kiwoom:
  appkey: "발급받은_APPKEY"
  secretkey: "발급받은_SECRETKEY"
  base_url: "https://mockapi.kiwoom.com"   # 모의
  # base_url: "https://api.kiwoom.com"     # 실전

account:
  account_no: "사용할_계좌번호"
  initial_cash: 10_000_000   # rest 모드에서는 참고용
```

**방법 B: 환경 변수 (권장)**

config.yaml의 `appkey`/`secretkey`/`account_no`는 비워 두고, 환경 변수로만 넣어도 됩니다.

```powershell
$env:KIWOOM_APPKEY = "발급받은_APPKEY"
$env:KIWOOM_SECRETKEY = "발급받은_SECRETKEY"
$env:KIWOOM_ACCOUNT = "사용할_계좌번호"
python main.py trade
```

또는 한 줄로:

```powershell
$env:KIWOOM_APPKEY="xxx"; $env:KIWOOM_SECRETKEY="yyy"; $env:KIWOOM_ACCOUNT="12345678"; python main.py trade
```

#### 실행 순서 (로컬)

1. `quant-trader`로 이동 후 가상환경 활성화 및 `pip install -r requirements.txt`
2. config.yaml에 `broker_mode: rest` 및 `base_url` (모의/실전) 설정
3. APPKEY, SECRETKEY, 계좌번호를 config 또는 환경 변수로 설정
4. `python main.py trade` 실행  
   → 엔진이 `config.yaml`의 `engine.interval_sec`(기본 60초)마다 전략 신호를 확인하고, REST API로 주문/조회

#### 참고

- REST 브로커는 **실제 TR URL/필드명**이 키움 가이드와 다를 수 있음.  
  `broker.py`의 `KiwoomRestBroker` 내 `_tr_request` URL·응답 파싱은 키움 REST API 최신 명세에 맞게 수정할 수 있음.

---

### 3.3 openapi (키움 OpenAPI+ COM, Windows 전용)

**목적:** Windows 로컬에서 키움 HTS와 COM으로 연결해 **실제 주문/체결**을 사용할 때.

#### 필요 사항

1. **Windows PC**
2. **키움 HTS (영웅문 등)** 설치  
   - OpenAPI+ 사용 가능한 버전인지 키움 안내 확인
3. **OpenAPI+** 설치 및 활성화  
   - HTS에서 OpenAPI+ 사용 설정
4. **Python: pywin32**  
   - COM 호출용

```powershell
pip install pywin32
```

5. **계좌번호**  
   - config.yaml 또는 환경 변수 `KIWOOM_ACCOUNT`

#### config.yaml 예시

```yaml
broker_mode: openapi

account:
  account_no: "사용할_계좌번호"
  initial_cash: 10_000_000
```

환경 변수 사용 시:

```powershell
$env:KIWOOM_ACCOUNT = "12345678"
python main.py trade
```

#### 실행 순서 (로컬)

1. **키움 HTS 실행 후 로그인**
2. OpenAPI+ 설정이 켜져 있는지 확인
3. `quant-trader`에서 가상환경 활성화, `pip install -r requirements.txt`, `pip install pywin32`
4. config.yaml에 `broker_mode: openapi`, `account.account_no` (또는 `KIWOOM_ACCOUNT`) 설정
5. `python main.py trade` 실행  
   → `KiwoomOpenApiBroker.connect()` 가 COM으로 HTS에 연결 요청  
   → 로그인 창이 뜨면 본인 계정으로 로그인

#### 주의

- 현재 `KiwoomOpenApiBroker`는 **get_price, get_ohlcv, get_balance, get_positions** 등이 `NotImplementedError`로 되어 있음.  
  COM 이벤트(OnReceiveTrData 등)를 붙여서 TR 조회를 구현해야 실전처럼 동작함.
- **place_order / cancel_order** 는 구현되어 있어, 전략이 신호를 내면 주문은 나갈 수 있음.

---

## 4. 전체 흐름 요약 (로컬)

1. **quant-trader** 디렉터리로 이동
2. **Python 가상환경** 생성·활성화 후 `pip install -r requirements.txt`
3. **rest** 사용 시: `pip install` 만으로 충분 (requests는 이미 requirements.txt에 있음)
4. **openapi** 사용 시: `pip install pywin32` 추가, HTS 실행·로그인
5. **config.yaml**에서 `broker_mode` 선택 (mock / rest / openapi)
6. **rest**면 APPKEY·SECRETKEY·계좌번호, **openapi**면 계좌번호만 설정 (config 또는 환경 변수)
7. 터미널에서 **`python main.py trade`** 실행  
   → 엔진이 장 시간(engine.market_open ~ market_close)에만 `interval_sec`마다 전략 실행·주문

---

## 5. 트러블슈팅

| 현상 | 확인 사항 |
|------|-----------|
| `ModuleNotFoundError: No module named 'core'` | 반드시 **quant-trader** 디렉터리에서 실행 (`python main.py trade`). 상위에서 실행 시 `python quant-trader/main.py trade` 등으로 경로 조정 |
| REST: `Hash computation failed` / 401 | APPKEY·SECRETKEY·base_url(모의/실전) 확인. 토큰 발급 실패 시 키움 개발자 센터·계정 상태 확인 |
| REST: TR 조회 실패 | broker.py 내 해당 TR의 URL·요청 body·응답 파싱이 키움 REST API 명세와 일치하는지 확인 |
| OpenAPI: `pywin32 가 설치되지 않았습니다` | `pip install pywin32` |
| OpenAPI: COM 연결 실패 | HTS 실행 중인지, OpenAPI+ 사용 가능 버전인지, 키움 안내에 따른 COM 등록 여부 확인 |
| OpenAPI: get_price 등 NotImplementedError | COM 이벤트 핸들러(OnReceiveTrData 등) 구현 필요. 현재는 주문만 가능한 상태 |

이 문서는 로컬에서 키움 API 기반 매매 프로그램을 실행하기 위한 **필요 조건과 과정**을 정리한 것입니다. 실제 키움 API·OpenAPI+ 사용 방법은 키움증권 제공 문서를 따르세요.
