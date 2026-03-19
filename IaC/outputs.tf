output "vpc_id" {
  value = module.vpc.vpc_id
}

output "eks_cluster_name" {
  value = module.eks.cluster_name
}

output "openvpn_public_ip" {
  value = aws_eip.openvpn.public_ip
}

output "openvpn_client_profile_path" {
  description = "OpenVPN 서버(EC2) 내부 경로에 생성됩니다."
  value       = "/home/ubuntu/client-configs/client1.ovpn"
}

