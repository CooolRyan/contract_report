package com.contractreport.performance.service;

import com.contractreport.performance.domain.PerformanceSummary;
import com.contractreport.performance.domain.Trade;
import org.springframework.stereotype.Service;

import java.math.BigDecimal;
import java.math.RoundingMode;
import java.time.Instant;
import java.time.LocalDate;
import java.time.ZoneId;
import java.util.ArrayList;
import java.util.List;
import java.util.Map;
import java.util.stream.Collectors;

/**
 * 거래 목록으로부터 PnL, MDD, Sharpe, 일별 equity curve 계산.
 */
@Service
public class PerformanceCalculator {

    public PerformanceSummary calculate(String accountId, String strategyTag,
                                         Instant periodStart, Instant periodEnd,
                                         List<Trade> trades) {
        if (trades == null || trades.isEmpty()) {
            return PerformanceSummary.builder()
                    .accountId(accountId)
                    .strategyTag(strategyTag != null ? strategyTag : "")
                    .periodStart(periodStart)
                    .periodEnd(periodEnd)
                    .totalPnl(BigDecimal.ZERO)
                    .maxDrawdown(BigDecimal.ZERO)
                    .sharpeRatio(BigDecimal.ZERO)
                    .equityCurveSampled(List.of())
                    .build();
        }

        // 일별 PnL (날짜 -> 당일 PnL 합계)
        Map<LocalDate, BigDecimal> dailyPnl = trades.stream()
                .collect(Collectors.groupingBy(
                        t -> t.getTradeDate().toLocalDate(),
                        Collectors.mapping(this::tradePnl, Collectors.reducing(BigDecimal.ZERO, BigDecimal::add))
                ));

        List<LocalDate> sortedDates = dailyPnl.keySet().stream().sorted().toList();
        BigDecimal running = BigDecimal.ZERO;
        List<BigDecimal> equityCurve = new ArrayList<>();
        BigDecimal peak = BigDecimal.ZERO;
        BigDecimal maxDrawdown = BigDecimal.ZERO;

        for (LocalDate d : sortedDates) {
            running = running.add(dailyPnl.getOrDefault(d, BigDecimal.ZERO));
            equityCurve.add(running);
            if (running.compareTo(peak) > 0) peak = running;
            BigDecimal dd = peak.subtract(running);
            if (dd.compareTo(maxDrawdown) > 0) maxDrawdown = dd;
        }

        BigDecimal totalPnl = running;
        // Sharpe: 연율화 (단순화: 일별 수익률 표준편차 기반, 무위험 0 가정)
        BigDecimal sharpe = computeSharpe(equityCurve);

        return PerformanceSummary.builder()
                .accountId(accountId)
                .strategyTag(strategyTag != null ? strategyTag : "")
                .periodStart(periodStart)
                .periodEnd(periodEnd)
                .totalPnl(totalPnl)
                .maxDrawdown(maxDrawdown)
                .sharpeRatio(sharpe)
                .equityCurveSampled(equityCurve)
                .build();
    }

    private BigDecimal tradePnl(Trade t) {
        BigDecimal notional = t.getPrice().multiply(t.getQty());
        BigDecimal fee = t.getFee() != null ? t.getFee() : BigDecimal.ZERO;
        if ("SELL".equalsIgnoreCase(t.getSide())) {
            return notional.subtract(fee);
        }
        return notional.negate().subtract(fee);
    }

    private BigDecimal computeSharpe(List<BigDecimal> equityCurve) {
        if (equityCurve.size() < 2) return BigDecimal.ZERO;
        List<BigDecimal> returns = new ArrayList<>();
        for (int i = 1; i < equityCurve.size(); i++) {
            BigDecimal prev = equityCurve.get(i - 1);
            if (prev.compareTo(BigDecimal.ZERO) == 0) continue;
            BigDecimal ret = equityCurve.get(i).subtract(prev).divide(prev, 8, RoundingMode.HALF_UP);
            returns.add(ret);
        }
        if (returns.isEmpty()) return BigDecimal.ZERO;
        BigDecimal avg = returns.stream().reduce(BigDecimal.ZERO, BigDecimal::add)
                .divide(BigDecimal.valueOf(returns.size()), 8, RoundingMode.HALF_UP);
        BigDecimal variance = returns.stream()
                .map(r -> r.subtract(avg).pow(2))
                .reduce(BigDecimal.ZERO, BigDecimal::add)
                .divide(BigDecimal.valueOf(returns.size()), 8, RoundingMode.HALF_UP);
        BigDecimal std = BigDecimal.valueOf(Math.sqrt(variance.doubleValue()));
        if (std.compareTo(BigDecimal.ZERO) == 0) return BigDecimal.ZERO;
        // 연율화 계수 sqrt(252)
        return avg.divide(std, 4, RoundingMode.HALF_UP).multiply(BigDecimal.valueOf(Math.sqrt(252)));
    }

    /** 승률: PnL > 0인 거래 수 / 전체 거래 수 * 100 (거래 단위 기준) */
    public BigDecimal computeWinRate(List<Trade> trades) {
        if (trades == null || trades.isEmpty()) return BigDecimal.ZERO;
        long wins = trades.stream().filter(t -> tradePnl(t).compareTo(BigDecimal.ZERO) > 0).count();
        return BigDecimal.valueOf(wins).divide(BigDecimal.valueOf(trades.size()), 4, RoundingMode.HALF_UP).multiply(BigDecimal.valueOf(100));
    }
}
