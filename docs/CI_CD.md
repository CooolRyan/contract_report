# CI/CD 파이프라인

GitHub Actions 기준으로 CI/CD 워크플로가 정의되어 있습니다.

## 브랜치 플로우

- **dev**: 개발·피처 작업. 여기서 작업 완료 후 CI(빌드·테스트)만 실행.
- **ci/cd**: 배포용 브랜치. dev에서 머지(또는 push)하면 **CD가 실행되어 배포**됨.
- **main**: 기본 브랜치. ci/cd에서 배포·검증이 끝난 뒤 **최종 반영용으로 머지** (main 자체에서는 배포 트리거 없음).

**권장 순서**: dev에서 작업 → PR/머지로 **ci/cd**에 반영 → CD로 배포 → 확인 후 **main**에 머지.

---

## CI (`.github/workflows/ci.yml`)

- **트리거**: `main`, `dev`, `ci/cd` 브랜치 push / pull_request
- **작업**:
  - **Backend**: Ubuntu + JDK 17, PostgreSQL 16 서비스 컨테이너로 Spring Boot 빌드·테스트 (`gradle build -x bootJar`)
  - **Frontend**: Node 20 + pnpm, `new-web-ui` 의존성 설치 → lint → build
  - **Kiwoom Agent**: Python 3.11, 의존성 설치 후 `fetch_trades.py` 문법 검사
  - **Contracts**: Foundry 설치 후 `forge build`, `forge test` (forge-std는 `forge install`로 설치 시도)

### Backend 테스트 DB

CI에서는 PostgreSQL 서비스 컨테이너를 띄우고, 다음 환경 변수로 연결합니다.

- `SPRING_DATASOURCE_URL=jdbc:postgresql://localhost:5432/performance_test`
- `SPRING_DATASOURCE_USERNAME=postgres`
- `SPRING_DATASOURCE_PASSWORD=postgres`

로컬에서 동일하게 테스트하려면 `performance_test` DB를 만들고 위 설정을 사용하면 됩니다.

### Contracts (Foundry)

`contracts/`에 `forge-std`가 없으면 CI에서 `forge install foundry-rs/forge-std --no-commit`을 실행합니다. 로컬에서 한 번 실행해 두면 `lib/forge-std`가 생기고, 필요 시 해당 디렉터리를 커밋하거나 submodule로 관리할 수 있습니다.

---

## CD (`.github/workflows/cd.yml`)

- **트리거**: **`ci/cd` 브랜치 push** 또는 수동 실행 (`workflow_dispatch`) 시에만 배포
- **작업**:
  - **Build & Publish**: Backend `bootJar` 빌드 후 JAR 아티팩트 업로드
  - **Deploy Backend**: 아티팩트 다운로드 후 배포 단계(플레이스홀더). `DEPLOY_HOST`, `DEPLOY_SSH_KEY` 등 시크릿 설정 후 실제 배포 스크립트 추가
  - **Deploy Frontend (nginx)**: Next.js **정적 내보내기**(`output: 'export'`) 빌드 → `out/` 아티팩트 업로드 → nginx 서버로 rsync/scp 배포(플레이스홀더). `DEPLOY_WEB_HOST`, `DEPLOY_WEB_USER`, `DEPLOY_SSH_KEY` 등 설정 후 배포 단계 주석 해제

### 웹 서버 (nginx)

- 프론트엔드는 **정적 빌드**(`new-web-ui/out/`)를 nginx로 서빙하는 구조.
- 예시 설정: **`deploy/nginx.conf.example`** — root를 `out/`이 복사된 경로(예: `/var/www/performance-registry`)로 두고, `/api/`는 백엔드(예: `127.0.0.1:8080`)로 프록시.

### 배포 활성화 방법

1. **Backend**: `deploy-backend` job에서 주석 처리된 Deploy 단계를 열고, `DEPLOY_HOST`, `DEPLOY_SSH_KEY` 등을 Secrets에 등록.
2. **Frontend (nginx)**: `deploy-frontend` job에서 "Deploy to nginx server" 단계 주석 해제 후, `DEPLOY_WEB_HOST`, `DEPLOY_WEB_USER`, `DEPLOY_SSH_KEY`, (선택) `DEPLOY_WEB_PATH`(vars) 설정. 서버에는 `deploy/nginx.conf.example` 참고해 nginx 설정 후 `root`를 해당 경로로 두면 됨.
3. **Environment**: GitHub 리포지토리에서 `Settings` → `Environments` → `production` 생성 후 필요 시 보호 규칙 설정.
