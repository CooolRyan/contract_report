# contract-report-db 시크릿 생성

백엔드 Deployment가 DB 접속에 사용하는 시크릿입니다. **contract** 네임스페이스에 한 번 생성해 두세요.

## kubectl로 생성 (권장)

실제 DB 호스트/비밀번호로 치환한 뒤 실행하세요.

```bash
kubectl create namespace contract --dry-run=client -o yaml | kubectl apply -f -

kubectl create secret generic contract-report-db -n contract \
  --from-literal=url='jdbc:postgresql://YOUR_DB_HOST:5432/performance' \
  --from-literal=username=postgres \
  --from-literal=password=YOUR_DB_PASSWORD
```

- `YOUR_DB_HOST`: PostgreSQL 서버 주소 (클러스터 내부면 서비스명, 외부면 IP/도메인)
- `YOUR_DB_PASSWORD`: DB 비밀번호

생성 후 ArgoCD에서 앱을 다시 Sync 하면 백엔드 Pod가 정상 기동됩니다.
