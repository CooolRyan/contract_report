package com.contractreport.performance.web;

import com.contractreport.performance.domain.KiwoomAccountLink;
import com.contractreport.performance.kiwoom.KiwoomTradeDto;
import com.contractreport.performance.service.KiwoomService;
import lombok.RequiredArgsConstructor;
import org.springframework.format.annotation.DateTimeFormat;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.*;

import java.time.LocalDateTime;
import java.util.List;
import java.util.stream.Collectors;

/**
 * 키움 계좌 연동·매매 조회·선택 등록 REST API.
 * userId는 프론트에서 지갑 주소 등으로 전달.
 */
@RestController
@RequestMapping("/api/kiwoom")
@RequiredArgsConstructor
public class KiwoomController {

    private final KiwoomService kiwoomService;

    /**
     * 키움 계좌 연동. 이미 연동된 경우 기존 연동 정보 반환.
     */
    @PostMapping("/link")
    public ResponseEntity<LinkResponse> linkAccount(@RequestBody LinkRequest request) {
        if (request.userId() == null || request.userId().isBlank() || request.kiwoomAccountNo() == null || request.kiwoomAccountNo().isBlank()) {
            return ResponseEntity.badRequest().build();
        }
        KiwoomAccountLink link = kiwoomService.linkAccount(request.userId(), request.kiwoomAccountNo());
        return ResponseEntity.ok(new LinkResponse(link.getId(), link.getUserId(), link.getKiwoomAccountNo(), link.getOurAccountId(), link.getCreatedAt().toString()));
    }

    /**
     * 내 연동 계좌 목록.
     */
    @GetMapping("/links")
    public List<LinkResponse> listLinks(@RequestParam String userId) {
        return kiwoomService.listLinks(userId).stream()
                .map(l -> new LinkResponse(l.getId(), l.getUserId(), l.getKiwoomAccountNo(), l.getOurAccountId(), l.getCreatedAt().toString()))
                .collect(Collectors.toList());
    }

    /**
     * 키움 API로 해당 연동 계좌의 매매/체결 내역 조회 (우리 DB가 아님).
     */
    @GetMapping("/trades")
    public List<KiwoomTradeDto> fetchTrades(
            @RequestParam String userId,
            @RequestParam String kiwoomAccountNo,
            @RequestParam @DateTimeFormat(iso = DateTimeFormat.ISO.DATE_TIME) LocalDateTime start,
            @RequestParam @DateTimeFormat(iso = DateTimeFormat.ISO.DATE_TIME) LocalDateTime end) {
        return kiwoomService.fetchTradesFromKiwoom(userId, kiwoomAccountNo, start, end);
    }

    /**
     * 키움에서 조회한 체결 중 선택한 항목을 우리 데이터(trades)에 등록.
     */
    @PostMapping("/register")
    public ResponseEntity<RegisterResponse> registerTrades(@RequestBody RegisterRequest request) {
        if (request.userId() == null || request.userId().isBlank() || request.kiwoomAccountNo() == null || request.kiwoomAccountNo().isBlank()
                || request.trades() == null || request.trades().isEmpty()) {
            return ResponseEntity.badRequest().build();
        }
        int count = kiwoomService.registerTrades(request.userId(), request.kiwoomAccountNo(), request.trades());
        return ResponseEntity.ok(new RegisterResponse(count));
    }

    public record LinkRequest(String userId, String kiwoomAccountNo) {}
    public record LinkResponse(Long id, String userId, String kiwoomAccountNo, String ourAccountId, String createdAt) {}
    public record RegisterRequest(String userId, String kiwoomAccountNo, List<KiwoomTradeDto> trades) {}
    public record RegisterResponse(int registeredCount) {}
}
