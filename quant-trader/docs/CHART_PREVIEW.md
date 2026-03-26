# 캔들 차트 미리보기

## GUI: 3슬롯 + 후보 리스트 (`tools/chart_gui.py`)

- **왼쪽**: 캔들 차트 **3개** (전략별 의미가 다른 슬롯 — `chart_common.three_slots_for_strategy` 참고).
  - **momentum**: 순위 1~3 (`mom_R1` …)
  - **moving_average_cross**: 매수 쪽 / 매도 쪽 / 관찰
  - **rsi_mean_reversion**: RSI 매수·매도·관찰
- **아래 라디오**: «어느 슬롯을 바꿀지» 선택.
- **오른쪽 리스트**: 조건에 맞는 후보 종목 (`scan`과 동일 필터). **종목 클릭** → 선택된 슬롯 차트만 해당 종목으로 갱신.
- **Redraw all slots**: 현재 슬롯 종목으로 3칸 다시 그림.

```bash
cd quant-trader
python tools/chart_gui.py --mock
```

## 웹: 브라우저 실시간 뷰 (`tools/chart_web.py`)

- **Plotly** 캔들 + 거래량 (+ 이동평균 옵션). 줌·팬·범례 클릭 등 인터랙션.
- 사이드바: **자동 새로고침(초)** — `streamlit-autorefresh` 설치 시 N초마다 데이터 재조회.
- 레이아웃 **스캔 전체**: 후보 종목을 세로로 나열 (최대 N개).
- 레이아웃 **3슬롯**: `chart_gui.py`와 동일한 전략 슬롯 + 종목 선택으로 슬롯 교체.

```bash
cd quant-trader
pip install -r requirements.txt
streamlit run tools/chart_web.py
```

브라우저에서 기본 **http://localhost:8501** — 키움은 `.env` + `config.yaml` 그대로 사용 (`Mock` 체크 시 샘플 데이터).

## CLI: PNG / 단일 창 (`tools/chart_preview.py`)

테스트·검증용으로 **OHLCV 캔들 + 거래량**을 PNG로 저장하거나, `--show` 로 matplotlib 창에 띄웁니다.

## 설치

```bash
cd quant-trader
pip install -r requirements.txt
```

## 어떤 차트인가?

- **캔들스틱(일봉 등) + 거래량** 막대. (종목 이름 검색 UI는 없음 — **종목코드 6자리** 기준.)
- **어떤 종목을 그릴지**
  - **`--mode scan` (기본)**: `config.yaml`의 **전략·유니버스**로 `generate_signals()`를 한 번 돌려,
    - **신호가 난 종목**을 우선 표시.
    - 신호가 없고 전략이 **`momentum`** 이면 **모멘텀 상위 N종목**을 표시 (랭킹 기준).
    - 그래도 없으면 **`--no-fallback-universe` 를 주지 않는 한** 유니버스 전체를 표시.
  - **`--mode symbol --symbol 005930`**: 지정한 종목만 (쉼표로 여러 개 가능).

> 키움 REST `get_ohlcv`는 레포 기준 **일/주/월봉 TR** 위주입니다. **분봉**은 API·브로커 구현을 붙인 뒤 `--period` 등을 확장하면 됩니다.

## 예시

```bash
# API 없이 샘플 데이터 + scan (전략 조건 우선)
python tools/chart_preview.py --mock --mode scan --output-dir chart_out

# 종목 직접 지정
python tools/chart_preview.py --mock --mode symbol --symbol 005930,000660

# 이동평균 크로스 전략일 때 MA(단기/장기) 오버레이
python tools/chart_preview.py --mock --mav

# 창으로 표시 (저장 안 함)
python tools/chart_preview.py --mock --symbol 005930 --show
```

실계좌/REST 사용 시 `config.yaml` + `.env` 에 키·계좌를 넣고 `--mock` 을 빼면 됩니다.

## 출력

- 기본: `--output-dir` (기본 `chart_out/`) 아래 `chart_{종목코드}_{period}.png`
- 차트 안 제목은 **ASCII**만 사용(한글은 터미널 로그에 출력) — matplotlib 기본 폰트 한글 깨짐 방지.
