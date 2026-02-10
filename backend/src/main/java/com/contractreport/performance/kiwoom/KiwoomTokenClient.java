package com.contractreport.performance.kiwoom;

import com.contractreport.performance.config.KiwoomProperties;
import com.fasterxml.jackson.databind.JsonNode;
import com.fasterxml.jackson.databind.ObjectMapper;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.http.*;
import org.springframework.stereotype.Component;
import org.springframework.web.client.RestTemplate;

import java.time.LocalDateTime;
import java.time.format.DateTimeFormatter;
import java.util.Map;

/**
 * 키움 OAuth2 Client Credentials 토큰 발급 및 캐시.
 * 토큰 유효기간 24시간, expires_dt 직전에 재발급하도록 갱신.
 */
@Component
public class KiwoomTokenClient {

    private static final Logger log = LoggerFactory.getLogger(KiwoomTokenClient.class);
    private static final DateTimeFormatter EXPIRES_FORMAT = DateTimeFormatter.ofPattern("yyyyMMddHHmmss");

    private final KiwoomProperties properties;
    private final RestTemplate restTemplate;
    private final ObjectMapper objectMapper;

    private volatile String cachedToken;
    private volatile LocalDateTime tokenExpiresAt;

    public KiwoomTokenClient(KiwoomProperties properties, RestTemplate restTemplate, ObjectMapper objectMapper) {
        this.properties = properties;
        this.restTemplate = restTemplate;
        this.objectMapper = objectMapper;
    }

    /**
     * 유효한 접근토큰 반환. 만료 5분 전이면 재발급.
     */
    public String getAccessToken() {
        if (cachedToken != null && tokenExpiresAt != null && LocalDateTime.now().plusMinutes(5).isBefore(tokenExpiresAt)) {
            return cachedToken;
        }
        synchronized (this) {
            if (cachedToken != null && tokenExpiresAt != null && LocalDateTime.now().plusMinutes(5).isBefore(tokenExpiresAt)) {
                return cachedToken;
            }
            fetchAndCacheToken();
            return cachedToken;
        }
    }

    private void fetchAndCacheToken() {
        if (!properties.isConfigured()) {
            log.warn("Kiwoom appkey/secretkey not configured. Token not requested.");
            cachedToken = null;
            tokenExpiresAt = null;
            return;
        }
        String url = properties.getBaseUrl().replaceAll("/$", "") + "/oauth2/token";
        HttpHeaders headers = new HttpHeaders();
        headers.setContentType(MediaType.APPLICATION_JSON);
        Map<String, String> body = Map.of(
                "grant_type", "client_credentials",
                "appkey", properties.getAppkey(),
                "secretkey", properties.getSecretkey()
        );
        try {
            ResponseEntity<String> response = restTemplate.exchange(
                    url,
                    HttpMethod.POST,
                    new HttpEntity<>(body, headers),
                    String.class
            );
            if (response.getStatusCode().is2xxSuccessful() && response.getBody() != null) {
                JsonNode node = objectMapper.readTree(response.getBody());
                int returnCode = node.path("return_code").asInt(1);
                if (returnCode == 0) {
                    cachedToken = node.path("token").asText(null);
                    String expiresDt = node.path("expires_dt").asText("");
                    if (!expiresDt.isEmpty()) {
                        tokenExpiresAt = LocalDateTime.parse(expiresDt, EXPIRES_FORMAT);
                    } else {
                        tokenExpiresAt = LocalDateTime.now().plusHours(23);
                    }
                    log.info("Kiwoom access token refreshed, expires at {}", tokenExpiresAt);
                } else {
                    log.error("Kiwoom token response error: return_code={}, msg={}", returnCode, node.path("return_msg").asText());
                    cachedToken = null;
                }
            } else {
                log.error("Kiwoom token request failed: status={}", response.getStatusCode());
                cachedToken = null;
            }
        } catch (Exception e) {
            log.error("Kiwoom token request failed", e);
            cachedToken = null;
            tokenExpiresAt = null;
        }
    }
}
