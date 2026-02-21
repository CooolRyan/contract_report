# 시크릿 목록 (직접 생성, Git에 올리지 않음)

백엔드가 참조하는 시크릿들입니다. **contract** 네임스페이스에 아래 이름·키대로 만들면 됩니다. 값은 로컬에서만 넣고 리포에는 올리지 마세요.

---

## 1. contract-report-db

PostgreSQL 접속용.

| 키 | 설명 |
|----|------|
| `url` | `jdbc:postgresql://호스트:5432/performance` |
| `username` | DB 사용자명 |
| `password` | DB 비밀번호 |

```bash
kubectl create secret generic contract-report-db -n contract \
  --from-literal=url='jdbc:postgresql://YOUR_HOST:5432/performance' \
  --from-literal=username=postgres \
  --from-literal=password=YOUR_PASSWORD
```

---

## 2. contract-report-blockchain

Amoy(또는 사용 중인 체인) RPC, 컨트랙트 주소, 커밋용 지갑 프라이빗 키.

| 키 | 설명 |
|----|------|
| `rpc-url` | RPC URL (예: Amoy 엔드포인트) |
| `contract-address` | 배포한 PerformanceRegistry 컨트랙트 주소 |
| `private-key` | 트랜잭션 전송용 지갑 프라이빗 키 (0x 제외해도 됨) |

```bash
kubectl create secret generic contract-report-blockchain -n contract \
  --from-literal=rpc-url='https://...' \
  --from-literal=contract-address='0x...' \
  --from-literal=private-key='...'
```

---

## 3. contract-report-kiwoom

키움 REST API (서비스용으로 쓸 때만).

| 키 | 설명 |
|----|------|
| `appkey` | 키움 개발자센터 앱키 |
| `secretkey` | 키움 개발자센터 시크릿키 |

```bash
kubectl create secret generic contract-report-kiwoom -n contract \
  --from-literal=appkey='...' \
  --from-literal=secretkey='...'
```

키움 미사용 시 이 시크릿을 안 만들어도 되고, 백엔드는 값이 비어 있으면 API 호출만 스킵합니다.
