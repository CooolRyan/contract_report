// SPDX-License-Identifier: MIT
pragma solidity ^0.8.24;

/**
 * @title PerformanceRegistry
 * @notice 트레이더가 기간별 성과 요약의 해시를 커밋·조회하는 레지스트리.
 *         오프체인에서 계산한 JSON 요약의 SHA-256 해시만 온체인에 기록.
 */
contract PerformanceRegistry {
    struct Performance {
        bytes32 hash;
        uint64 periodStart;
        uint64 periodEnd;
    }

    /// trader => (periodStart, periodEnd) => Performance
    mapping(address => mapping(bytes32 => Performance)) private _performances;

    event PerformanceCommitted(
        address indexed trader,
        bytes32 indexed hash,
        uint64 periodStart,
        uint64 periodEnd
    );

    /**
     * @notice 성과 해시를 기간과 함께 커밋. 호출자 = trader.
     * @param hash 오프체인 성과 요약 JSON의 SHA-256 해시 (32 bytes)
     * @param periodStart 기간 시작 Unix timestamp (초)
     * @param periodEnd 기간 종료 Unix timestamp (초)
     */
    function commitPerformance(
        bytes32 hash,
        uint64 periodStart,
        uint64 periodEnd
    ) external {
        require(periodStart < periodEnd, "Invalid period");
        bytes32 key = _key(periodStart, periodEnd);
        _performances[msg.sender][key] = Performance({
            hash: hash,
            periodStart: periodStart,
            periodEnd: periodEnd
        });
        emit PerformanceCommitted(msg.sender, hash, periodStart, periodEnd);
    }

    /**
     * @notice 특정 트레이더·기간의 성과 레코드 조회
     */
    function getPerformance(
        address trader,
        uint64 periodStart,
        uint64 periodEnd
    ) external view returns (Performance memory) {
        bytes32 key = _key(periodStart, periodEnd);
        return _performances[trader][key];
    }

    /**
     * @notice 동일 기간 중복 커밋 방지: 이미 있으면 revert (선택)
     *         현재는 덮어쓰기 허용. 필요 시 commitPerformance 내부에서 체크.
     */
    function getPerformanceHash(
        address trader,
        uint64 periodStart,
        uint64 periodEnd
    ) external view returns (bytes32) {
        bytes32 key = _key(periodStart, periodEnd);
        return _performances[trader][key].hash;
    }

    function _key(uint64 periodStart, uint64 periodEnd) internal pure returns (bytes32) {
        return keccak256(abi.encodePacked(periodStart, periodEnd));
    }
}
