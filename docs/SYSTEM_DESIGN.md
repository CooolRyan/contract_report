# On-chain Proof-of-Performance for Kiwoom Trading — 시스템 설계서

## 1. 프로젝트 개요

### 용도: 수익 인증 + 조언·전략 공유 시 검증 + 커뮤니티

- **사용자들이 자기 수익을 인증**하고, **조언·전략을 공유할 때** 그 말이 허위가 아닌지 **검증할 수단**을 제공하는 것이 목적이다.
- **커뮤니티**를 형성하고, 그 내용(인증된 성과·검증 가능한 기록)을 **원장성 DB + 블록체인**에 기록한다.
- 흐름: 사용자 A가 “이 기간에 이만큼 수익 냈다”고 성과를 커밋 → 온체인 해시 + 원장 DB에 기록 → 다른 사용자는 A가 **조언·전략을 공유할 때** **온체인/해시 검증**으로 실제 성과를 확인할 수 있다.

### 문제 정의
국내 주식 계좌(키움)의 실제 매매 내역을 기반으로, 개인 트레이딩 전략의 성과(PnL, MDD, 샤프 등)를 계산하고, 그 요약 결과를 블록체인에 커밋해서 **사후에 검증 가능**하게 만들고 싶다. 이 검증 수단을 바탕으로 **커뮤니티**(수익 인증·조언·전략 공유)를 형성하고, 그 내용을 **원장성 DB + 블록체인**에 기록한다.

### 목표
- 키움 API로 특정 계좌의 매매 내역을 주기적으로 수집
- (서버 또는 로컬에서) 성과 지표 계산
- 계산 결과 요약 JSON과 그 해시를 생성
- EVM 호환 체인(예: 테스트넷)에 해시를 기록하는 스마트 컨트랙트 및 UI
- **원장성 DB**(커밋 목록·성과 요약) + **블록체인**(해시)으로 검증 가능한 기록 유지

### 키움 API 선택: 서비스 vs 로컬 전용

| 방식 | 용도 | 설치/환경 |
|------|------|------------|
| **키움 REST API** | **서비스 운영** (서버에서 호출) | 로컬 HTS 불필요. OAuth2(App Key/Secret)로 `https://api.kiwoom.com` 호출. Spring 등 어떤 서버에서든 사용 가능. |
| **키움 Open API+** | 로컬 전용 (개인 PC) | Windows + 키움 HTS/Open API+ 설치 필요. COM 기반이라 사용자 PC에만 사용. |

**서비스를 하려면**: 로컬 HTS 없이 **키움 REST API**로 서버(Spring)에서 직접 접근토큰 발급 후 체결/계좌 TR 호출 → 결과를 PostgreSQL에 저장. 상세는 `docs/KIWOOM_REST_API.md` 및 [키움 REST API 가이드](https://openapi.kiwoom.com/m/guide/apiguide) 참고.

---

## 2. 아키텍처 개요

### 서비스 운영 시 (키움 REST API)

- **Spring Backend**가 키움 REST API를 호출: OAuth2 토큰 발급 → 체결/계좌 조회 TR 호출 → trades 등 DB 저장 → 성과 계산·해시·온체인 커밋. 사용자 PC에 별도 설치 없음.

### 로컬 전용 시 (키움 Open API+)

| 담당 | 기술 | 이유 |
|------|------|------|
| **Kiwoom 연동** | Python (KOAPY/COM) | Open API+가 Windows COM 기반. Python(pywin32, KOAPY)으로 거래 내역 조회 후 DB 적재. |
| **비즈니스 로직·API** | Spring Boot (Java) | 성과 계산, DB 조회, 해시 생성, 블록체인 호출. |

**데이터 경계**: (REST API 사용 시) Spring이 키움 서버 → DB 직접 적재. (Open API+ 사용 시) Python 에이전트가 거래 내역만 PostgreSQL에 적재하고, Spring은 DB 읽기·계산·온체인. **DB는 PostgreSQL 사용.**

### 검증 흐름 (커뮤니티·조언 검증에서의 사용)

- 사용자 A: 기간별 성과를 계산해 **해시를 온체인에 커밋** + **원장 DB**에 커밋 목록·요약 저장.
- 다른 사용자: A가 “이 기간 15% 수익” 등 **조언·전략을 공유할 때**, **원장 DB**에서 A의 커밋 목록을 보고, **온체인 해시** 또는 **해시 검증 UI**(JSON 업로드 + 온체인 해시 비교)로 **실제 성과와 일치하는지 검증** 가능.
- 커뮤니티: 인증된 성과(원장 + 블록체인)를 기준으로 피드/게시판 등을 구성하면, **성과 기반 조언의 신뢰도**를 높일 수 있음.

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
