package com.contractreport.performance.service;

import com.contractreport.performance.domain.PerformanceSummary;
import com.contractreport.performance.domain.Trade;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;

import java.math.BigDecimal;
import java.time.Instant;
import java.time.LocalDateTime;
import java.util.List;

import static org.junit.jupiter.api.Assertions.*;

class PerformanceCalculatorTest {

    private PerformanceCalculator calculator;

    private static final Instant PERIOD_START = Instant.parse("2024-01-01T00:00:00Z");
    private static final Instant PERIOD_END   = Instant.parse("2024-01-31T23:59:59Z");

    @BeforeEach
    void setUp() {
        calculator = new PerformanceCalculator();
    }

    // ──────────────── 헬퍼 ────────────────

    private Trade sellTrade(String date, String qty, String price, String fee) {
        return Trade.builder()
                .id(null).accountId("acc1")
                .tradeDate(LocalDateTime.parse(date + "T09:00:00"))
                .symbol("AAPL").side("SELL")
                .qty(new BigDecimal(qty)).price(new BigDecimal(price)).fee(new BigDecimal(fee))
                .orderId("o1").execId("e1").strategyTag(null)
                .build();
    }

    private Trade buyTrade(String date, String qty, String price, String fee) {
        return Trade.builder()
                .id(null).accountId("acc1")
                .tradeDate(LocalDateTime.parse(date + "T09:00:00"))
                .symbol("AAPL").side("BUY")
                .qty(new BigDecimal(qty)).price(new BigDecimal(price)).fee(new BigDecimal(fee))
                .orderId("o2").execId("e2").strategyTag(null)
                .build();
    }

    // ──────────────── calculate() ────────────────

    @Test
    void calculate_nullTrades_returnsZeroSummary() {
        PerformanceSummary result = calculator.calculate("acc1", "tag1", PERIOD_START, PERIOD_END, null);

        assertEquals(BigDecimal.ZERO, result.getTotalPnl());
        assertEquals(BigDecimal.ZERO, result.getMaxDrawdown());
        assertEquals(BigDecimal.ZERO, result.getSharpeRatio());
        assertTrue(result.getEquityCurveSampled().isEmpty());
        assertEquals("tag1", result.getStrategyTag());
    }

    @Test
    void calculate_emptyTrades_returnsZeroSummary() {
        PerformanceSummary result = calculator.calculate("acc1", null, PERIOD_START, PERIOD_END, List.of());

        assertEquals(BigDecimal.ZERO, result.getTotalPnl());
        assertEquals(BigDecimal.ZERO, result.getMaxDrawdown());
        assertEquals(BigDecimal.ZERO, result.getSharpeRatio());
        assertTrue(result.getEquityCurveSampled().isEmpty());
        assertEquals("", result.getStrategyTag()); // null strategyTag -> ""
    }

    @Test
    void calculate_singleSellTrade_positivePnl_noDrawdown() {
        // SELL 10 @ 100, fee=5 → PnL = 1000 - 5 = 995
        Trade trade = sellTrade("2024-01-01", "10", "100", "5");

        PerformanceSummary result = calculator.calculate("acc1", null, PERIOD_START, PERIOD_END, List.of(trade));

        assertEquals(new BigDecimal("995"), result.getTotalPnl());
        // peak=0 → running=995 → peak=995 → dd=0
        assertEquals(BigDecimal.ZERO, result.getMaxDrawdown());
        assertEquals(1, result.getEquityCurveSampled().size());
    }

    @Test
    void calculate_singleBuyTrade_negativePnl_drawdownFromZero() {
        // BUY 10 @ 100, fee=5 → PnL = -1000 - 5 = -1005
        Trade trade = buyTrade("2024-01-01", "10", "100", "5");

        PerformanceSummary result = calculator.calculate("acc1", null, PERIOD_START, PERIOD_END, List.of(trade));

        assertEquals(new BigDecimal("-1005"), result.getTotalPnl());
        // peak=0, running=-1005, dd=0-(-1005)=1005
        assertEquals(new BigDecimal("1005"), result.getMaxDrawdown());
    }

    @Test
    void calculate_buyThenSell_differentDays_correctTotalPnl() {
        // Day1: BUY 10@100 fee=5 → -1005
        // Day2: SELL 10@120 fee=5 → +1195
        // total = 190
        Trade buy  = buyTrade("2024-01-01", "10", "100", "5");
        Trade sell = sellTrade("2024-01-02", "10", "120", "5");

        PerformanceSummary result = calculator.calculate("acc1", null, PERIOD_START, PERIOD_END, List.of(buy, sell));

        assertEquals(new BigDecimal("190"), result.getTotalPnl());
        assertEquals(2, result.getEquityCurveSampled().size());
    }

    @Test
    void calculate_peakThenDropDown_correctMaxDrawdown() {
        // Day1: SELL 10@100 fee=0 → +1000  (peak=1000)
        // Day2: BUY  5@100  fee=0 → -500   (equity=500, dd=500)
        Trade sell = sellTrade("2024-01-01", "10", "100", "0");
        Trade buy  = buyTrade("2024-01-02",  "5", "100", "0");

        PerformanceSummary result = calculator.calculate("acc1", null, PERIOD_START, PERIOD_END, List.of(sell, buy));

        assertEquals(new BigDecimal("500"), result.getTotalPnl());
        assertEquals(new BigDecimal("500"), result.getMaxDrawdown());
    }

    @Test
    void calculate_sameDay_tradesGroupedIntoOneEquityPoint() {
        // 두 SELL 같은 날 → equity curve 길이=1, totalPnl=1000
        Trade t1 = sellTrade("2024-01-01", "5", "100", "0");
        Trade t2 = sellTrade("2024-01-01", "5", "100", "0");

        PerformanceSummary result = calculator.calculate("acc1", null, PERIOD_START, PERIOD_END, List.of(t1, t2));

        assertEquals(new BigDecimal("1000"), result.getTotalPnl());
        assertEquals(1, result.getEquityCurveSampled().size());
    }

    @Test
    void calculate_nullFee_treatedAsZero() {
        Trade trade = Trade.builder()
                .id(null).accountId("acc1")
                .tradeDate(LocalDateTime.parse("2024-01-01T09:00:00"))
                .symbol("AAPL").side("SELL")
                .qty(new BigDecimal("10")).price(new BigDecimal("100"))
                .fee(null) // null fee
                .orderId("o1").execId("e1").strategyTag(null)
                .build();

        PerformanceSummary result = calculator.calculate("acc1", null, PERIOD_START, PERIOD_END, List.of(trade));

        assertEquals(new BigDecimal("1000"), result.getTotalPnl());
    }

    @Test
    void calculate_sideIsCaseInsensitive() {
        // "sell" (소문자)도 SELL로 처리돼야 함
        Trade trade = Trade.builder()
                .id(null).accountId("acc1")
                .tradeDate(LocalDateTime.parse("2024-01-01T09:00:00"))
                .symbol("AAPL").side("sell")
                .qty(new BigDecimal("10")).price(new BigDecimal("100"))
                .fee(new BigDecimal("0"))
                .orderId("o1").execId("e1").strategyTag(null)
                .build();

        PerformanceSummary result = calculator.calculate("acc1", null, PERIOD_START, PERIOD_END, List.of(trade));

        assertEquals(new BigDecimal("1000"), result.getTotalPnl());
    }

    @Test
    void calculate_returnsCorrectAccountIdAndPeriod() {
        PerformanceSummary result = calculator.calculate("myAccount", "stratA", PERIOD_START, PERIOD_END, List.of());

        assertEquals("myAccount", result.getAccountId());
        assertEquals("stratA", result.getStrategyTag());
        assertEquals(PERIOD_START, result.getPeriodStart());
        assertEquals(PERIOD_END, result.getPeriodEnd());
    }

    // ──────────────── computeWinRate() ────────────────

    @Test
    void computeWinRate_nullTrades_returnsZero() {
        assertEquals(BigDecimal.ZERO, calculator.computeWinRate(null));
    }

    @Test
    void computeWinRate_emptyTrades_returnsZero() {
        assertEquals(BigDecimal.ZERO, calculator.computeWinRate(List.of()));
    }

    @Test
    void computeWinRate_oneWinOneLoss_returns50() {
        // SELL 10@100 fee=0 → PnL=1000 (win)
        // BUY  10@100 fee=0 → PnL=-1000 (loss)
        Trade win  = sellTrade("2024-01-01", "10", "100", "0");
        Trade loss = buyTrade("2024-01-01", "10", "100", "0");

        BigDecimal rate = calculator.computeWinRate(List.of(win, loss));

        // 1/2 * 100 = 50.0000
        assertEquals(new BigDecimal("50.0000"), rate);
    }

    @Test
    void computeWinRate_allWins_returns100() {
        Trade t1 = sellTrade("2024-01-01", "10", "100", "0");
        Trade t2 = sellTrade("2024-01-02", "5", "200", "0");

        BigDecimal rate = calculator.computeWinRate(List.of(t1, t2));

        assertEquals(new BigDecimal("100.0000"), rate);
    }

    @Test
    void computeWinRate_allLosses_returnsZero() {
        Trade t1 = buyTrade("2024-01-01", "10", "100", "0");
        Trade t2 = buyTrade("2024-01-02", "5", "200", "0");

        BigDecimal rate = calculator.computeWinRate(List.of(t1, t2));

        assertEquals(new BigDecimal("0.0000"), rate);
    }

    @Test
    void computeWinRate_exactlyZeroPnl_notCountedAsWin() {
        // SELL 10@100 fee=1000 → PnL = 1000 - 1000 = 0 (not a win)
        Trade breakEven = sellTrade("2024-01-01", "10", "100", "1000");

        BigDecimal rate = calculator.computeWinRate(List.of(breakEven));

        assertEquals(new BigDecimal("0.0000"), rate);
    }
}
