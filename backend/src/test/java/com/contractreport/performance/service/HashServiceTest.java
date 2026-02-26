package com.contractreport.performance.service;

import com.contractreport.performance.domain.PerformanceSummary;
import com.fasterxml.jackson.databind.ObjectMapper;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;

import java.math.BigDecimal;
import java.time.Instant;
import java.util.List;

import static org.junit.jupiter.api.Assertions.*;

class HashServiceTest {

    private HashService hashService;

    @BeforeEach
    void setUp() {
        hashService = new HashService(new ObjectMapper());
    }

    private PerformanceSummary buildSummary(String accountId, BigDecimal totalPnl) {
        return PerformanceSummary.builder()
                .accountId(accountId)
                .strategyTag("strategy1")
                .periodStart(Instant.parse("2024-01-01T00:00:00Z"))
                .periodEnd(Instant.parse("2024-01-31T23:59:59Z"))
                .totalPnl(totalPnl)
                .maxDrawdown(new BigDecimal("100.00"))
                .sharpeRatio(new BigDecimal("1.5000"))
                .equityCurveSampled(List.of(new BigDecimal("500"), new BigDecimal("1234.56")))
                .build();
    }

    // ──────────────── sha256Hex() ────────────────

    @Test
    void sha256Hex_returns64CharLowercaseHex() {
        String hex = hashService.sha256Hex(buildSummary("acc1", new BigDecimal("1234.56")));

        assertEquals(64, hex.length());
        assertTrue(hex.matches("[0-9a-f]{64}"), "Should be lowercase hex: " + hex);
    }

    @Test
    void sha256Hex_sameSummary_producesIdenticalHash() {
        PerformanceSummary s1 = buildSummary("acc1", new BigDecimal("1234.56"));
        PerformanceSummary s2 = buildSummary("acc1", new BigDecimal("1234.56"));

        assertEquals(hashService.sha256Hex(s1), hashService.sha256Hex(s2));
    }

    @Test
    void sha256Hex_differentAccountId_producesDifferentHash() {
        String h1 = hashService.sha256Hex(buildSummary("acc1", new BigDecimal("1000")));
        String h2 = hashService.sha256Hex(buildSummary("acc2", new BigDecimal("1000")));

        assertNotEquals(h1, h2);
    }

    @Test
    void sha256Hex_differentTotalPnl_producesDifferentHash() {
        String h1 = hashService.sha256Hex(buildSummary("acc1", new BigDecimal("100")));
        String h2 = hashService.sha256Hex(buildSummary("acc1", new BigDecimal("200")));

        assertNotEquals(h1, h2);
    }

    @Test
    void sha256Hex_emptyEquityCurve_doesNotThrow() {
        PerformanceSummary summary = PerformanceSummary.builder()
                .accountId("acc1").strategyTag("")
                .periodStart(Instant.EPOCH).periodEnd(Instant.EPOCH)
                .totalPnl(BigDecimal.ZERO).maxDrawdown(BigDecimal.ZERO)
                .sharpeRatio(BigDecimal.ZERO)
                .equityCurveSampled(List.of())
                .build();

        assertDoesNotThrow(() -> hashService.sha256Hex(summary));
    }

    // ──────────────── sha256() ────────────────

    @Test
    void sha256_returns32ByteArray() {
        byte[] hash = hashService.sha256(buildSummary("acc1", BigDecimal.TEN));

        assertEquals(32, hash.length);
    }

    @Test
    void sha256_sameSummary_identicalBytes() {
        PerformanceSummary s = buildSummary("acc1", new BigDecimal("999"));

        assertArrayEquals(hashService.sha256(s), hashService.sha256(s));
    }

    @Test
    void sha256_hexIsHexEncodingOfBytes() {
        PerformanceSummary s = buildSummary("acc1", new BigDecimal("1234.56"));
        byte[] bytes = hashService.sha256(s);
        String hex   = hashService.sha256Hex(s);

        // hex 문자열이 byte[] 를 올바르게 인코딩하는지 검증
        StringBuilder sb = new StringBuilder();
        for (byte b : bytes) {
            sb.append(String.format("%02x", b));
        }
        assertEquals(sb.toString(), hex);
    }
}
