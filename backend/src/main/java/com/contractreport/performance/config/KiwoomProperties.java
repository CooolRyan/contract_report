package com.contractreport.performance.config;

import org.springframework.boot.context.properties.ConfigurationProperties;
import org.springframework.stereotype.Component;

/**
 * 키움 REST API 설정. appkey, secretkey는 환경변수 또는 시크릿 저장소 사용 권장.
 */
@Component
@ConfigurationProperties(prefix = "kiwoom")
public class KiwoomProperties {

    /** 키움 개발자센터에서 발급한 앱키 */
    private String appkey = "";
    /** 키움 개발자센터에서 발급한 시크릿키 */
    private String secretkey = "";
    /** 운영: https://api.kiwoom.com, 모의: https://mockapi.kiwoom.com */
    private String baseUrl = "https://api.kiwoom.com";

    public String getAppkey() {
        return appkey;
    }

    public void setAppkey(String appkey) {
        this.appkey = appkey;
    }

    public String getSecretkey() {
        return secretkey;
    }

    public void setSecretkey(String secretkey) {
        this.secretkey = secretkey;
    }

    public String getBaseUrl() {
        return baseUrl;
    }

    public void setBaseUrl(String baseUrl) {
        this.baseUrl = baseUrl;
    }

    public boolean isConfigured() {
        return appkey != null && !appkey.isBlank() && secretkey != null && !secretkey.isBlank();
    }
}
