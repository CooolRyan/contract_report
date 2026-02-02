# On-chain Proof-of-Performance for Kiwoom Trading

국내 주식 계좌(키움) 매매 내역 기반으로 트레이딩 성과(PnL, MDD, Sharpe)를 계산하고, 요약 해시를 블록체인에 커밋해 검증 가능하게 하는 PoC 프로젝트입니다.

## 아키텍처 요약

| 컴포넌트 | 기술 | 역할 |
|----------|------|------|
| **Kiwoom 에이전트** | Python | 키움 OpenAPI+로 거래 내역 조회 → PostgreSQL 저장 (최소 코드) |
| **백엔드** | Spring Boot (Java 17) | PostgreSQL 조회, 성과 계산, 해시 생성, 온체인 커밋 호출 |
| **스마트 컨트랙트** | Solidity (Foundry) | `commitPerformance` / `getPerformance` / 이벤트 |
| **웹 UI** | Vercel v0 등 | 화면은 Vercel v0로 생성 예정. (뼈대: Next.js + wagmi) |

원본 매매 데이터는 로컬에만 존재하며, 온체인에는 **요약 JSON의 SHA-256 해시**만 기록됩니다.

## 디렉터리 구조

```
contract_report/
├── docs/SYSTEM_DESIGN.md   # 상세 설계서 (컴포넌트/시퀀스 다이어그램)
├── kiwoom-agent/           # Python: 키움 연동 → PostgreSQL
├── backend/                # Spring Boot: PostgreSQL, 성과 계산·해시·블록체인
├── contracts/              # Solidity + Foundry
└── web-ui/                 # Next.js (지갑 연결, 성과 조회)
```

## 빠른 시작

### 0. PostgreSQL

- DB 생성: `createdb performance` (또는 원하는 DB명)
- `backend/src/main/resources/application.yml` 또는 환경변수로 `spring.datasource.url`, `username`, `password` 설정.
- 최초 테이블 생성: `backend/src/main/resources/schema.sql` 내용을 DB에 실행 (또는 Kiwoom 에이전트 실행 시 자동 생성).

### 1. Kiwoom 에이전트 (Python)

- Windows + 키움 OpenAPI+ 설치 필요.
- `kiwoom-agent/`에서 `pip install -r requirements.txt` 후, 실제 키움 API 연동은 `fetch_trades.py` 내 `fetch_trades_from_kiwoom()` 구현.
- Spring과 동일 DB 사용: `--db-url postgresql://user:pass@localhost:5432/performance` 또는 환경변수 `DB_URL`.

```bash
cd kiwoom-agent
pip install -r requirements.txt
python fetch_trades.py --account YOUR_ACCOUNT --start 2025-01-01 --end 2025-01-31
# 또는: python fetch_trades.py ... --db-url "postgresql://postgres:postgres@localhost:5432/performance"
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
  - `GET /api/performance/summary?accountId=...&start=...&end=...` — 성과 요약 + 해시
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

### 4. 웹 UI (Vercel v0 / Next.js)

- **화면은 Vercel v0로 뽑을 예정.** `web-ui/`는 API 연동·지갑 연결용 뼈대만 두었음.
- v0로 UI 구성 후, 백엔드 API·컨트랙트 주소만 연결하면 됨.

```bash
cd web-ui
npm install
npm run dev
```

- `.env.local` 예시: `NEXT_PUBLIC_REGISTRY_ADDRESS=0x...` (배포된 PerformanceRegistry 주소)

## 백엔드 구조 (Python vs Spring)

- **키움 연동만 Python**: OpenAPI+가 Windows COM 기반이라 Python(pywin32/KOAPY) 생태계가 검증되어 있어, **최소한의 Python 스크립트**로 거래 내역만 조회·SQLite 저장합니다.
- **나머지 비즈니스 로직은 Spring**: 성과 계산, 해시, 블록체인 호출, REST API를 Java/Spring으로 구현해 두었습니다. Spring에 익숙하다면 이 부분만 유지·확장하면 됩니다.
- 데이터 경계: Python은 **INSERT만**, Spring은 **SELECT + 계산 + 온체인**. 원본 매매 데이터는 로컬 DB에서만 사용됩니다.

## 데이터 스키마

- **DB**: PostgreSQL.
- **trades**: `id`, `account_id`, `trade_date`, `symbol`, `side`, `qty`, `price`, `fee`, `order_id`, `exec_id`, `strategy_tag`
- **PerformanceSummary** (JSON → 해시): `account_id`, `strategy_tag`, `period_start`, `period_end`, `total_pnl`, `max_drawdown`, `sharpe_ratio`, `equity_curve_sampled`

## 라이선스 / 비고

- PoC용이며, 개인정보·키 관리 등 운영 환경에 맞게 보안 설정을 추가해야 합니다.
- 체인: Sepolia 또는 Polygon Amoy 등 테스트넷 사용을 권장합니다.
