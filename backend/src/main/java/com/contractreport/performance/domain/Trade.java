package com.contractreport.performance.domain;

import lombok.Builder;
import lombok.Value;

import java.math.BigDecimal;
import java.time.LocalDateTime;

/**
 * 로컬 DB trades 테이블과 매핑되는 거래 한 건.
 */
@Value
@Builder
public class Trade {
    Long id;
    String accountId;
    LocalDateTime tradeDate;
    String symbol;
    String side;   // BUY, SELL
    BigDecimal qty;
    BigDecimal price;
    BigDecimal fee;
    String orderId;
    String execId;
    String strategyTag;  // optional
}
