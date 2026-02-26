package com.contractreport.performance.service;

import org.junit.jupiter.api.Test;

import static org.junit.jupiter.api.Assertions.*;

class BlockchainServiceTest {

    // ──────────────── 미설정 시 IllegalStateException ────────────────

    @Test
    void commitPerformance_emptyContractAddress_throwsIllegalState() {
        BlockchainService service = new BlockchainService("https://rpc.sepolia.org", "", "someKey");
        assertThrows(IllegalStateException.class,
                () -> service.commitPerformance("deadbeef", 1_000_000L, 2_000_000L));
    }

    @Test
    void commitPerformance_blankContractAddress_throwsIllegalState() {
        BlockchainService service = new BlockchainService("https://rpc.sepolia.org", "   ", "someKey");
        assertThrows(IllegalStateException.class,
                () -> service.commitPerformance("deadbeef", 1_000_000L, 2_000_000L));
    }

    @Test
    void commitPerformance_nullContractAddress_throwsIllegalState() {
        BlockchainService service = new BlockchainService("https://rpc.sepolia.org", null, "someKey");
        assertThrows(IllegalStateException.class,
                () -> service.commitPerformance("deadbeef", 1_000_000L, 2_000_000L));
    }

    @Test
    void commitPerformance_emptyPrivateKey_throwsIllegalState() {
        BlockchainService service = new BlockchainService("https://rpc.sepolia.org", "0xABCD", "");
        assertThrows(IllegalStateException.class,
                () -> service.commitPerformance("deadbeef", 1_000_000L, 2_000_000L));
    }

    @Test
    void commitPerformance_nullPrivateKey_throwsIllegalState() {
        BlockchainService service = new BlockchainService("https://rpc.sepolia.org", "0xABCD", null);
        assertThrows(IllegalStateException.class,
                () -> service.commitPerformance("deadbeef", 1_000_000L, 2_000_000L));
    }

    // ──────────────── Getter 검증 ────────────────

    @Test
    void getRpcUrl_returnsConfiguredValue() {
        BlockchainService service = new BlockchainService("https://rpc.test.org", "0xABC", "key");
        assertEquals("https://rpc.test.org", service.getRpcUrl());
    }

    @Test
    void getContractAddress_returnsConfiguredValue() {
        BlockchainService service = new BlockchainService("https://rpc.test.org", "0xContractAddr", "key");
        assertEquals("0xContractAddr", service.getContractAddress());
    }
}
