# IaC: Private EKS + OpenVPN (Terraform)

이 Terraform은 AWS 상에서:
1. EKS 클러스터를 **private API endpoint-only**로 구성
2. OpenVPN 서버를 **public subnet**에 띄우고, OpenVPN을 유일한 진입점으로 사용
3. OpenVPN 서버에서 **VPC 대역으로 라우팅 push** + **VPN 클라이언트 source NAT(masquerade)** 수행
4. VPN 서버 보안그룹에서 EKS API(443) 및 노드(NodePort/HTTP/HTTPS)에 접근 가능하도록 SG 허용

개요는 아래 글을 기반으로 함:
- [Building a Production-Grade Private EKS Cluster with OpenVPN, Prometheus & Grafana](https://dev.to/aws-builders/building-a-production-grade-private-eks-cluster-with-openvpn-prometheus-grafana-419)

## Prerequisites
- Terraform 1.5+
- AWS credentials (환경변수 또는 `~/.aws/credentials`)
- 선택: OpenVPN 서버 AMI를 찾기 위한 Ubuntu jammy availability

## Quickstart
1. `IaC/terraform.tfvars` 생성

예시:
```hcl
aws_region = "ap-northeast-2"
project_name = "private-eks-vpn"

vpc_cidr = "10.0.0.0/16"
availability_zones = ["ap-northeast-2a", "ap-northeast-2c"]

public_subnet_cidrs  = ["10.0.101.0/24", "10.0.102.0/24"]
private_subnet_cidrs = ["10.0.1.0/24", "10.0.2.0/24"]

admin_ssh_ingress_cidr = "YOUR_PUBLIC_IP/32"
vpn_ingress_cidr       = "0.0.0.0/0"

vpn_client_cidr = "10.8.0.0/24"

cluster_version = "1.31"
node_instance_types = ["t3.small"]
```

2. 실행
```bash
terraform init
terraform apply
```

3. OpenVPN 클라이언트 설정 확인
```bash
terraform output -raw openvpn_public_ip
```
출력된 `openvpn_public_ip`로 SSH 접속 후 `/home/ubuntu/client-configs/client1.ovpn` 파일을 가져오면 됩니다.

## 보안 주의
- 기본값으로 OpenVPN UDP 1194 ingress를 `0.0.0.0/0`로 열어두었습니다(`vpn_ingress_cidr`).
  실제 운영에서는 반드시 본인 IP/32 또는 필요한 CIDR로 제한하세요.

