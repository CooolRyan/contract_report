// SPDX-License-Identifier: MIT
pragma solidity ^0.8.24;

import {Script, console} from "forge-std/Script.sol";
import {PerformanceRegistry} from "../src/PerformanceRegistry.sol";

contract DeployScript is Script {
    function run() external {
        uint256 deployerPrivateKey = vm.envUint("PRIVATE_KEY");
        vm.startBroadcast(deployerPrivateKey);
        PerformanceRegistry registry = new PerformanceRegistry();
        console.log("PerformanceRegistry deployed at:", address(registry));
        vm.stopBroadcast();
    }
}
