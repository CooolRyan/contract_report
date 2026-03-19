package com.contractreport.performance.web;

import com.contractreport.performance.domain.KiwoomAccountLink;
import com.contractreport.performance.kiwoom.KiwoomTradeDto;
import com.contractreport.performance.service.KiwoomService;
import org.junit.jupiter.api.Test;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.boot.test.autoconfigure.web.servlet.WebMvcTest;
import org.springframework.boot.test.mock.mockito.MockBean;
import org.springframework.http.MediaType;
import org.springframework.test.web.servlet.MockMvc;

import java.time.LocalDateTime;
import java.util.List;

import static org.mockito.ArgumentMatchers.*;
import static org.mockito.Mockito.*;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.*;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.*;

@WebMvcTest(KiwoomController.class)
class KiwoomControllerTest {

    @Autowired MockMvc mockMvc;

    @MockBean KiwoomService kiwoomService;

    // ──────────────── POST /api/kiwoom/link ────────────────

    @Test
    void linkAccount_validRequest_returns200WithLinkInfo() throws Exception {
        KiwoomAccountLink link = KiwoomAccountLink.builder()
                .id(1L).userId("user1").kiwoomAccountNo("acc123")
                .ourAccountId("kiwoom_user1_acc123")
                .createdAt(LocalDateTime.parse("2024-01-01T00:00:00"))
                .build();
        when(kiwoomService.linkAccount("user1", "acc123")).thenReturn(link);

        mockMvc.perform(post("/api/kiwoom/link")
                        .contentType(MediaType.APPLICATION_JSON)
                        .content("""
                                {"userId": "user1", "kiwoomAccountNo": "acc123"}
                                """))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$.id").value(1))
                .andExpect(jsonPath("$.userId").value("user1"))
                .andExpect(jsonPath("$.kiwoomAccountNo").value("acc123"))
                .andExpect(jsonPath("$.ourAccountId").value("kiwoom_user1_acc123"));
    }

    @Test
    void linkAccount_emptyUserId_returns400() throws Exception {
        mockMvc.perform(post("/api/kiwoom/link")
                        .contentType(MediaType.APPLICATION_JSON)
                        .content("""
                                {"userId": "", "kiwoomAccountNo": "acc123"}
                                """))
                .andExpect(status().isBadRequest());

        verifyNoInteractions(kiwoomService);
    }

    @Test
    void linkAccount_nullUserId_returns400() throws Exception {
        mockMvc.perform(post("/api/kiwoom/link")
                        .contentType(MediaType.APPLICATION_JSON)
                        .content("""
                                {"userId": null, "kiwoomAccountNo": "acc123"}
                                """))
                .andExpect(status().isBadRequest());

        verifyNoInteractions(kiwoomService);
    }

    @Test
    void linkAccount_emptyKiwoomAccountNo_returns400() throws Exception {
        mockMvc.perform(post("/api/kiwoom/link")
                        .contentType(MediaType.APPLICATION_JSON)
                        .content("""
                                {"userId": "user1", "kiwoomAccountNo": ""}
                                """))
                .andExpect(status().isBadRequest());

        verifyNoInteractions(kiwoomService);
    }

    // ──────────────── GET /api/kiwoom/links ────────────────

    @Test
    void listLinks_returnsLinksForUser() throws Exception {
        KiwoomAccountLink link = KiwoomAccountLink.builder()
                .id(1L).userId("user1").kiwoomAccountNo("acc123")
                .ourAccountId("oa1").createdAt(LocalDateTime.parse("2024-01-01T00:00:00"))
                .build();
        when(kiwoomService.listLinks("user1")).thenReturn(List.of(link));

        mockMvc.perform(get("/api/kiwoom/links").param("userId", "user1"))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$.length()").value(1))
                .andExpect(jsonPath("$[0].userId").value("user1"))
                .andExpect(jsonPath("$[0].kiwoomAccountNo").value("acc123"));
    }

    @Test
    void listLinks_noLinks_returnsEmptyArray() throws Exception {
        when(kiwoomService.listLinks("user1")).thenReturn(List.of());

        mockMvc.perform(get("/api/kiwoom/links").param("userId", "user1"))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$.length()").value(0));
    }

    // ──────────────── GET /api/kiwoom/trades ────────────────

    @Test
    void fetchTrades_returnsKiwoomTrades() throws Exception {
        KiwoomTradeDto dto = KiwoomTradeDto.builder()
                .accountNo("acc123").symbol("AAPL").side("BUY")
                .qty("10").price("100").orderId("o1").execId("e1")
                .tradeDateTime("2024-01-10T09:00:00").fee("5")
<<<<<<< HEAD
                .strategyTag(null)
=======
>>>>>>> feat/unit-tests
                .build();
        when(kiwoomService.fetchTradesFromKiwoom(eq("user1"), eq("acc123"), any(), any()))
                .thenReturn(List.of(dto));

        mockMvc.perform(get("/api/kiwoom/trades")
                        .param("userId",          "user1")
                        .param("kiwoomAccountNo", "acc123")
                        .param("start",           "2024-01-01T00:00:00")
                        .param("end",             "2024-01-31T23:59:59"))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$.length()").value(1))
                .andExpect(jsonPath("$[0].symbol").value("AAPL"))
                .andExpect(jsonPath("$[0].side").value("BUY"));
    }

    @Test
    void fetchTrades_noData_returnsEmptyArray() throws Exception {
        when(kiwoomService.fetchTradesFromKiwoom(any(), any(), any(), any()))
                .thenReturn(List.of());

        mockMvc.perform(get("/api/kiwoom/trades")
                        .param("userId",          "user1")
                        .param("kiwoomAccountNo", "acc123")
                        .param("start",           "2024-01-01T00:00:00")
                        .param("end",             "2024-01-31T23:59:59"))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$.length()").value(0));
    }

    // ──────────────── POST /api/kiwoom/register ────────────────

    @Test
    void registerTrades_validRequest_returnsRegisteredCount() throws Exception {
        when(kiwoomService.registerTrades(eq("user1"), eq("acc123"), any())).thenReturn(2);

        mockMvc.perform(post("/api/kiwoom/register")
                        .contentType(MediaType.APPLICATION_JSON)
                        .content("""
                                {
                                  "userId": "user1",
                                  "kiwoomAccountNo": "acc123",
                                  "trades": [
                                    {
                                      "accountNo": "acc123",
                                      "symbol": "AAPL",
                                      "side": "BUY",
                                      "qty": "10",
                                      "price": "100",
                                      "orderId": "o1",
                                      "execId": "e1",
                                      "tradeDateTime": "2024-01-10T09:00:00",
                                      "fee": "5"
                                    }
                                  ]
                                }
                                """))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$.registeredCount").value(2));
    }

    @Test
    void registerTrades_emptyUserId_returns400() throws Exception {
        mockMvc.perform(post("/api/kiwoom/register")
                        .contentType(MediaType.APPLICATION_JSON)
                        .content("""
                                {
                                  "userId": "",
                                  "kiwoomAccountNo": "acc123",
                                  "trades": [{"accountNo":"acc123","symbol":"AAPL","side":"BUY","qty":"1","price":"100","orderId":"o1","execId":"e1","tradeDateTime":"2024-01-10T09:00:00","fee":"0"}]
                                }
                                """))
                .andExpect(status().isBadRequest());

        verifyNoInteractions(kiwoomService);
    }

    @Test
    void registerTrades_emptyTradeList_returns400() throws Exception {
        mockMvc.perform(post("/api/kiwoom/register")
                        .contentType(MediaType.APPLICATION_JSON)
                        .content("""
                                {
                                  "userId": "user1",
                                  "kiwoomAccountNo": "acc123",
                                  "trades": []
                                }
                                """))
                .andExpect(status().isBadRequest());

        verifyNoInteractions(kiwoomService);
    }
}
