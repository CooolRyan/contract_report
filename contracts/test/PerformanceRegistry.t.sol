// SPDX-License-Identifier: MIT
pragma solidity ^0.8.24;

import {Test, console} from "forge-std/Test.sol";
import {PerformanceRegistry} from "../src/PerformanceRegistry.sol";

contract PerformanceRegistryTest is Test {
    PerformanceRegistry public registry;

    address public trader1;
    address public trader2;

    function setUp() public {
        registry = new PerformanceRegistry();
        trader1 = makeAddr("trader1");
        trader2 = makeAddr("trader2");
    }

    function test_CommitAndGet() public {
        vm.startPrank(trader1);
        bytes32 hash = keccak256("summary-json-hash");
        uint64 start = 1704067200; // 2024-01-01 00:00:00 UTC
        uint64 end = 1704153600;    // 2024-01-02 00:00:00 UTC

        vm.expectEmit(true, true, true, true);
        emit PerformanceRegistry.PerformanceCommitted(trader1, hash, start, end);
        registry.commitPerformance(hash, start, end);

        (bytes32 h, uint64 s, uint64 e) = registry.getPerformance(trader1, start, end);
        assertEq(h, hash);
        assertEq(s, start);
        assertEq(e, end);
        assertEq(registry.getPerformanceHash(trader1, start, end), hash);
        vm.stopPrank();
    }

    function test_RevertInvalidPeriod() public {
        vm.prank(trader1);
        vm.expectRevert("Invalid period");
        registry.commitPerformance(keccak256("x"), 100, 100);
    }

    function test_OverwriteSamePeriod() public {
        vm.startPrank(trader1);
        bytes32 hash1 = keccak256("first");
        bytes32 hash2 = keccak256("second");
        uint64 start = 1704067200;
        uint64 end = 1704153600;

        registry.commitPerformance(hash1, start, end);
        assertEq(registry.getPerformanceHash(trader1, start, end), hash1);

        registry.commitPerformance(hash2, start, end);
        assertEq(registry.getPerformanceHash(trader1, start, end), hash2);
        vm.stopPrank();
    }

    function test_IsolationPerTrader() public {
        bytes32 hash = keccak256("same");
        uint64 start = 1704067200;
        uint64 end = 1704153600;

        vm.prank(trader1);
        registry.commitPerformance(hash, start, end);

        vm.prank(trader2);
        registry.commitPerformance(keccak256("other"), start, end);

        assertEq(registry.getPerformanceHash(trader1, start, end), hash);
        assertEq(registry.getPerformanceHash(trader2, start, end), keccak256("other"));
    }
}
