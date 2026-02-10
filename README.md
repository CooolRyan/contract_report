# On-chain Proof-of-Performance for Kiwoom Trading

**용도**: 사용자들이 **자기 수익을 인증**하고, **조언·전략을 공유할 때** 그 말이 허위가 아닌지 **검증할 수단**을 제공. 이걸 바탕으로 **커뮤니티**를 형성하고, 그 내용을 **원장성 DB + 블록체인**에 기록한다.

국내 주식 계좌(키움) 매매 내역 기반으로 트레이딩 성과(PnL, MDD, Sharpe)를 계산하고, 요약 해시를 블록체인에 커밋해 **사후 검증 가능**하게 하는 PoC 프로젝트입니다.

## 아키텍처 요약

| 컴포넌트 | 기술 | 역할 |
|----------|------|------|
| **키움 연동** | **서비스**: 키움 REST API (Spring에서 호출) / **로컬**: Python(Open API+ COM) | 거래 내역 조회 → PostgreSQL 저장 |
| **백엔드** | Spring Boot (Java 17) | PostgreSQL 조회, 성과 계산, 해시 생성, 온체인 커밋 호출 |
| **스마트 컨트랙트** | Solidity (Foundry) | `commitPerformance` / `getPerformance` / 이벤트 |
| **웹 UI** | Next.js + wagmi (v0 UI) | 대시보드, 지갑 연결, 백엔드 API 연동 |

원본 매매 데이터는 로컬에만 존재하며, 온체인에는 **요약 JSON의 SHA-256 해시**만 기록됩니다.

## 디렉터리 구조

```
contract_report/
├── docs/SYSTEM_DESIGN.md   # 상세 설계서 (컴포넌트/시퀀스 다이어그램)
├── kiwoom-agent/           # Python: 키움 연동 → PostgreSQL
├── backend/                # Spring Boot: PostgreSQL, 성과 계산·해시·블록체인
├── contracts/              # Solidity + Foundry
└── new-web-ui/             # Next.js + wagmi (v0 UI, 백엔드 API 연동)
```

## 빠른 시작

### 0. PostgreSQL

- DB 생성: `createdb performance` (또는 원하는 DB명)
- `backend/src/main/resources/application.yml` 또는 환경변수로 `spring.datasource.url`, `username`, `password` 설정.
- 최초 테이블 생성: `backend/src/main/resources/schema.sql` 내용을 DB에 실행 (또는 Kiwoom 에이전트 실행 시 자동 생성).

### 1. 키움 거래 내역 수집

- **서비스 운영 시**: 로컬 HTS 설치 없이 **키움 REST API** 사용. Spring 백엔드에서 OAuth2 토큰 발급 후 `https://api.kiwoom.com` 호출 → 체결/계좌 TR로 데이터 수집 후 DB 저장. 상세는 **`docs/KIWOOM_REST_API.md`** 참고.
- **로컬 전용 시**: Windows + 키움 Open API+(HTS) 설치 후 **kiwoom-agent**(Python) 사용. `pip install -r requirements-windows.txt` (Windows), `requirements.txt` (리눅스/CI). `--db-url` 또는 환경변수 `DB_URL`로 Spring과 동일 DB 지정.

```bash
# 로컬 전용 (Windows)
cd kiwoom-agent
pip install -r requirements-windows.txt
python fetch_trades.py --account YOUR_ACCOUNT --start 2025-01-01 --end 2025-01-31
```

### 2. Spring Backend

- Java 17+, Gradle. **PostgreSQL** 실행 중이어야 함.

```bash
cd backend
./gradlew bootRun
```

- 설정: `application.yml` 또는 환경변수
  - `spring.datasource.url`, `username`, `password`: PostgreSQL 연결
  - `blockchain.rpc-url`, `blockchain.contract-address`, `blockchain.private-key` (PoC 시에만 사용)

- API 예시
  - `GET /api/trades?accountId=...&start=...&end=...` — 거래 내역
  - `GET /api/performance/summary?accountId=...&start=...&end=...` — 성과 요약 + 해시 (winRate, tradeCount, verified 포함)
  - `GET /api/performance/commits?accountId=&limit=50` — 커밋 목록 (백엔드 원장 기준)
  - `POST /api/performance/commit` — 성과 계산 후 온체인 커밋 (Body: accountId, start, end, strategyTag)

### 3. 스마트 컨트랙트 (Foundry)

- [Foundry](https://book.getfoundry.sh/getting-started/installation) 설치 후:

```bash
cd contracts
forge install foundry-rs/forge-std --no-commit   # 최초 1회
forge build
forge test
```

- 배포 (Sepolia 예):

```bash
export PRIVATE_KEY=...
export SEPOLIA_RPC_URL=https://rpc.sepolia.org
forge script script/Deploy.s.sol --rpc-url $SEPOLIA_RPC_URL --broadcast
```

- 배포된 컨트랙트 주소를 Backend `blockchain.contract-address`와 Web UI `NEXT_PUBLIC_REGISTRY_ADDRESS`에 설정.

### 4. 웹 UI (new-web-ui, Next.js + wagmi)

- **new-web-ui**: v0로 만든 대시보드 UI + wagmi 지갑 연결 + 백엔드 API 연동.
- 커밋 목록·성과 요약·해시 검증은 백엔드 API 기준으로 동작.
- **CI/CD**: `package.json` 수정 후 로컬에서 `pnpm install` 실행하고 `pnpm-lock.yaml`을 커밋하면, 워크플로에서 `--frozen-lockfile` 사용 가능 (현재는 lockfile 미동기 시 통과하도록 `--no-frozen-lockfile` 사용).

```bash
cd new-web-ui
pnpm install   # 또는 npm install
pnpm dev
```

- `.env.local` 예시:
  - `NEXT_PUBLIC_API_URL=http://localhost:8080` (백엔드 주소)
  - (선택) `NEXT_PUBLIC_REGISTRY_ADDRESS=0x...` (배포된 PerformanceRegistry 주소)

## 백엔드 구조

- **서비스 운영**: **키움 REST API**를 Spring에서 호출 (OAuth2 + 체결/계좌 TR) → DB 저장 → 성과 계산·해시·온체인. 사용자 PC에 HTS 설치 불필요. `docs/KIWOOM_REST_API.md` 참고.
- **로컬 전용**: 키움 **Open API+**(COM)는 Windows 전용이라 Python(pywin32/KOAPY)으로 거래 내역만 조회·PostgreSQL 저장. Spring은 DB 조회·성과 계산·해시·블록체인 호출.
- 데이터 경계: (REST API 사용 시) Spring이 키움 → DB 직접 적재. (Open API+ 사용 시) Python은 INSERT만, Spring은 SELECT + 계산 + 온체인.

## 데이터 스키마

- **DB**: PostgreSQL.
- **trades**: `id`, `account_id`, `trade_date`, `symbol`, `side`, `qty`, `price`, `fee`, `order_id`, `exec_id`, `strategy_tag`
- **PerformanceSummary** (JSON → 해시): `account_id`, `strategy_tag`, `period_start`, `period_end`, `total_pnl`, `max_drawdown`, `sharpe_ratio`, `equity_curve_sampled`

## 라이선스 / 비고

- PoC용이며, 개인정보·키 관리 등 운영 환경에 맞게 보안 설정을 추가해야 합니다.
- 체인: Sepolia 또는 Polygon Amoy 등 테스트넷 사용을 권장합니다.
