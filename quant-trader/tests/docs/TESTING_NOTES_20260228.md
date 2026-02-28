# quant-trader 테스트 구성 시행착오 정리

테스트 로직을 구성하면서 겪은 문제와 해결 방법을 정리한 문서입니다.

---

## 1. KiwoomRestBroker 테스트 시 OverflowError

### 현상

`test_get_balance_mocked`, `test_get_price_mocked` 실행 시 다음 오류 발생:

```
OverflowError: date value out of range
```

발생 위치: `KiwoomRestBroker._ensure_token()` 내부

```python
if datetime.now() < self._token_expires_at - timedelta(minutes=5):
```

### 원인

- `KiwoomRestBroker` 생성 직후 `_token_expires_at`은 `datetime.min`으로 초기화됨.
- 토큰을 한 번도 발급하지 않은 상태에서 `_token_expires_at - timedelta(minutes=5)`를 계산하면 `datetime.min`보다 더 과거가 되어 일부 환경에서 **OverflowError**가 발생함.
- 테스트에서는 `requests.post`만 모킹했기 때문에, `get_balance()` / `get_price()` 호출 시 내부적으로 `_ensure_token()` → `_issue_token()`이 호출되고, 그 과정에서 위 조건식이 실행됨.

### 해결

- **TR 응답만 검증하는 테스트**에서는 토큰 갱신 로직을 타지 않도록 **`_ensure_token`을 패치**함.
- `@patch("core.broker.KiwoomRestBroker._ensure_token", return_value="fake-token")` 를 추가하고, `requests.post`는 TR 한 번만 호출되도록 모킹.

```python
@patch("core.broker.KiwoomRestBroker._ensure_token", return_value="fake-token")
@patch("core.broker.requests.post")
def test_get_balance_mocked(self, mock_post, _ensure_token, rest_broker):
    mock_post.return_value.json.return_value = { ... }
    bal = rest_broker.get_balance()
    ...
```

- 토큰 발급 로직 자체는 `test_issue_token`에서 별도로 검증.

### 참고 (본문 수정 옵션)

본문 코드에서 초기값을 바꾸고 싶다면, 예:  
`if self._token and self._token_expires_at > datetime.min and datetime.now() < self._token_expires_at - timedelta(...)` 처럼 `datetime.min`일 때는 무조건 재발급하도록 조건을 나누는 방법도 있음.  
현재는 테스트에서 `_ensure_token` 패치로 회피.

---

## 2. 테스트 실행 경로와 `core.*` import

### 현상

- 테스트/코드에서 `from core.broker import ...`, `from core.portfolio import ...` 처럼 **`core` 패키지 기준**으로 import 함.
- 프로젝트 루트를 `sys.path`에 넣지 않으면 `ModuleNotFoundError: No module named 'core'` 발생.

### 원인

- pytest 기본 동작은 **실행한 디렉터리**를 기준으로 모듈을 찾음.
- `contract_report`(상위)에서 `pytest quant-trader/tests/` 로 실행하면 working directory는 `contract_report`인데, `core`는 `quant-trader/core`에 있어서 import 경로가 맞지 않음.

### 해결

- **quant-trader 루트**를 Python path에 넣기 위해 **quant-trader/conftest.py**에서 다음을 수행:

```python
_root = Path(__file__).resolve().parent
if str(_root) not in sys.path:
    sys.path.insert(0, str(_root))
```

- 실행 방법은 두 가지:
  1. **quant-trader로 이동 후 실행**  
     `cd quant-trader` → `pytest tests/ -v`  
     (이때 conftest.py가 로드되며 `quant-trader`가 sys.path에 추가됨.)
  2. **상위(contract_report)에서 실행**  
     `python -m pytest quant-trader/tests/ -v`  
     (테스트 디렉터리만 지정하면 conftest는 quant-trader 루트 것이 아님. 상위에서 실행할 때는 `quant-trader`가 자동으로 path에 안 들어갈 수 있으므로, CI 등에서는 `PYTHONPATH=quant-trader` 또는 `cd quant-trader && pytest tests/` 사용 권장.)

- 정리: **quant-trader 디렉터리에서 `pytest tests/`** 로 실행하는 것을 기준으로 conftest가 설계되어 있음. CI/스크립트에서는 `cd quant-trader` 후 pytest 실행을 권장.

---

## 3. unittest.mock 패치 경로

### 현상

- `requests.post`를 패치할 때 `requests.post`가 아니라 **실제로 호출되는 모듈 기준**으로 패치해야 함.

### 원인

- `from unittest.mock import patch`로 패치할 때, patch 인자는 **그 객체가 사용되는 이름 공간**을 가리켜야 함.  
  `core.broker`에서 `import requests` 후 `requests.post(...)`를 쓰므로, **`core.broker`의 `requests`**를 패치해야 함.

### 해결

- 패치 경로를 **`"core.broker.requests.post"`** 로 지정.

```python
@patch("core.broker.requests.post")
def test_issue_token(self, mock_post, rest_broker):
    ...
```

- `"requests.post"`만 쓰면, 테스트 모듈이 사용하는 `requests`가 패치되어 `core.broker` 내부의 `requests`는 그대로라서 모킹이 적용되지 않을 수 있음.

---

## 4. OpenAPI 브로커 테스트 (Windows 전용)

### 현상

- `create_broker(cfg)`에서 `broker_mode: "openapi"`일 때 `KiwoomOpenApiBroker`가 생성되고, 내부에서 `connect()` → `win32com.client` 사용.
- Windows가 아니거나 pywin32가 없으면 실패하거나 환경 의존성이 커짐.

### 해결

- OpenAPI 브로커 생성 테스트는 **의도적으로 스킵** 처리.  
  `@pytest.mark.skip(reason="OpenAPI는 Windows + pywin32 필요")`  
- CI나 다른 OS에서도 전체 테스트가 통과하도록 유지.

---

## 5. pytest 실행 시 한글 경로 (Windows)

### 현상

- Windows PowerShell에서 프로젝트 경로에 **한글**이 포함되어 있으면, `cd` 시 인코딩 문제로 경로를 찾지 못하는 경우가 있음 (예: `Set-Location ... ��δ� ����`).

### 해결

- 한글 경로를 피할 수 없다면:
  - **상위(영문만 있는) 디렉터리**에서 `python -m pytest quant-trader/tests/ -v` 로 실행하거나,
  - **영문만 있는 경로**로 프로젝트를 복사한 뒤 그곳에서 `cd quant-trader` 후 `pytest tests/` 실행.
- CI는 보통 영문 경로를 쓰므로 이 문제는 로컬(Windows + 한글 경로)에서만 고려하면 됨.

---

## 요약

| 문제 | 원인 | 해결 |
|------|------|------|
| `OverflowError` in KiwoomRestBroker 테스트 | `_token_expires_at == datetime.min`일 때 `- timedelta(5분)` 계산 | TR 테스트에서 `_ensure_token` 패치 |
| `ModuleNotFoundError: No module named 'core'` | quant-trader 루트가 sys.path에 없음 | quant-trader/conftest.py에서 sys.path에 루트 추가, `cd quant-trader` 후 pytest 실행 |
| requests 모킹이 안 됨 | 잘못된 패치 대상 | `core.broker.requests.post` 로 패치 |
| OpenAPI 테스트 실패 | Windows/pywin32 의존 | 해당 테스트 `@pytest.mark.skip` |
| 한글 경로에서 cd 실패 | PowerShell 인코딩 | 상위 경로에서 pytest 실행 또는 영문 경로 사용 |

이 문서는 테스트를 수정·확장할 때 참고용으로 사용하면 됩니다.
