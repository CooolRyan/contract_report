package com.contractreport.performance.service;

import com.contractreport.performance.domain.KiwoomAccountLink;
import com.contractreport.performance.domain.Trade;
import com.contractreport.performance.kiwoom.KiwoomRestClient;
import com.contractreport.performance.kiwoom.KiwoomTradeDto;
import com.contractreport.performance.repository.KiwoomAccountLinkRepository;
import com.contractreport.performance.repository.TradeRepository;
import com.fasterxml.jackson.databind.JsonNode;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.extension.ExtendWith;
import org.mockito.ArgumentCaptor;
import org.mockito.InjectMocks;
import org.mockito.Mock;
import org.mockito.junit.jupiter.MockitoExtension;

import java.time.LocalDateTime;
import java.util.List;
import java.util.Optional;

import static org.junit.jupiter.api.Assertions.*;
import static org.mockito.ArgumentMatchers.*;
import static org.mockito.Mockito.*;

@ExtendWith(MockitoExtension.class)
class KiwoomServiceTest {

    @Mock KiwoomAccountLinkRepository linkRepository;
    @Mock KiwoomRestClient             kiwoomRestClient;
    @Mock TradeRepository              tradeRepository;

    @InjectMocks KiwoomService kiwoomService;

    // ──────────────── linkAccount() ────────────────

    @Test
    void linkAccount_existingLink_returnsExistingWithoutSaving() {
        KiwoomAccountLink existing = KiwoomAccountLink.builder()
                .id(1L).userId("user1").kiwoomAccountNo("acc123")
                .ourAccountId("kiwoom_user1_acc123").createdAt(LocalDateTime.now())
                .build();
        when(linkRepository.findByUserIdAndKiwoomAccountNo("user1", "acc123"))
                .thenReturn(Optional.of(existing));

        KiwoomAccountLink result = kiwoomService.linkAccount("user1", "acc123");

        assertSame(existing, result);
        verify(linkRepository, never()).save(any());
    }

    @Test
    void linkAccount_newShortId_savesWithPrefixedAccountId() {
        when(linkRepository.findByUserIdAndKiwoomAccountNo("u1", "a1")).thenReturn(Optional.empty());

        KiwoomAccountLink saved = KiwoomAccountLink.builder()
                .id(10L).userId("u1").kiwoomAccountNo("a1")
                .ourAccountId("kiwoom_u1_a1").createdAt(LocalDateTime.now())
                .build();
        when(linkRepository.save(any())).thenReturn(saved);

        KiwoomAccountLink result = kiwoomService.linkAccount("u1", "a1");

        assertEquals("kiwoom_u1_a1", result.getOurAccountId());
        verify(linkRepository).save(any());
    }

    @Test
    void linkAccount_longIdExceeds32Chars_generatesHashedId() {
        // "kiwoom_" + userId + "_" + kiwoomAccountNo → 36자 > 32
        String longUser = "verylonguser";
        String kiwoomNo = "1234567890123"; // 13자 → 총 "kiwoom_verylonguser_1234567890123" = 33자

        when(linkRepository.findByUserIdAndKiwoomAccountNo(longUser, kiwoomNo))
                .thenReturn(Optional.empty());
        when(linkRepository.save(any())).thenAnswer(inv -> inv.getArgument(0));

        KiwoomAccountLink result = kiwoomService.linkAccount(longUser, kiwoomNo);

        assertTrue(result.getOurAccountId().startsWith("k_"),
                "32자 초과 시 'k_' + hashCode 형식이어야 합니다: " + result.getOurAccountId());
    }

    @Test
    void linkAccount_ourAccountIdMaxLength() {
        // ourAccountId 가 정확히 32자 이내여야 함
        String userId   = "short";
        String kiwoomNo = "123";

        when(linkRepository.findByUserIdAndKiwoomAccountNo(userId, kiwoomNo)).thenReturn(Optional.empty());
        when(linkRepository.save(any())).thenAnswer(inv -> inv.getArgument(0));

        KiwoomAccountLink result = kiwoomService.linkAccount(userId, kiwoomNo);

        assertTrue(result.getOurAccountId().length() <= 32,
                "ourAccountId 는 32자 이하여야 합니다: " + result.getOurAccountId());
    }

    // ──────────────── listLinks() ────────────────

    @Test
    void listLinks_delegatesToRepository() {
        List<KiwoomAccountLink> links = List.of(
                KiwoomAccountLink.builder().id(1L).userId("user1").kiwoomAccountNo("a1")
                        .ourAccountId("oa1").createdAt(LocalDateTime.now()).build()
        );
        when(linkRepository.findByUserId("user1")).thenReturn(links);

        List<KiwoomAccountLink> result = kiwoomService.listLinks("user1");

        assertEquals(links, result);
        verify(linkRepository).findByUserId("user1");
    }

    // ──────────────── fetchTradesFromKiwoom() ────────────────

    @Test
    void fetchTradesFromKiwoom_noLink_returnsEmpty() {
        when(linkRepository.findByUserIdAndKiwoomAccountNo("user1", "acc123"))
                .thenReturn(Optional.empty());

        List<KiwoomTradeDto> result = kiwoomService.fetchTradesFromKiwoom(
                "user1", "acc123",
                LocalDateTime.parse("2024-01-01T00:00:00"),
                LocalDateTime.parse("2024-01-01T23:59:59"));

        assertTrue(result.isEmpty());
        verifyNoInteractions(kiwoomRestClient);
    }

    @Test
    void fetchTradesFromKiwoom_withLink_returnsKiwoomApiResult() {
        KiwoomAccountLink link = KiwoomAccountLink.builder()
                .id(1L).userId("user1").kiwoomAccountNo("acc123")
                .ourAccountId("ourAcc123").createdAt(LocalDateTime.now())
                .build();
        when(linkRepository.findByUserIdAndKiwoomAccountNo("user1", "acc123"))
                .thenReturn(Optional.of(link));

        KiwoomTradeDto dto = KiwoomTradeDto.builder()
                .accountNo("acc123").symbol("AAPL").side("BUY")
                .qty("10").price("100").orderId("o1").execId("e1")
                .tradeDateTime("2024-01-01T09:00:00").fee("5")
                .strategyTag(null)
                .build();

        JsonNode mockNode = mock(JsonNode.class);
        when(kiwoomRestClient.fetchOrderExecutions(eq("acc123"), any(), any())).thenReturn(mockNode);
        when(kiwoomRestClient.parseTradesFromResponse(mockNode, "acc123")).thenReturn(List.of(dto));

        List<KiwoomTradeDto> result = kiwoomService.fetchTradesFromKiwoom(
                "user1", "acc123",
                LocalDateTime.parse("2024-01-01T00:00:00"),
                LocalDateTime.parse("2024-01-01T23:59:59"));

        assertEquals(1, result.size());
        assertEquals(dto, result.get(0));
    }

    // ──────────────── registerTrades() ────────────────

    @Test
    void registerTrades_nullTrades_returnsZero() {
        int count = kiwoomService.registerTrades("user1", "acc123", null);
        assertEquals(0, count);
        verifyNoInteractions(linkRepository);
    }

    @Test
    void registerTrades_emptyTrades_returnsZero() {
        int count = kiwoomService.registerTrades("user1", "acc123", List.of());
        assertEquals(0, count);
        verifyNoInteractions(linkRepository);
    }

    @Test
    void registerTrades_noLink_returnsZero() {
        when(linkRepository.findByUserIdAndKiwoomAccountNo("user1", "acc123"))
                .thenReturn(Optional.empty());

        KiwoomTradeDto dto = KiwoomTradeDto.builder()
                .accountNo("acc123").symbol("AAPL").side("BUY").qty("10").price("100")
                .orderId("o1").execId("e1").tradeDateTime("2024-01-01T09:00:00").fee("5")
                .strategyTag(null)
                .build();

        int count = kiwoomService.registerTrades("user1", "acc123", List.of(dto));

        assertEquals(0, count);
        verifyNoInteractions(tradeRepository);
    }

    @Test
    void registerTrades_withLink_savesTradesAndReturnsCount() {
        KiwoomAccountLink link = KiwoomAccountLink.builder()
                .id(1L).userId("user1").kiwoomAccountNo("acc123")
                .ourAccountId("ourAcc123").createdAt(LocalDateTime.now())
                .build();
        when(linkRepository.findByUserIdAndKiwoomAccountNo("user1", "acc123"))
                .thenReturn(Optional.of(link));

        KiwoomTradeDto dto1 = KiwoomTradeDto.builder()
                .accountNo("acc123").symbol("AAPL").side("BUY").qty("10").price("100")
                .orderId("o1").execId("e1").tradeDateTime("2024-01-01T09:00:00").fee("5")
                .strategyTag(null)
                .build();
        KiwoomTradeDto dto2 = KiwoomTradeDto.builder()
                .accountNo("acc123").symbol("AAPL").side("SELL").qty("10").price("110")
                .orderId("o2").execId("e2").tradeDateTime("2024-01-02T09:00:00").fee("5")
                .strategyTag(null)
                .build();

        int count = kiwoomService.registerTrades("user1", "acc123", List.of(dto1, dto2));

        assertEquals(2, count);

        @SuppressWarnings("unchecked")
        ArgumentCaptor<List<Trade>> captor = ArgumentCaptor.forClass(List.class);
        verify(tradeRepository).saveAll(captor.capture());
        assertEquals(2, captor.getValue().size());
    }

    @Test
    void registerTrades_mapsOurAccountId() {
        KiwoomAccountLink link = KiwoomAccountLink.builder()
                .id(1L).userId("user1").kiwoomAccountNo("acc123")
                .ourAccountId("MAPPED_ID").createdAt(LocalDateTime.now())
                .build();
        when(linkRepository.findByUserIdAndKiwoomAccountNo("user1", "acc123"))
                .thenReturn(Optional.of(link));

        KiwoomTradeDto dto = KiwoomTradeDto.builder()
                .accountNo("acc123").symbol("AAPL").side("BUY").qty("10").price("100")
                .orderId("o1").execId("e1").tradeDateTime("2024-01-01T09:00:00").fee("0")
                .strategyTag(null)
                .build();

        kiwoomService.registerTrades("user1", "acc123", List.of(dto));

        @SuppressWarnings("unchecked")
        ArgumentCaptor<List<Trade>> captor = ArgumentCaptor.forClass(List.class);
        verify(tradeRepository).saveAll(captor.capture());

        assertEquals("MAPPED_ID", captor.getValue().get(0).getAccountId());
    }

    @Test
    void registerTrades_invalidTradeDateTime_usesNow() {
        KiwoomAccountLink link = KiwoomAccountLink.builder()
                .id(1L).userId("user1").kiwoomAccountNo("acc123")
                .ourAccountId("ourAcc").createdAt(LocalDateTime.now())
                .build();
        when(linkRepository.findByUserIdAndKiwoomAccountNo("user1", "acc123"))
                .thenReturn(Optional.of(link));

        KiwoomTradeDto dto = KiwoomTradeDto.builder()
                .accountNo("acc123").symbol("AAPL").side("BUY").qty("1").price("50")
                .orderId("o1").execId("e1")
                .tradeDateTime("INVALID_DATE") // 파싱 불가
                .fee("0")
                .strategyTag(null)
                .build();

        // 예외 없이 처리돼야 함
        assertDoesNotThrow(() -> kiwoomService.registerTrades("user1", "acc123", List.of(dto)));
    }
}
