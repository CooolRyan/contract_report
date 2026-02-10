package com.contractreport.performance.repository;

import com.contractreport.performance.domain.Trade;
import org.springframework.jdbc.core.RowMapper;
import org.springframework.jdbc.core.JdbcTemplate;
import org.springframework.stereotype.Repository;

import java.math.BigDecimal;
import java.time.LocalDateTime;
import java.util.List;

/**
 * SQLite trades 테이블 조회. (Python Kiwoom 에이전트가 INSERT 담당)
 */
@Repository
public class TradeRepository {

    private final JdbcTemplate jdbc;

    private static final RowMapper<Trade> ROW_MAPPER = (rs, rowNum) -> Trade.builder()
            .id(rs.getLong("id"))
            .accountId(rs.getString("account_id"))
            .tradeDate(rs.getObject("trade_date", LocalDateTime.class))
            .symbol(rs.getString("symbol"))
            .side(rs.getString("side"))
            .qty(rs.getBigDecimal("qty"))
            .price(rs.getBigDecimal("price"))
            .fee(rs.getBigDecimal("fee") != null ? rs.getBigDecimal("fee") : BigDecimal.ZERO)
            .orderId(rs.getString("order_id"))
            .execId(rs.getString("exec_id"))
            .strategyTag(rs.getString("strategy_tag"))
            .build();

    public TradeRepository(JdbcTemplate jdbc) {
        this.jdbc = jdbc;
    }

    public List<Trade> findByAccountAndPeriod(String accountId, LocalDateTime start, LocalDateTime end) {
        String sql = """
                SELECT id, account_id, trade_date, symbol, side, qty, price, fee, order_id, exec_id, strategy_tag
                FROM trades
                WHERE account_id = ? AND trade_date >= ? AND trade_date <= ?
                ORDER BY trade_date
                """;
        return jdbc.query(sql, ROW_MAPPER, accountId, start, end);
    }

    /**
     * 키움에서 선택한 체결을 trades에 일괄 등록.
     */
    public void saveAll(List<Trade> trades) {
        if (trades == null || trades.isEmpty()) return;
        String sql = """
                INSERT INTO trades (account_id, trade_date, symbol, side, qty, price, fee, order_id, exec_id, strategy_tag)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """;
        for (Trade t : trades) {
            jdbc.update(sql,
                    t.getAccountId(),
                    t.getTradeDate(),
                    t.getSymbol(),
                    t.getSide(),
                    t.getQty(),
                    t.getPrice(),
                    t.getFee() != null ? t.getFee() : BigDecimal.ZERO,
                    t.getOrderId(),
                    t.getExecId(),
                    t.getStrategyTag());
        }
    }
}
