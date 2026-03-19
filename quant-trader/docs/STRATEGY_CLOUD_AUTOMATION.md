# 전략 자동 증명 + 클라우드 자동화

## 목표

1. **체결 시** `quant-trader`가 Spring `POST /api/kiwoom/register`로 `trades`에 넣고, `strategyTag`로 전략을 구분한다.
2. **장 마감 후(또는 일정)** `python main.py commit`으로 `POST /api/performance/commit`을 호출해 해시를 온체인에 남긴다.

## 로컬 설정

1. `config.yaml`에서 `contract_report.enabled: true`
2. `api_base_url`, `user_id`(지갑 주소 등), `account.account_no`(키움 계좌) 설정
3. 또는 환경변수:
   - `CONTRACT_REPORT_API_URL`
   - `CONTRACT_REPORT_USER_ID`
   - `KIWOOM_ACCOUNT`
   - `CONTRACT_REPORT_ENABLED=true` (체결 동기화 켤 때)

## 명령어

```bash
# 실전 루프 (체결마다 백엔드 등록)
python main.py trade

# 특정 일자 성과 온체인 커밋 (백엔드가 트랜잭션 전송)
python main.py commit --date 2026-02-02
python main.py commit --start 2026-02-01T00:00:00 --end 2026-02-02T23:59:59
python main.py commit --date 2026-02-02 --strategy-tag moving_average_cross
```

`commit`은 `contract_report.enabled`가 꺼져 있어도, URL/USER/계좌만 있으면 동작하도록 `enabled`를 일시적으로 켠다.

## Kubernetes

- **Deployment**: `deploy/k8s-quant-trader-deployment.yaml` — 백엔드와 동일 네임스페이스면 `CONTRACT_REPORT_API_URL=http://contract-report-backend:8080`
- **CronJob**(선택): 장 마감 후 `main.py commit --date ...` 실행. 클러스터 타임존은 UTC가 많으니 스케줄 조정(예: KST 16:10 → UTC 07:10).
- **시크릿**: 키움 키·DB는 백엔드와 동일하게 쓰지 않고, quant Pod에는 `KIWOOM_APPKEY`, `KIWOOM_SECRETKEY`, `KIWOOM_ACCOUNT`만 주면 된다.

## CI/CD

`.github/workflows/cd.yml`에 `contract-report-quant-trader` 이미지 빌드/푸시가 포함되면, ArgoCD 매니페스트의 이미지 태그가 `sha-<commit>`으로 갱신된다.

## 주의

- **키움 REST 주문/체결**은 증권사·API 정책에 따른다. 클라우드에서 “실주문”을 돌리기 전에 모의투자·리스크 검토를 권장한다.
- 백엔드 `TZ=Asia/Seoul`과 commit 시각이 맞아야 기간 조회가 기대와 일치한다.
