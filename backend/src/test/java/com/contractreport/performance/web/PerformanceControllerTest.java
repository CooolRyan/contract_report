package com.contractreport.performance.web;

import com.contractreport.performance.domain.PerformanceCommit;
import com.contractreport.performance.domain.PerformanceSummary;
import com.contractreport.performance.domain.Trade;
import com.contractreport.performance.repository.PerformanceCommitRepository;
import com.contractreport.performance.repository.TradeRepository;
import com.contractreport.performance.service.BlockchainService;
import com.contractreport.performance.service.HashService;
import com.contractreport.performance.service.PerformanceCalculator;
import org.junit.jupiter.api.Test;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.boot.test.autoconfigure.web.servlet.WebMvcTest;
import org.springframework.boot.test.mock.mockito.MockBean;
import org.springframework.http.MediaType;
import org.springframework.test.web.servlet.MockMvc;

import java.math.BigDecimal;
import java.time.Instant;
import java.time.LocalDateTime;
import java.util.List;

import static org.mockito.ArgumentMatchers.*;
import static org.mockito.Mockito.*;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.*;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.*;

@WebMvcTest(PerformanceController.class)
class PerformanceControllerTest {

    @Autowired MockMvc mockMvc;

    @MockBean TradeRepository              tradeRepository;
    @MockBean PerformanceCommitRepository  performanceCommitRepository;
    @MockBean PerformanceCalculator        performanceCalculator;
    @MockBean HashService                  hashService;
    @MockBean BlockchainService            blockchainService;

    // ──────────────── GET /api/trades ────────────────

    @Test
    void getTrades_noData_returnsEmptyArray() throws Exception {
        when(tradeRepository.findByAccountAndPeriod(any(), any(), any())).thenReturn(List.of());

        mockMvc.perform(get("/api/trades")
                        .param("accountId", "acc1")
                        .param("start", "2024-01-01T00:00:00")
                        .param("end",   "2024-01-31T23:59:59"))
                .andExpect(status().isOk())
                .andExpect(content().contentType(MediaType.APPLICATION_JSON))
                .andExpect(jsonPath("$").isArray())
                .andExpect(jsonPath("$.length()").value(0));
    }

    @Test
    void getTrades_returnsTradeList() throws Exception {
        Trade trade = Trade.builder()
                .id(1L).accountId("acc1")
                .tradeDate(LocalDateTime.parse("2024-01-15T09:00:00"))
                .symbol("AAPL").side("BUY")
                .qty(new BigDecimal("10")).price(new BigDecimal("100"))
                .fee(new BigDecimal("5")).orderId("o1").execId("e1").strategyTag(null)
                .build();
        when(tradeRepository.findByAccountAndPeriod(eq("acc1"), any(), any())).thenReturn(List.of(trade));

        mockMvc.perform(get("/api/trades")
                        .param("accountId", "acc1")
                        .param("start", "2024-01-01T00:00:00")
                        .param("end",   "2024-01-31T23:59:59"))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$.length()").value(1))
                .andExpect(jsonPath("$[0].accountId").value("acc1"))
                .andExpect(jsonPath("$[0].symbol").value("AAPL"));
    }

    @Test
    void getTrades_strategyTagFilter_appliesFilter() throws Exception {
        Trade matchTrade = Trade.builder()
                .id(1L).accountId("acc1")
                .tradeDate(LocalDateTime.parse("2024-01-15T09:00:00"))
                .symbol("AAPL").side("BUY")
                .qty(BigDecimal.ONE).price(BigDecimal.TEN)
                .fee(BigDecimal.ZERO).orderId("o1").execId("e1")
                .strategyTag("stratA")
                .build();
        Trade otherTrade = Trade.builder()
                .id(2L).accountId("acc1")
                .tradeDate(LocalDateTime.parse("2024-01-16T09:00:00"))
                .symbol("GOOG").side("SELL")
                .qty(BigDecimal.ONE).price(BigDecimal.TEN)
                .fee(BigDecimal.ZERO).orderId("o2").execId("e2")
                .strategyTag("stratB")
                .build();
        when(tradeRepository.findByAccountAndPeriod(any(), any(), any()))
                .thenReturn(List.of(matchTrade, otherTrade));

        mockMvc.perform(get("/api/trades")
                        .param("accountId", "acc1")
                        .param("start", "2024-01-01T00:00:00")
                        .param("end",   "2024-01-31T23:59:59")
                        .param("strategyTag", "stratA"))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$.length()").value(1))
                .andExpect(jsonPath("$[0].strategyTag").value("stratA"));
    }

    // ──────────────── GET /api/performance/summary ────────────────

    @Test
    void getPerformanceSummary_returnsResponseWithHashAndWinRate() throws Exception {
        PerformanceSummary summary = PerformanceSummary.builder()
                .accountId("acc1").strategyTag("")
                .periodStart(Instant.parse("2024-01-01T00:00:00Z"))
                .periodEnd(Instant.parse("2024-01-31T23:59:59Z"))
                .totalPnl(new BigDecimal("1234.56")).maxDrawdown(new BigDecimal("100"))
                .sharpeRatio(new BigDecimal("1.5000"))
                .equityCurveSampled(List.of())
                .build();

        when(tradeRepository.findByAccountAndPeriod(any(), any(), any())).thenReturn(List.of());
        when(performanceCalculator.calculate(any(), any(), any(), any(), any())).thenReturn(summary);
        when(hashService.sha256Hex(any())).thenReturn("a".repeat(64));
        when(performanceCalculator.computeWinRate(any())).thenReturn(new BigDecimal("75.0000"));

        mockMvc.perform(get("/api/performance/summary")
                        .param("accountId", "acc1")
                        .param("start", "2024-01-01T00:00:00")
                        .param("end",   "2024-01-31T23:59:59"))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$.hashHex").value("a".repeat(64)))
                .andExpect(jsonPath("$.winRate").value(75.0))
                .andExpect(jsonPath("$.tradeCount").value(0))
                .andExpect(jsonPath("$.verified").value(false))
                .andExpect(jsonPath("$.txHash").doesNotExist());
    }

    // ──────────────── GET /api/performance/commits ────────────────

    @Test
    void getCommits_noAccountId_returnsAllCommits() throws Exception {
        PerformanceCommit commit = PerformanceCommit.builder()
                .id(1L).accountId("acc1").strategyTag("")
                .periodStartEpoch(1_704_067_200L).periodEndEpoch(1_706_745_599L)
                .totalPnl(new BigDecimal("500")).maxDrawdown(new BigDecimal("50"))
                .sharpeRatio(new BigDecimal("1.2")).winRate(new BigDecimal("60"))
                .tradeCount(5).hashHex("a".repeat(64)).txHash("0xTX")
                .createdAt(LocalDateTime.parse("2024-01-31T12:00:00"))
                .build();
        when(performanceCommitRepository.findAll(50)).thenReturn(List.of(commit));

        mockMvc.perform(get("/api/performance/commits"))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$.length()").value(1))
                .andExpect(jsonPath("$[0].hash").value("a".repeat(64)))
                .andExpect(jsonPath("$[0].txHash").value("0xTX"))
                .andExpect(jsonPath("$[0].verified").value(true));
    }

    @Test
    void getCommits_withAccountId_queriesByAccount() throws Exception {
        when(performanceCommitRepository.findByAccountId(eq("acc1"), anyInt())).thenReturn(List.of());

        mockMvc.perform(get("/api/performance/commits")
                        .param("accountId", "acc1"))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$.length()").value(0));

        verify(performanceCommitRepository).findByAccountId(eq("acc1"), anyInt());
        verify(performanceCommitRepository, never()).findAll(anyInt());
    }

    @Test
    void getCommits_customLimit_passedToRepository() throws Exception {
        when(performanceCommitRepository.findAll(10)).thenReturn(List.of());

        mockMvc.perform(get("/api/performance/commits")
                        .param("limit", "10"))
                .andExpect(status().isOk());

        verify(performanceCommitRepository).findAll(10);
    }

    // ──────────────── POST /api/performance/commit ────────────────

    @Test
    void commitPerformance_validRequest_returnsOkWithTxHash() throws Exception {
        PerformanceSummary summary = PerformanceSummary.builder()
                .accountId("acc1").strategyTag("")
                .periodStart(Instant.parse("2024-01-01T00:00:00Z"))
                .periodEnd(Instant.parse("2024-01-31T23:59:59Z"))
                .totalPnl(new BigDecimal("500")).maxDrawdown(BigDecimal.ZERO)
                .sharpeRatio(BigDecimal.ZERO).equityCurveSampled(List.of())
                .build();

        when(tradeRepository.findByAccountAndPeriod(any(), any(), any())).thenReturn(List.of());
        when(performanceCalculator.calculate(any(), any(), any(), any(), any())).thenReturn(summary);
        when(hashService.sha256Hex(any())).thenReturn("b".repeat(64));
        when(blockchainService.commitPerformance(any(), anyLong(), anyLong())).thenReturn("0xTXHASH");
        when(performanceCalculator.computeWinRate(any())).thenReturn(BigDecimal.ZERO);

        mockMvc.perform(post("/api/performance/commit")
                        .contentType(MediaType.APPLICATION_JSON)
                        .content("""
                                {
                                  "accountId": "acc1",
                                  "start": "2024-01-01T00:00:00",
                                  "end":   "2024-01-31T23:59:59",
                                  "strategyTag": null
                                }
                                """))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$.txHash").value("0xTXHASH"))
                .andExpect(jsonPath("$.verified").value(true))
                .andExpect(jsonPath("$.hashHex").value("b".repeat(64)));

        verify(performanceCommitRepository).save(any());
    }

    @Test
    void commitPerformance_strategyTagFiltered() throws Exception {
        PerformanceSummary summary = PerformanceSummary.builder()
                .accountId("acc1").strategyTag("stratA")
                .periodStart(Instant.EPOCH).periodEnd(Instant.EPOCH)
                .totalPnl(BigDecimal.ZERO).maxDrawdown(BigDecimal.ZERO)
                .sharpeRatio(BigDecimal.ZERO).equityCurveSampled(List.of())
                .build();

        Trade matchTrade = Trade.builder()
                .id(1L).accountId("acc1")
                .tradeDate(LocalDateTime.parse("2024-01-10T09:00:00"))
                .symbol("AAPL").side("SELL")
                .qty(BigDecimal.ONE).price(BigDecimal.TEN)
                .fee(BigDecimal.ZERO).orderId("o1").execId("e1")
                .strategyTag("stratA")
                .build();

        when(tradeRepository.findByAccountAndPeriod(any(), any(), any()))
                .thenReturn(List.of(matchTrade));
        when(performanceCalculator.calculate(any(), any(), any(), any(), any())).thenReturn(summary);
        when(hashService.sha256Hex(any())).thenReturn("c".repeat(64));
        when(blockchainService.commitPerformance(any(), anyLong(), anyLong())).thenReturn("0xTX2");
        when(performanceCalculator.computeWinRate(any())).thenReturn(new BigDecimal("100.0000"));

        mockMvc.perform(post("/api/performance/commit")
                        .contentType(MediaType.APPLICATION_JSON)
                        .content("""
                                {
                                  "accountId": "acc1",
                                  "start": "2024-01-01T00:00:00",
                                  "end":   "2024-01-31T23:59:59",
                                  "strategyTag": "stratA"
                                }
                                """))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$.verified").value(true));
    }
}
