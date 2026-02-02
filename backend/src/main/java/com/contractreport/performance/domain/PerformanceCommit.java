package com.contractreport.performance.domain;

import lombok.Builder;
import lombok.Value;

import java.math.BigDecimal;
import java.time.Instant;
import java.time.LocalDateTime;

/**
 * performance_commits 테이블 한 건 (커밋 목록 API용).
 */
@Value
@Builder
public class PerformanceCommit {
    Long id;
    String accountId;
    String strategyTag;
    long periodStartEpoch;
    long periodEndEpoch;
    BigDecimal totalPnl;
    BigDecimal maxDrawdown;
    BigDecimal sharpeRatio;
    BigDecimal winRate;
    int tradeCount;
    String hashHex;
    String txHash;
    LocalDateTime createdAt;
}
