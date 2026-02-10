package com.contractreport.performance.repository;

import com.contractreport.performance.domain.KiwoomAccountLink;
import org.springframework.jdbc.core.JdbcTemplate;
import org.springframework.jdbc.core.RowMapper;
import org.springframework.jdbc.support.GeneratedKeyHolder;
import org.springframework.stereotype.Repository;

import java.time.LocalDateTime;
import java.util.List;
import java.util.Optional;

@Repository
public class KiwoomAccountLinkRepository {

    private final JdbcTemplate jdbc;

    private static final RowMapper<KiwoomAccountLink> ROW_MAPPER = (rs, rowNum) -> KiwoomAccountLink.builder()
            .id(rs.getLong("id"))
            .userId(rs.getString("user_id"))
            .kiwoomAccountNo(rs.getString("kiwoom_account_no"))
            .ourAccountId(rs.getString("our_account_id"))
            .createdAt(rs.getObject("created_at", LocalDateTime.class))
            .build();

    public KiwoomAccountLinkRepository(JdbcTemplate jdbc) {
        this.jdbc = jdbc;
    }

    public KiwoomAccountLink save(KiwoomAccountLink link) {
        if (link.getId() != null) {
            jdbc.update("""
                    UPDATE kiwoom_account_links SET user_id=?, kiwoom_account_no=?, our_account_id=? WHERE id=?
                    """, link.getUserId(), link.getKiwoomAccountNo(), link.getOurAccountId(), link.getId());
            return link;
        }
        GeneratedKeyHolder keyHolder = new GeneratedKeyHolder();
        jdbc.update(con -> {
            var ps = con.prepareStatement("""
                    INSERT INTO kiwoom_account_links (user_id, kiwoom_account_no, our_account_id)
                    VALUES (?, ?, ?)
                    """, java.sql.Statement.RETURN_GENERATED_KEYS);
            ps.setString(1, link.getUserId());
            ps.setString(2, link.getKiwoomAccountNo());
            ps.setString(3, link.getOurAccountId());
            return ps;
        }, keyHolder);
        Number key = keyHolder.getKey();
        if (key == null) return link;
        return KiwoomAccountLink.builder()
                .id(key.longValue())
                .userId(link.getUserId())
                .kiwoomAccountNo(link.getKiwoomAccountNo())
                .ourAccountId(link.getOurAccountId())
                .createdAt(link.getCreatedAt() != null ? link.getCreatedAt() : LocalDateTime.now())
                .build();
    }

    public List<KiwoomAccountLink> findByUserId(String userId) {
        return jdbc.query("""
                SELECT id, user_id, kiwoom_account_no, our_account_id, created_at
                FROM kiwoom_account_links WHERE user_id = ? ORDER BY created_at DESC
                """, ROW_MAPPER, userId);
    }

    public Optional<KiwoomAccountLink> findByUserIdAndKiwoomAccountNo(String userId, String kiwoomAccountNo) {
        List<KiwoomAccountLink> list = jdbc.query("""
                SELECT id, user_id, kiwoom_account_no, our_account_id, created_at
                FROM kiwoom_account_links WHERE user_id = ? AND kiwoom_account_no = ?
                """, ROW_MAPPER, userId, kiwoomAccountNo);
        return list.isEmpty() ? Optional.empty() : Optional.of(list.get(0));
    }

    public Optional<KiwoomAccountLink> findByUserIdAndOurAccountId(String userId, String ourAccountId) {
        List<KiwoomAccountLink> list = jdbc.query("""
                SELECT id, user_id, kiwoom_account_no, our_account_id, created_at
                FROM kiwoom_account_links WHERE user_id = ? AND our_account_id = ?
                """, ROW_MAPPER, userId, ourAccountId);
        return list.isEmpty() ? Optional.empty() : Optional.of(list.get(0));
    }
}
