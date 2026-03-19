# quant-trader 테스트

## 설치

```bash
cd quant-trader
pip install -r requirements-test.txt
```

## 실행

**quant-trader 프로젝트 루트에서** 실행 (상대 경로/import가 `core.*` 기준).

```bash
cd quant-trader
pytest tests/ -v
```

커버리지 포함:

```bash
pytest tests/ -v --cov=core --cov-report=term-missing
```

## 구성

- `conftest.py` – MockBroker, sample OHLCV, Portfolio 픽스처
- `test_broker.py` – MockBroker 단위 테스트, KiwoomRestBroker(requests 모킹), create_broker
- `test_portfolio.py` – Portfolio sync/record, summary, position_weight

## 시행착오 정리

테스트 구성 중 겪은 문제와 해결 방법은 **[TESTING_NOTES.md](./TESTING_NOTES.md)** 에 정리되어 있습니다. (OverflowError, import 경로, mock 패치 경로, OpenAPI 스킵, 한글 경로 등)
