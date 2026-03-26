output "vpc_id" {
  value = module.vpc.vpc_id
}

output "eks_cluster_name" {
  value = module.eks.cluster_name
}

output "wireguard_public_ip" {
  value = aws_eip.wireguard.public_ip
}

output "wireguard_client_config_path" {
  description = "WireGuard 서버(EC2) 내부 경로에 생성됩니다."
  value       = "/home/ubuntu/client-configs/client1.conf"
}

