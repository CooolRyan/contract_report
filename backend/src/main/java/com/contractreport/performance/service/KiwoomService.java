package com.contractreport.performance.service;

import com.contractreport.performance.domain.KiwoomAccountLink;
import com.contractreport.performance.domain.Trade;
import com.contractreport.performance.kiwoom.KiwoomRestClient;
import com.contractreport.performance.kiwoom.KiwoomTradeDto;
import com.contractreport.performance.repository.KiwoomAccountLinkRepository;
import com.contractreport.performance.repository.TradeRepository;
import com.fasterxml.jackson.databind.JsonNode;
import lombok.RequiredArgsConstructor;
import org.springframework.stereotype.Service;

import java.math.BigDecimal;
import java.time.LocalDateTime;
import java.time.format.DateTimeFormatter;
import java.util.List;
import java.util.Optional;
import java.util.stream.Collectors;

/**
 * 키움 계좌 연동·매매 조회·선택 등록 서비스.
 */
@Service
@RequiredArgsConstructor
public class KiwoomService {

    private static final DateTimeFormatter YYYYMMDD = DateTimeFormatter.ofPattern("yyyyMMdd");

    private final KiwoomAccountLinkRepository linkRepository;
    private final KiwoomRestClient kiwoomRestClient;
    private final TradeRepository tradeRepository;

    /**
     * 사용자가 키움 계좌를 연동. our_account_id = kiwoom_account_no 또는 user_키움계좌 조합.
     */
    public KiwoomAccountLink linkAccount(String userId, String kiwoomAccountNo) {
        Optional<KiwoomAccountLink> existing = linkRepository.findByUserIdAndKiwoomAccountNo(userId, kiwoomAccountNo);
        if (existing.isPresent()) {
            return existing.get();
        }
        String ourAccountId = "kiwoom_" + userId + "_" + kiwoomAccountNo;
        if (ourAccountId.length() > 32) {
            ourAccountId = "k_" + Math.abs(ourAccountId.hashCode());
        }
        KiwoomAccountLink link = KiwoomAccountLink.builder()
                .id(null)
                .userId(userId)
                .kiwoomAccountNo(kiwoomAccountNo)
                .ourAccountId(ourAccountId)
                .createdAt(LocalDateTime.now())
                .build();
        return linkRepository.save(link);
    }

    public List<KiwoomAccountLink> listLinks(String userId) {
        return linkRepository.findByUserId(userId);
    }

    /**
     * 키움 API로 해당 계좌의 주문체결/매매일지 조회. 연동된 계좌만 허용.
     */
    public List<KiwoomTradeDto> fetchTradesFromKiwoom(String userId, String kiwoomAccountNo,
                                                      LocalDateTime start, LocalDateTime end) {
        Optional<KiwoomAccountLink> link = linkRepository.findByUserIdAndKiwoomAccountNo(userId, kiwoomAccountNo);
        if (link.isEmpty()) {
            return List.of();
        }
        String strtDt = start.format(YYYYMMDD);
        String endDt = end.format(YYYYMMDD);
        JsonNode response = kiwoomRestClient.fetchOrderExecutions(kiwoomAccountNo, strtDt, endDt);
        List<KiwoomTradeDto> list = kiwoomRestClient.parseTradesFromResponse(response, kiwoomAccountNo);
        if (list.isEmpty()) {
            for (LocalDateTime d = start; !d.isAfter(end); d = d.plusDays(1)) {
                JsonNode daily = kiwoomRestClient.fetchDailyTrades(d.format(YYYYMMDD), null);
                list.addAll(kiwoomRestClient.parseTradesFromResponse(daily, kiwoomAccountNo));
            }
        }
        return list;
    }

    /**
     * 키움에서 조회한 체결 목록 중 선택한 항목을 우리 trades 테이블에 등록.
     * account_id = 연동의 our_account_id.
     */
    public int registerTrades(String userId, String kiwoomAccountNo, List<KiwoomTradeDto> selected) {
        if (selected == null || selected.isEmpty()) return 0;
        Optional<KiwoomAccountLink> link = linkRepository.findByUserIdAndKiwoomAccountNo(userId, kiwoomAccountNo);
        if (link.isEmpty()) return 0;
        String ourAccountId = link.get().getOurAccountId();
        List<Trade> trades = selected.stream()
                .map(dto -> toTrade(dto, ourAccountId))
                .collect(Collectors.toList());
        tradeRepository.saveAll(trades);
        return trades.size();
    }

    private static Trade toTrade(KiwoomTradeDto dto, String ourAccountId) {
        LocalDateTime tradeDate = parseTradeDateTime(dto.getTradeDateTime());
        return Trade.builder()
                .id(null)
                .accountId(ourAccountId)
                .tradeDate(tradeDate != null ? tradeDate : LocalDateTime.now())
                .symbol(dto.getSymbol() != null ? dto.getSymbol() : "")
                .side(dto.getSide() != null ? dto.getSide().toUpperCase() : "BUY")
                .qty(new BigDecimal(dto.getQty() != null ? dto.getQty() : "0"))
                .price(new BigDecimal(dto.getPrice() != null ? dto.getPrice() : "0"))
                .fee(new BigDecimal(dto.getFee() != null ? dto.getFee() : "0"))
                .orderId(dto.getOrderId())
                .execId(dto.getExecId())
                .strategyTag(null)
                .build();
    }

    private static LocalDateTime parseTradeDateTime(String s) {
        if (s == null || s.isBlank()) return null;
        try {
            return LocalDateTime.parse(s.replace(" ", "T"));
        } catch (Exception e) {
            return null;
        }
    }
}
