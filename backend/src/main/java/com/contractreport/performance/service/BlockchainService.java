package com.contractreport.performance.service;

import org.springframework.beans.factory.annotation.Value;
import org.springframework.stereotype.Service;
import org.web3j.crypto.Credentials;
import org.web3j.protocol.Web3j;
import org.web3j.protocol.core.DefaultBlockParameterName;
import org.web3j.protocol.http.HttpService;
import org.web3j.tx.RawTransactionManager;
import org.web3j.tx.gas.DefaultGasProvider;

import java.math.BigInteger;

/**
 * EVM 체인과 연동: commitPerformance 호출 및 조회.
 * 실제 컨트랙트 ABI/주소는 설정에서 주입. (뼈대만 제공)
 */
@Service
public class BlockchainService {

    private final String rpcUrl;
    private final String contractAddress;
    private final String privateKey; // PoC용; 운영에서는 Vault/환경변수 등으로 분리

    public BlockchainService(
            @Value("${blockchain.rpc-url:https://rpc.sepolia.org}") String rpcUrl,
            @Value("${blockchain.contract-address:}") String contractAddress,
            @Value("${blockchain.private-key:}") String privateKey) {
        this.rpcUrl = rpcUrl;
        this.contractAddress = contractAddress;
        this.privateKey = privateKey;
    }

    /**
     * commitPerformance(hash, periodStart, periodEnd) 트랜잭션 전송.
     * 실제 구현 시 Web3j Contract 로드 후 호출.
     *
     * @param hashHex SHA-256 해시 32바이트 hex (0x 제거 가능)
     * @param periodStart Unix timestamp (초)
     * @param periodEnd   Unix timestamp (초)
     * @return 트랜잭션 해시 또는 null (미구성 시)
     */
    public String commitPerformance(String hashHex, long periodStart, long periodEnd) {
        if (contractAddress == null || contractAddress.isBlank() || privateKey == null || privateKey.isBlank()) {
            throw new IllegalStateException("blockchain.contract-address and blockchain.private-key must be set");
        }
        try {
            Web3j web3j = Web3j.build(new HttpService(rpcUrl));
            Credentials credentials = Credentials.create(privateKey);
            RawTransactionManager txManager = new RawTransactionManager(web3j, credentials, 11155111L); // Sepolia chainId

            // TODO: contracts 모듈에서 생성한 Java wrapper 사용
            // PerformanceRegistry contract = PerformanceRegistry.load(contractAddress, web3j, txManager, new DefaultGasProvider());
            // TransactionReceipt receipt = contract.commitPerformance(
            //     Numeric.toHexStringWithPrefix(Numeric.hexStringToByteArray(hashHex)),
            //     BigInteger.valueOf(periodStart),
            //     BigInteger.valueOf(periodEnd)
            // ).send();
            // return receipt.getTransactionHash();

            return "tx-hash-placeholder"; // 뼈대: 실제로는 위 주석 구현
        } catch (Exception e) {
            throw new RuntimeException("Blockchain commit failed", e);
        }
    }

    public String getRpcUrl() {
        return rpcUrl;
    }

    public String getContractAddress() {
        return contractAddress;
    }
}
