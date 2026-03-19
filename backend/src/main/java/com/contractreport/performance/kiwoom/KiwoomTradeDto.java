package com.contractreport.performance.kiwoom;

import com.fasterxml.jackson.annotation.JsonIgnoreProperties;
import lombok.Builder;
import lombok.Value;

/**
 * 키움 API에서 조회한 체결/매매 한 건 (아직 우리 DB에 없는 임시 DTO).
 */
@Value
@Builder
@JsonIgnoreProperties(ignoreUnknown = true)
public class KiwoomTradeDto {
    String accountNo;
    String symbol;
    String side;
    String qty;
    String price;
    String orderId;
    String execId;
    String tradeDateTime; // ISO_LOCAL_DATE_TIME 형식 문자열
    String fee;
    /** 전략 태그 (quant-trader 등에서 자동 등록 시 사용). */
    String strategyTag;
}
