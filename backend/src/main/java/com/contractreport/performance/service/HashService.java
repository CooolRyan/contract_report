package com.contractreport.performance.service;

import com.contractreport.performance.domain.PerformanceSummary;
import com.fasterxml.jackson.core.JsonProcessingException;
import com.fasterxml.jackson.databind.ObjectMapper;
import com.fasterxml.jackson.databind.SerializationFeature;
import org.springframework.stereotype.Service;

import java.nio.charset.StandardCharsets;
import java.security.MessageDigest;
import java.security.NoSuchAlgorithmException;
import java.util.HexFormat;

/**
 * PerformanceSummary를 정규 JSON으로 직렬화 후 SHA-256 해시 반환.
 */
@Service
public class HashService {

    private final ObjectMapper objectMapper;

    public HashService(ObjectMapper objectMapper) {
        this.objectMapper = objectMapper.copy()
                .enable(SerializationFeature.ORDER_MAP_ENTRIES_BY_KEYS);
    }

    public byte[] sha256(PerformanceSummary summary) {
        try {
            String json = objectMapper.writeValueAsString(summary);
            MessageDigest digest = MessageDigest.getInstance("SHA-256");
            return digest.digest(json.getBytes(StandardCharsets.UTF_8));
        } catch (JsonProcessingException | NoSuchAlgorithmException e) {
            throw new RuntimeException("Hash computation failed", e);
        }
    }

    /** Solidity bytes32에 넣기 위한 32바이트 hex 문자열 (0x 접두사 없음). */
    public String sha256Hex(PerformanceSummary summary) {
        byte[] hash = sha256(summary);
        return HexFormat.of().formatHex(hash);
    }
}
