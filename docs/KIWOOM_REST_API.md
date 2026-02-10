# 키움 REST API 연동 (서비스용)

서비스를 운영할 때는 사용자 PC에 키움 HTS를 설치하지 않고, **키움 REST API**를 서버(Spring)에서 호출하면 됩니다.

## 요약

| 항목 | 내용 |
|------|------|
| **운영 도메인** | `https://api.kiwoom.com` |
| **모의투자** | `https://mockapi.kiwoom.com` (KRX만 지원) |
| **인증** | OAuth 2.0 (Client Credentials). POST `/oauth2/token`에 `grant_type`, `appkey`, `secretkey` 전달. |
| **토큰 유효기간** | 24시간 (매일 재발급 필요) |
| **문서** | [키움 REST API 가이드](https://openapi.kiwoom.com/m/guide/apiguide) |

## 서비스 신청

1. 키움증권 계좌 개설
2. [REST API 홈](https://openapi.kiwoom.com)에서 API 사용신청 → 약관·동의, IP 등록(최대 10개), 계좌 등록(SMS 인증)
3. App Key, App Secret 다운로드 (1회만 가능) → 접근토큰 발급

## 백엔드에서 사용할 TR 예시 (매매/체결)

- **접근토큰 발급**: `au10001` (OAuth2 token)
- **체결요청**: `ka10076`
- **계좌별주문체결내역상세요청**: `kt00007`
- **당일매매일지요청**: `ka10170`
- 기타: [가이드 전체메뉴](https://openapi.kiwoom.com/m/guide/apiguide) 참고

## Spring 연동 시

1. **설정**: `appkey`, `secretkey`는 환경변수 또는 Vault 등에 저장. (리포에 올리지 않기)
2. **토큰**: 매일(또는 만료 전) POST `https://api.kiwoom.com/oauth2/token` 호출해 접근토큰 발급 후 캐시.
3. **TR 호출**: 발급한 토큰으로 필요한 TR(체결/계좌 등) 요청 → 응답 파싱 후 `trades` 테이블에 맞게 저장.
4. **스케줄**: 주기적으로 체결/매매일지 조회 후 DB 적재 → 기존 성과 계산·해시·온체인 플로우 그대로 사용.

백엔드에 `KiwoomRestClient`(또는 `kiwoom-rest` 모듈)를 두고, OAuth2 + TR 호출을 구현하면 됩니다. (현재 `kiwoom-agent/`는 로컬 Open API+용이며, 서비스용은 Spring에서 REST API만 호출하도록 구성 가능.)

## 구현된 API (Spring)

| 메서드 | 경로 | 설명 |
|--------|------|------|
| POST | `/api/kiwoom/link` | 키움 계좌 연동. Body: `{ "userId", "kiwoomAccountNo" }` |
| GET | `/api/kiwoom/links?userId=` | 내 연동 계좌 목록 |
| GET | `/api/kiwoom/trades?userId=&kiwoomAccountNo=&start=&end=` | 키움 API로 매매/체결 조회 (우리 DB 아님) |
| POST | `/api/kiwoom/register` | 선택한 체결을 우리 `trades`에 등록. Body: `{ "userId", "kiwoomAccountNo", "trades": [ KiwoomTradeDto... ] }` |

- **userId**: 사이트 사용자 식별자(예: 지갑 주소). 프론트에서 전달.
- 연동 시 `kiwoom_account_links` 테이블에 저장되고, `our_account_id`가 `trades.account_id`로 사용됨.
- 키움 TR 응답 필드명은 TR별로 상이할 수 있으므로, 실제 키움 가이드에 맞춰 `KiwoomRestClient.parseTradesFromResponse` 매핑을 조정할 수 있음.
