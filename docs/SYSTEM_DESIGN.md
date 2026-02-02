# On-chain Proof-of-Performance for Kiwoom Trading — 시스템 설계서

## 1. 프로젝트 개요

### 문제 정의
국내 주식 계좌(키움)의 실제 매매 내역을 기반으로, 개인 트레이딩 전략의 성과(PnL, MDD, 샤프 등)를 계산하고, 그 요약 결과를 블록체인에 커밋해서 사후에 검증 가능하게 만들고 싶다.

### 목표
- 키움 OpenAPI+로 특정 계좌의 매매 내역을 주기적으로 수집
- 로컬에서 성과 지표 계산
- 계산 결과 요약 JSON과 그 해시를 생성
- EVM 호환 체인(예: 테스트넷)에 해시를 기록하는 스마트 컨트랙트 및 간단 UI

---

## 2. 아키텍처 개요

### 백엔드 분리 전략 (Python vs Spring)

| 담당 | 기술 | 이유 |
|------|------|------|
| **Kiwoom 연동** | Python (KOAPY/COM) | OpenAPI+가 Windows COM 기반이라 Python 생태계(pywin32, KOAPY)가 검증됨. 최소한의 스크립트만 유지. |
| **비즈니스 로직·API** | Spring Boot (Java) | 성과 계산, DB 조회, 해시 생성, 블록체인 호출. Spring에 익숙하다면 이 부분을 Java로 통일. |

**데이터 경계**: Python 에이전트는 **거래 내역만** PostgreSQL에 적재. Spring은 해당 DB를 읽어서 성과 계산·해시·온체인 커밋을 수행. 원본 매매 데이터는 로컬 DB에서만 유통. **DB는 PostgreSQL 사용.**

---

## 3. 컴포넌트 다이어그램 (텍스트)

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                           사용자 PC (Windows)                                │
│  ┌──────────────────────┐    ┌──────────────────────────────────────────┐  │
│  │ Kiwoom OpenAPI+      │    │ Spring Boot Backend                       │  │
│  │ (키움 HTS)           │    │  - REST API (기간/계좌 조회, 성과 계산)   │  │
│  └──────────┬───────────┘    │  - 성과 계산 엔진 (PnL, MDD, Sharpe)      │  │
│             │                 │  - 해시 생성 (SHA-256)                     │  │
│             │                 │  - Web3j (블록체인 트랜잭션)               │  │
│  ┌──────────▼───────────┐    └──────────────────┬───────────────────────┘  │
│  │ Python Kiwoom Agent │                       │                          │  │
│  │ - 계좌/기간 조회     │─────── SQLite ────────►│  SQLite (trades 등)    │  │
│  │ - trades 테이블 저장 │       (로컬 파일)      │                          │  │
│  └─────────────────────┘                       └──────────────────────────┘  │
└─────────────────────────────────────────────────────────────────────────────┘
                                        │
                                        │ RPC (commitPerformance 등)
                                        ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                    EVM 체인 (Sepolia / Amoy 등)                              │
│  ┌─────────────────────────────────────────────────────────────────────┐    │
│  │ PerformanceRegistry.sol                                              │    │
│  │  - commitPerformance(hash, periodStart, periodEnd)                   │    │
│  │  - getPerformance(trader, periodStart, periodEnd)                   │    │
│  │  - event PerformanceCommitted                                       │    │
│  └─────────────────────────────────────────────────────────────────────┘    │
└─────────────────────────────────────────────────────────────────────────────┘
                                        │
                                        │ read (view)
                                        ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                    Web UI (Vercel v0 / Next.js)                              │
│  - 화면은 Vercel v0로 생성 예정. 지갑 연결, 성과 목록 조회 등.               │
│  - (선택) JSON/로그 드롭 → 재계산·해시 비교                                  │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## 4. 시퀀스 다이어그램 (텍스트)

### 4.1 거래 수집 → 성과 계산 → 온체인 커밋

```
User          Kiwoom HTS    Python Agent    PostgreSQL  Spring Backend    Chain
  │                │              │               │             │            │
  │  [매매 발생]   │              │               │             │            │
  │                │              │               │             │            │
  │  주기 실행     │              │               │             │            │
  │───────────────►│              │               │             │            │
  │                │  OpenAPI+   │               │             │            │
  │                │────────────►│               │             │            │
  │                │  거래 내역   │               │             │            │
  │                │◄────────────│               │             │            │
  │                │              │  INSERT       │             │            │
  │                │              │──────────────►│             │            │
  │                │              │               │             │            │
  │  "기간 성과 계산 & 커밋"      │               │             │            │
  │─────────────────────────────────────────────►│             │            │
  │                │              │               │  SELECT     │            │
  │                │              │               │◄───────────│            │
  │                │              │               │  trades     │            │
  │                │              │               │────────────►│            │
  │                │              │            │             │ PnL/MDD/  │
  │                │              │            │             │ Sharpe    │
  │                │              │            │             │ JSON→hash │
  │                │              │            │             │────------►│
  │                │              │            │             │ commitPerformance
  │                │              │            │             │◄───────────│
  │                │              │            │             │  tx receipt
  │◄────────────────────────────────────────────────────────│            │
```

### 4.2 웹 UI에서 온체인 성과 조회

```
User          Web UI         Spring (optional)    Chain
  │               │                   │              │
  │  지갑 연결    │                   │              │
  │──────────────►│                   │              │
  │               │  getPerformance (view)          │
  │               │─────────────────────────────────►│
  │               │◄─────────────────────────────────│
  │               │  이벤트 로그 조회 (PerformanceCommitted)
  │               │─────────────────────────────────►│
  │               │◄─────────────────────────────────│
  │  목록 표시    │                   │              │
  │◄──────────────│                   │              │
```

---

## 5. 디렉터리 구조 (제안)

```
contract_report/
├── docs/
│   └── SYSTEM_DESIGN.md          # 본 설계서
├── kiwoom-agent/                 # Python: Kiwoom 전용 (최소)
│   ├── requirements.txt
│   ├── fetch_trades.py           # 계좌/기간 → PostgreSQL
│   └── schema.sql                # trades 테이블 (PostgreSQL)
├── backend/                      # Spring Boot
│   ├── src/main/java/.../performance/
│   │   ├── PerformanceApplication.java
│   │   ├── domain/               # Trade, PerformanceSummary
│   │   ├── repository/           # TradeRepository (PostgreSQL)
│   │   ├── service/              # PerformanceCalculator, HashService, BlockchainService
│   │   ├── web/                  # REST (기간 조회, 성과 계산, 커밋 트리거)
│   │   └── config/
│   └── build.gradle
├── contracts/                    # Solidity + Foundry
│   ├── src/PerformanceRegistry.sol
│   ├── test/
│   └── script/Deploy.s.sol
└── web-ui/                       # Next.js + React
    ├── app/
    ├── components/
    └── package.json
```

---

## 6. 데이터 스키마 요약

- **DB**: PostgreSQL.
- **trades**: `id`, `account_id`, `trade_date`, `symbol`, `side`, `qty`, `price`, `fee`, `order_id`, `exec_id`, `strategy_tag`
- **performance_summary** (메모리/JSON): `account_id`, `strategy_tag`, `period_start`, `period_end`, `total_pnl`, `max_drawdown`, `sharpe_ratio`, `equity_curve_sampled` → 직렬화 후 SHA-256 해시

---

## 7. 비기능 요구사항 반영

- **개인정보**: 원본 매매 데이터는 외부 전송 없음. 온체인에는 요약 해시만 기록.
- **인증**: Kiwoom 인증/토큰은 사용자 PC의 Python 에이전트 환경에만 저장.
- **개발 환경**: Python 3.x (Kiwoom 에이전트), Java 17+ / Spring Boot 3 (백엔드), Solidity + Foundry, TypeScript + Next.js (UI).
- **체인**: PoC는 Sepolia 또는 Amoy 등 테스트넷; 가스비는 PoC 단계에서 무시.

이 설계서를 기준으로 각 레포의 코드 골격을 생성한다.
