package com.contractreport.performance.domain;

import com.fasterxml.jackson.annotation.JsonProperty;
import lombok.Builder;
import lombok.Value;

import java.math.BigDecimal;
import java.time.Instant;
import java.util.List;

/**
 * 기간별 성과 요약. JSON 직렬화 후 SHA-256 해시 계산 대상.
 */
@Value
@Builder
public class PerformanceSummary {
    String accountId;
    String strategyTag;

    @JsonProperty("period_start")
    Instant periodStart;

    @JsonProperty("period_end")
    Instant periodEnd;

    @JsonProperty("total_pnl")
    BigDecimal totalPnl;

    @JsonProperty("max_drawdown")
    BigDecimal maxDrawdown;

    @JsonProperty("sharpe_ratio")
    BigDecimal sharpeRatio;

    /** 일별 등가치 곡선 샘플 (예: 하루 1점) */
    @JsonProperty("equity_curve_sampled")
    List<BigDecimal> equityCurveSampled;
}
