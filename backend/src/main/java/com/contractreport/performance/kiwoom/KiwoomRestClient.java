package com.contractreport.performance.kiwoom;

import com.contractreport.performance.config.KiwoomProperties;
import com.fasterxml.jackson.databind.JsonNode;
import com.fasterxml.jackson.databind.ObjectMapper;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.http.*;
import org.springframework.stereotype.Component;
import org.springframework.web.client.RestTemplate;

import java.util.*;

/**
 * 키움 REST API TR 호출.
 * - kt00007: 계좌별주문체결내역상세요청 (주문/체결)
 * - ka10170: 당일매매일지요청 (당일 매매)
 * 공식 문서: https://openapi.kiwoom.com/m/guide/apiguide
 */
@Component
public class KiwoomRestClient {

    private static final Logger log = LoggerFactory.getLogger(KiwoomRestClient.class);

    /** 계좌별주문체결내역상세요청 */
    public static final String TR_ORDER_EXEC = "kt00007";
    /** 당일매매일지요청 */
    public static final String TR_DAILY_TRADES = "ka10170";

    private final KiwoomProperties properties;
    private final KiwoomTokenClient tokenClient;
    private final RestTemplate restTemplate;
    private final ObjectMapper objectMapper;

    public KiwoomRestClient(KiwoomProperties properties, KiwoomTokenClient tokenClient,
                            RestTemplate restTemplate, ObjectMapper objectMapper) {
        this.properties = properties;
        this.tokenClient = tokenClient;
        this.restTemplate = restTemplate;
        this.objectMapper = objectMapper;
    }

    /**
     * TR 호출 공통: POST /api/dostk/ordr (주문·체결) 또는 /api/dostk/acnt (계좌).
     * @param apiId TR명 (kt00007, ka10170 등)
     * @param body 요청 Body (TR별 파라미터)
     * @return 응답 JSON 노드; 실패 시 null
     */
    public JsonNode callTr(String apiId, Map<String, Object> body) {
        String token = tokenClient.getAccessToken();
        if (token == null) {
            log.warn("No Kiwoom token available");
            return null;
        }
        String path = (apiId != null && apiId.startsWith("ka")) ? "/api/dostk/acnt" : "/api/dostk/ordr";
        String url = properties.getBaseUrl().replaceAll("/$", "") + path;
        HttpHeaders headers = new HttpHeaders();
        headers.setContentType(MediaType.APPLICATION_JSON);
        headers.set("Authorization", "Bearer " + token);
        headers.set("api-id", apiId);
        try {
            ResponseEntity<String> response = restTemplate.exchange(
                    url,
                    HttpMethod.POST,
                    new HttpEntity<>(body != null ? body : Map.of(), headers),
                    String.class
            );
            if (response.getStatusCode().is2xxSuccessful() && response.getBody() != null) {
                return objectMapper.readTree(response.getBody());
            }
            log.warn("Kiwoom TR {} failed: status={}", apiId, response.getStatusCode());
            return null;
        } catch (Exception e) {
            log.error("Kiwoom TR {} request failed", apiId, e);
            return null;
        }
    }

    /**
     * 계좌별 주문 체결 내역 조회 (kt00007).
     * 문서 기준: 계좌번호·시작일·종료일 등 TR별 Body 파라미터 필요. 실제 필드명은 키움 가이드 참고.
     */
    public JsonNode fetchOrderExecutions(String accountNo, String startDate, String endDate) {
        Map<String, Object> body = new HashMap<>();
        body.put("acnt_no", accountNo);
        body.put("strt_dt", startDate); // YYYYMMDD
        body.put("end_dt", endDate);
        return callTr(TR_ORDER_EXEC, body);
    }

    /**
     * 당일 매매일지 조회 (ka10170).
     * strt_dt: YYYYMMDD, (선택) stk_cd: 종목코드
     */
    public JsonNode fetchDailyTrades(String startDate, String stkCd) {
        Map<String, Object> body = new HashMap<>();
        body.put("strt_dt", startDate);
        if (stkCd != null && !stkCd.isBlank()) {
            body.put("stk_cd", stkCd);
        }
        return callTr(TR_DAILY_TRADES, body);
    }

    /**
     * TR 응답에서 체결/매매 목록을 파싱해 KiwoomTradeDto 리스트로 변환.
     * 키움 실제 응답 구조에 따라 필드명 매핑이 달라질 수 있음. (output1, list 등)
     */
    public List<KiwoomTradeDto> parseTradesFromResponse(JsonNode response, String accountNo) {
        if (response == null) return List.of();
        List<KiwoomTradeDto> list = new ArrayList<>();
        JsonNode output1 = response.path("output1");
        if (output1.isMissingNode()) {
            JsonNode listNode = response.path("list");
            if (listNode.isArray()) {
                for (JsonNode item : listNode) list.add(toTradeDto(item, accountNo));
            }
            return list;
        }
        if (output1.isArray()) {
            for (JsonNode item : output1) list.add(toTradeDto(item, accountNo));
        } else {
            list.add(toTradeDto(output1, accountNo));
        }
        return list;
    }

    private KiwoomTradeDto toTradeDto(JsonNode n, String accountNo) {
        // 키움 응답 필드명은 TR별로 상이. 예: ord_dt, ord_tm, stk_cd, ord_qty, exec_uv, sll_buy_tp 등
        String symbol = n.has("stk_cd") ? n.path("stk_cd").asText("") : n.path("symbol").asText("");
        String side = n.has("sll_buy_tp") ? (n.path("sll_buy_tp").asText("").startsWith("1") ? "BUY" : "SELL")
                : (n.has("side") ? n.path("side").asText("BUY") : "BUY");
        if (n.has("ord_side") || n.has("매매구분")) {
            String v = n.has("ord_side") ? n.path("ord_side").asText("") : n.path("매매구분").asText("");
            if (v.contains("매도") || v.contains("2") || "2".equals(v)) side = "SELL";
            else if (v.contains("매수") || v.contains("1") || "1".equals(v)) side = "BUY";
        }
        String qtyStr = n.has("exec_qty") ? n.path("exec_qty").asText("0") : n.has("ord_qty") ? n.path("ord_qty").asText("0") : n.path("qty").asText("0");
        String priceStr = n.has("exec_uv") ? n.path("exec_uv").asText("0") : n.has("ord_uv") ? n.path("ord_uv").asText("0") : n.path("price").asText("0");
        String orderId = n.has("ord_no") ? n.path("ord_no").asText("") : n.path("order_id").asText("");
        String execId = n.has("exec_no") ? n.path("exec_no").asText("") : n.path("exec_id").asText("");
        String dateStr = n.has("ord_dt") ? n.path("ord_dt").asText("") : n.path("trade_date").asText("");
        String timeStr = n.has("ord_tm") ? n.path("ord_tm").asText("") : n.path("trade_time").asText("000000");
        String tradeDate = parseTradeDateTime(dateStr, timeStr);

        return KiwoomTradeDto.builder()
                .accountNo(accountNo)
                .symbol(symbol)
                .side(side)
                .qty(qtyStr)
                .price(priceStr)
                .orderId(orderId)
                .execId(execId)
                .tradeDateTime(tradeDate)
                .fee(n.has("fee") ? n.path("fee").asText("0") : "0")
                .build();
    }

    private static String parseTradeDateTime(String yyyyMMdd, String HHmmss) {
        if (yyyyMMdd == null || yyyyMMdd.length() < 8) return "";
        if (HHmmss == null || HHmmss.length() < 6) HHmmss = "000000";
        return yyyyMMdd.substring(0, 4) + "-" + yyyyMMdd.substring(4, 6) + "-" + yyyyMMdd.substring(6, 8)
                + "T" + HHmmss.substring(0, 2) + ":" + HHmmss.substring(2, 4) + ":" + HHmmss.substring(4, 6);
    }
}
