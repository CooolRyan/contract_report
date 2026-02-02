package com.contractreport.performance.repository;

import com.contractreport.performance.domain.PerformanceCommit;
import org.springframework.jdbc.core.JdbcTemplate;
import org.springframework.jdbc.core.RowMapper;
import org.springframework.stereotype.Repository;

import java.math.BigDecimal;
import java.time.LocalDateTime;
import java.util.List;

@Repository
public class PerformanceCommitRepository {

    private final JdbcTemplate jdbc;

    private static final RowMapper<PerformanceCommit> ROW_MAPPER = (rs, rowNum) -> PerformanceCommit.builder()
            .id(rs.getLong("id"))
            .accountId(rs.getString("account_id"))
            .strategyTag(rs.getString("strategy_tag"))
            .periodStartEpoch(rs.getLong("period_start_epoch"))
            .periodEndEpoch(rs.getLong("period_end_epoch"))
            .totalPnl(rs.getBigDecimal("total_pnl"))
            .maxDrawdown(rs.getBigDecimal("max_drawdown"))
            .sharpeRatio(rs.getBigDecimal("sharpe_ratio"))
            .winRate(rs.getBigDecimal("win_rate"))
            .tradeCount(rs.getInt("trade_count"))
            .hashHex(rs.getString("hash_hex"))
            .txHash(rs.getString("tx_hash"))
            .createdAt(rs.getObject("created_at", LocalDateTime.class))
            .build();

    public PerformanceCommitRepository(JdbcTemplate jdbc) {
        this.jdbc = jdbc;
    }

    public void save(PerformanceCommit commit) {
        jdbc.update("""
                INSERT INTO performance_commits (account_id, strategy_tag, period_start_epoch, period_end_epoch,
                    total_pnl, max_drawdown, sharpe_ratio, win_rate, trade_count, hash_hex, tx_hash)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                commit.getAccountId(),
                commit.getStrategyTag(),
                commit.getPeriodStartEpoch(),
                commit.getPeriodEndEpoch(),
                commit.getTotalPnl(),
                commit.getMaxDrawdown(),
                commit.getSharpeRatio(),
                commit.getWinRate(),
                commit.getTradeCount(),
                commit.getHashHex(),
                commit.getTxHash());
    }

    public List<PerformanceCommit> findByAccountId(String accountId, int limit) {
        String sql = """
                SELECT id, account_id, strategy_tag, period_start_epoch, period_end_epoch,
                    total_pnl, max_drawdown, sharpe_ratio, win_rate, trade_count, hash_hex, tx_hash, created_at
                FROM performance_commits
                WHERE account_id = ?
                ORDER BY created_at DESC
                LIMIT ?
                """;
        return jdbc.query(sql, ROW_MAPPER, accountId, limit);
    }

    public List<PerformanceCommit> findAll(int limit) {
        String sql = """
                SELECT id, account_id, strategy_tag, period_start_epoch, period_end_epoch,
                    total_pnl, max_drawdown, sharpe_ratio, win_rate, trade_count, hash_hex, tx_hash, created_at
                FROM performance_commits
                ORDER BY created_at DESC
                LIMIT ?
                """;
        return jdbc.query(sql, ROW_MAPPER, limit);
    }
}
