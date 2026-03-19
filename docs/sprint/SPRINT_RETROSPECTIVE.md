# SPRINT RETROSPECTIVE (자동 기록)

이 문서는 제가 프로젝트 파일을 수정할 때마다, “스프린트 회고” 형식으로 누적 기록하기 위한 용도입니다.
필요하면 다음 스프린트에서 같은 항목을 다시 적용(재현)할 수 있도록, 변경 이유와 실행/검증 커맨드까지 포함합니다.

---

## Sprint: 2026-02-02-1 (전략 자동 증명: strategyTag + 체결/커밋 연결)

### 목표
1. `quant-trader`가 생성한 체결을 Spring 백엔드에 자동 등록하고, 기간 성과를 온체인 커밋까지 연결
2. 전략 단위로 `strategyTag`가 체결 등록 → 성과 계산 → 커밋까지 이어지게 함

### 이번에 수정한 핵심 변경(무엇을/왜)
1. 백엔드: `strategyTag`가 `trades` 저장에 반영되도록 확장
   - `backend/src/main/java/.../kiwoom/KiwoomTradeDto`에 `strategyTag` 필드 추가
   - `KiwoomService.registerTrades()`에서 `Trade.strategyTag`를 `KiwoomTradeDto.strategyTag` 기반으로 저장
   - `KiwoomRestClient.parseTradesFromResponse()`는 `strategyTag=null` 기본값 유지
   - `KiwoomServiceTest`, `KiwoomControllerTest`에서 컴파일/런 안정화

2. quant-trader: 백엔드(스프링)와 “체결 등록 → 온체인 커밋” 연결
   - `quant-trader/core/contract_report_client.py` 추가
     - `POST /api/kiwoom/link`로 `ourAccountId` 확보
     - `POST /api/kiwoom/register`로 체결 1건씩 `trades` 등록(전략태그 포함)
     - `POST /api/performance/commit`으로 기간 성과를 온체인 커밋
     - `ourAccountId`는 반드시 link 응답 값을 사용(해시 함수 차이)
   - `quant-trader/core/engine.py`
     - 주문(체결) 직후 마지막 `TradeRecord`를 백엔드에 등록
   - `quant-trader/main.py`
     - CLI `commit` 모드 추가(커밋 요청)

### 배운점/리스크
1. `ourAccountId`는 “서버가 발급한 값”을 그대로 써야 함 (Java/Python hash 차이)
2. `trade` 실행 시 “체결 직후” 등록은 타이밍 이슈가 있을 수 있음(다중 체결/지연 시 보강 필요)

---

## Sprint: 2026-02-02-2 (클라우드 자동화: Docker/K8s/CI + 문서)

### 목표
1. K8s에서 `quant-trader`를 자동 실행할 수 있도록 배치/이미지 경로 준비
2. ArgoCD가 새 이미지 태그로 sync 되게 CI/CD 확장

### 이번에 수정한 핵심 변경(무엇을/왜)
1. `quant-trader/config.yaml`에 `contract_report` 설정 추가
2. `quant-trader/Dockerfile`, `.dockerignore` 추가
3. `quant-trader/docs/STRATEGY_CLOUD_AUTOMATION.md` 추가
4. K8s: `deploy/k8s-quant-trader-deployment.yaml` 추가
5. `.github/workflows/cd.yml`
   - `docker-push-quant-trader` 작업 추가
   - ArgoCD 매니페스트의 `deploy/k8s-quant-trader-deployment.yaml` 이미지 태그를 `sha-<commit>`으로 갱신

---

## Sprint: 2026-02-02-3 (장애/테스트 안정화: cp949 요구사항 + 단위 테스트)

### 목표
1. Windows에서 `pip install -r requirements-test.txt`가 깨지는 장애 제거
2. 최소 단위 테스트를 통해 연동 클라이언트의 핵심 payload/동작이 깨지지 않게 함

### 이번에 수정한 핵심 변경(무엇을/왜)
1. `quant-trader/requirements-test.txt`의 한글 주석을 ASCII/영문으로 변경
2. `quant-trader/tests/test_contract_report_client.py` 추가

### 검증 커맨드(재현용)
1. quant-trader 테스트
   - `cd quant-trader`
   - `.venv`가 있으면 `& .venv\\Scripts\\python.exe -m pytest -q tests/test_contract_report_client.py`

### 배운점/리스크
1. Windows에서 pip이 requirements 파일 인코딩을 cp949로 디코드하려는 상황이 발생할 수 있음 → requirements 주석은 ASCII/영문만 유지

---

## Sprint: 2026-03-19 (Terraform IaC 스캐폴딩: Private EKS + OpenVPN)

### 목표
1. `IaC/` 디렉토리 하위로 Terraform 코드 스캐폴딩을 생성
2. EKS는 private endpoint-only로 구성(`cluster_endpoint_public_access=false`, `cluster_endpoint_private_access=true`)
3. OpenVPN 서버를 public subnet에 배치하고, VPN 클라이언트 트래픽을 VPC로 라우팅/포워딩 + source NAT(masquerade) 적용
4. VPN 서버 SG에서 EKS API(443) 및 노드(NodePort/HTTP/HTTPS)에 접근 가능하도록 SG 룰 추가

### 이번에 수정한 핵심 변경(무엇을/왜)
1. 새 디렉토리 및 Terraform 파일 추가
   - `IaC/main.tf`, `IaC/variables.tf`, `IaC/providers.tf`, `IaC/outputs.tf`, `IaC/versions.tf`
   - `IaC/openvpn_userdata.sh.tpl`: OpenVPN 설치/PKI 생성/서버 라우팅 push/iptables NAT(masquerade)/클라이언트 `.ovpn` 생성
   - `IaC/README.md`: Apply 가이드 및 보안 주의사항 정리

2. SG/네트워크 구성 포인트
   - OpenVPN EC2에 `source_dest_check = false` 적용 (VPN 포워딩을 위해 필요)
   - VPN SG -> EKS cluster SG : `443/tcp` 허용
   - VPN SG -> 노드 SG : `80-443` + `NodePort 30000-32767` 범위 허용(ingress controller가 NodePort로 붙는 전제)

3. Git 컨플릭트(UNMERGED stage) 정리 + 레포 청소
   - `git status`의 `Unmerged paths`가 발생했는데, 해당 파일들에 대해 현재 작업 트리 버전으로 `git add` 처리해서 unmerged 상태를 해소
   - `quant-trader/__pycache__/*.pyc`가 커밋 대상에 올라오는 것을 막기 위해 `.gitignore`에 `quant-trader` pyc 규칙을 추가하고, 해당 pyc 파일은 `git rm --cached`로 인덱스에서 제거

### 검증 커맨드(재현용)
1. Terraform 초기화/적용
   - `cd IaC`
   - `terraform init`
   - `terraform apply`
2. OpenVPN 클라이언트 프로파일 확보
   - `terraform output -raw openvpn_public_ip`
   - SSH로 `/home/ubuntu/client-configs/client1.ovpn` 파일 가져오기

### 배운점/리스크
1. OpenVPN으로 “Pod IP까지” 접근하려면 VPC CIDR을 터널로 라우팅(push route)해야 함
2. `cluster_endpoint_private_access`만 켜두면, OpenVPN 게이트웨이(=VPC 내 라우팅 가능한 소스)가 443 접근을 하도록 SG가 반드시 필요
3. “Ingress를 어떤 형태(예: NLB/ALB, NodePort, 직접 타겟)”로 붙이느냐에 따라 노드 SG 포트 허용 범위를 조정해야 함

