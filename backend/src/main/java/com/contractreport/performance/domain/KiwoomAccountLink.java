package com.contractreport.performance.domain;

import lombok.Builder;
import lombok.Value;

import java.time.LocalDateTime;

/**
 * 사용자-키움 계좌 연동. 우리 서비스의 account_id로 trades에 저장.
 */
@Value
@Builder
public class KiwoomAccountLink {
    Long id;
    /** 사이트 사용자 식별자 (예: 지갑 주소) */
    String userId;
    /** 키움 증권 계좌번호 */
    String kiwoomAccountNo;
    /** 우리 DB trades.account_id 로 사용할 값 */
    String ourAccountId;
    LocalDateTime createdAt;
}
