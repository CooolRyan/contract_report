package com.contractreport.performance.web;

import com.contractreport.performance.domain.PerformanceCommit;
import com.contractreport.performance.domain.PerformanceSummary;
import com.contractreport.performance.domain.Trade;
import com.contractreport.performance.repository.PerformanceCommitRepository;
import com.contractreport.performance.repository.TradeRepository;
import com.contractreport.performance.service.BlockchainService;
import com.contractreport.performance.service.HashService;
import com.contractreport.performance.service.PerformanceCalculator;
import lombok.RequiredArgsConstructor;
import org.springframework.format.annotation.DateTimeFormat;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.*;

import java.time.Instant;
import java.time.LocalDateTime;
import java.time.ZoneId;
import java.util.List;
import java.util.stream.Collectors;

/**
 * 기간 조회, 성과 계산, 온체인 커밋, 커밋 목록 REST API.
 */
@RestController
@RequestMapping("/api")
@RequiredArgsConstructor
public class PerformanceController {

    private final TradeRepository tradeRepository;
    private final PerformanceCommitRepository performanceCommitRepository;
    private final PerformanceCalculator performanceCalculator;
    private final HashService hashService;
    private final BlockchainService blockchainService;

    /**
     * 지정 계좌/기간 거래 내역 조회 (로컬 DB).
     */
    @GetMapping("/trades")
    public List<Trade> getTrades(
            @RequestParam String accountId,
            @RequestParam @DateTimeFormat(iso = DateTimeFormat.ISO.DATE_TIME) LocalDateTime start,
            @RequestParam @DateTimeFormat(iso = DateTimeFormat.ISO.DATE_TIME) LocalDateTime end,
            @RequestParam(required = false) String strategyTag) {
        List<Trade> trades = tradeRepository.findByAccountAndPeriod(accountId, start, end);
        if (strategyTag != null && !strategyTag.isBlank()) {
            trades = trades.stream().filter(t -> strategyTag.equals(t.getStrategyTag())).toList();
        }
        return trades;
    }

    /**
     * 지정 기간 성과 계산 (요약 + 해시). 온체인 전송 없음.
     */
    @GetMapping("/performance/summary")
    public PerformanceResponse getPerformanceSummary(
            @RequestParam String accountId,
            @RequestParam @DateTimeFormat(iso = DateTimeFormat.ISO.DATE_TIME) LocalDateTime start,
            @RequestParam @DateTimeFormat(iso = DateTimeFormat.ISO.DATE_TIME) LocalDateTime end,
            @RequestParam(required = false) String strategyTag) {
        List<Trade> trades = tradeRepository.findByAccountAndPeriod(accountId, start, end);
        if (strategyTag != null && !strategyTag.isBlank()) {
            trades = trades.stream().filter(t -> strategyTag.equals(t.getStrategyTag())).toList();
        }
        Instant periodStart = start.atZone(ZoneId.systemDefault()).toInstant();
        Instant periodEnd = end.atZone(ZoneId.systemDefault()).toInstant();
        PerformanceSummary summary = performanceCalculator.calculate(accountId, strategyTag, periodStart, periodEnd, trades);
        String hashHex = hashService.sha256Hex(summary);
        double winRate = performanceCalculator.computeWinRate(trades).doubleValue();
        int tradeCount = trades.size();
        boolean verified = false;
        return new PerformanceResponse(summary, hashHex, null, winRate, tradeCount, verified);
    }

    /**
     * 백엔드 원장 기준 커밋 목록 조회. accountId 없으면 전체(최신순).
     */
    @GetMapping("/performance/commits")
    public List<CommitListItem> getCommits(
            @RequestParam(required = false) String accountId,
            @RequestParam(defaultValue = "50") int limit) {
        List<PerformanceCommit> commits = accountId != null && !accountId.isBlank()
                ? performanceCommitRepository.findByAccountId(accountId, limit)
                : performanceCommitRepository.findAll(limit);
        return commits.stream().map(this::toListItem).collect(Collectors.toList());
    }

    /**
     * 성과 계산 후 해시를 온체인에 커밋하고 원장에 기록.
     */
    @PostMapping("/performance/commit")
    public ResponseEntity<PerformanceResponse> commitPerformance(@RequestBody CommitRequest request) {
        List<Trade> trades = tradeRepository.findByAccountAndPeriod(
                request.accountId(),
                request.start(),
                request.end());
        if (request.strategyTag() != null && !request.strategyTag().isBlank()) {
            trades = trades.stream().filter(t -> request.strategyTag().equals(t.getStrategyTag())).toList();
        }
        Instant periodStart = request.start().atZone(ZoneId.systemDefault()).toInstant();
        Instant periodEnd = request.end().atZone(ZoneId.systemDefault()).toInstant();
        PerformanceSummary summary = performanceCalculator.calculate(
                request.accountId(), request.strategyTag(), periodStart, periodEnd, trades);
        String hashHex = hashService.sha256Hex(summary);
        String txHash = blockchainService.commitPerformance(hashHex, periodStart.getEpochSecond(), periodEnd.getEpochSecond());

        double winRate = performanceCalculator.computeWinRate(trades).doubleValue();
        int tradeCount = trades.size();
        boolean verified = txHash != null && !txHash.isBlank();

        PerformanceCommit commit = PerformanceCommit.builder()
                .id(null)
                .accountId(request.accountId())
                .strategyTag(request.strategyTag() != null ? request.strategyTag() : "")
                .periodStartEpoch(periodStart.getEpochSecond())
                .periodEndEpoch(periodEnd.getEpochSecond())
                .totalPnl(summary.getTotalPnl())
                .maxDrawdown(summary.getMaxDrawdown())
                .sharpeRatio(summary.getSharpeRatio())
                .winRate(performanceCalculator.computeWinRate(trades))
                .tradeCount(tradeCount)
                .hashHex(hashHex)
                .txHash(txHash)
                .createdAt(LocalDateTime.now())
                .build();
        performanceCommitRepository.save(commit);

        return ResponseEntity.ok(new PerformanceResponse(summary, hashHex, txHash, winRate, tradeCount, verified));
    }

    private CommitListItem toListItem(PerformanceCommit c) {
        return new CommitListItem(
                c.getId(),
                c.getAccountId(),
                Instant.ofEpochSecond(c.getPeriodStartEpoch()),
                Instant.ofEpochSecond(c.getPeriodEndEpoch()),
                c.getTotalPnl().doubleValue(),
                c.getMaxDrawdown().doubleValue(),
                c.getSharpeRatio().doubleValue(),
                c.getWinRate().doubleValue(),
                c.getTradeCount(),
                c.getHashHex(),
                c.getTxHash(),
                c.getCreatedAt().atZone(ZoneId.systemDefault()).toInstant().toEpochMilli(),
                c.getTxHash() != null && !c.getTxHash().isBlank()
        );
    }

    public record PerformanceResponse(
            PerformanceSummary summary,
            String hashHex,
            String txHash,
            double winRate,
            int tradeCount,
            boolean verified) {}

    public record CommitListItem(
            Long id,
            String trader,
            Instant periodStart,
            Instant periodEnd,
            double totalPnl,
            double maxDrawdown,
            double sharpeRatio,
            double winRate,
            int tradeCount,
            String hash,
            String txHash,
            long timestamp,
            boolean verified) {}

    public record CommitRequest(
            String accountId,
            @DateTimeFormat(iso = DateTimeFormat.ISO.DATE_TIME) LocalDateTime start,
            @DateTimeFormat(iso = DateTimeFormat.ISO.DATE_TIME) LocalDateTime end,
            String strategyTag) {}
}
