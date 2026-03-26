variable "aws_region" {
  type    = string
  default = "ap-northeast-2"
}

variable "project_name" {
  type    = string
  default = "private-eks-vpn"
}

variable "vpc_cidr" {
  type    = string
  default = "10.0.0.0/16"
}

variable "availability_zones" {
  type    = list(string)
  default = []
}

variable "public_subnet_cidrs" {
  type    = list(string)
  default = ["10.0.101.0/24", "10.0.102.0/24"]
}

variable "private_subnet_cidrs" {
  type    = list(string)
  default = ["10.0.1.0/24", "10.0.2.0/24"]
}

variable "cluster_version" {
  type    = string
  default = "1.31"
}

variable "node_instance_types" {
  type    = list(string)
  default = ["t3.small"]
}

variable "node_min_size" {
  type    = number
  default = 1
}

variable "node_max_size" {
  type    = number
  default = 3
}

variable "node_desired_size" {
  type    = number
  default = 2
}

variable "admin_ssh_ingress_cidr" {
  description = "Admin SSH allowed CIDR (your home public IP/32 recommended)"
  type        = string
  default     = "0.0.0.0/0"
}

variable "vpn_ingress_cidr" {
  description = "VPN server UDP allowed CIDR (restrict to your IP recommended)"
  type        = string
  default     = "0.0.0.0/0"
}

variable "vpn_client_cidr" {
  description = "VPN client network CIDR (WireGuard tunnel subnet)"
  type        = string
  default     = "10.8.0.0/24"
}

variable "nodeport_from" {
  description = "NodePort lower bound"
  type        = number
  default     = 30000
}

variable "nodeport_to" {
  description = "NodePort upper bound"
  type        = number
  default     = 32767
}

variable "enable_nat_gateway" {
  description = "EKS nodes need outbound access for pulling images; if you already mirror images, you can disable."
  type        = bool
  default     = true
}

