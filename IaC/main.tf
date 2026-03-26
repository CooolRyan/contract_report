data "aws_availability_zones" "available" {
  state = "available"
}

locals {
  azs = length(var.availability_zones) > 0 ? var.availability_zones : slice(data.aws_availability_zones.available.names, 0, 2)

  # WireGuard tunnel IPs (server/client) live inside vpn_client_cidr
  vpn_client_prefix = split("/", var.vpn_client_cidr)[1]
  wg_server_ip      = cidrhost(var.vpn_client_cidr, 1)
  wg_client1_ip     = cidrhost(var.vpn_client_cidr, 2)

  vpc_cidr_mask = cidrnetmask(var.vpc_cidr)
  vpc_dns_ip    = cidrhost(var.vpc_cidr, 2)

  common_tags = merge(
    {
      Project   = var.project_name
      ManagedBy = "Terraform"
    },
    var.extra_tags
  )
}

module "vpc" {
  source  = "terraform-aws-modules/vpc/aws"
  version = "~> 5.0"

  name = "${var.project_name}-vpc"
  cidr = var.vpc_cidr

  tags = local.common_tags

  azs             = local.azs
  public_subnets  = var.public_subnet_cidrs
  private_subnets = var.private_subnet_cidrs

  enable_nat_gateway = var.enable_nat_gateway
  single_nat_gateway = true

  enable_dns_hostnames = true
  enable_dns_support   = true

  public_subnet_tags = {
    "kubernetes.io/role/elb" = "1"
  }

  private_subnet_tags = {
    "kubernetes.io/role/internal-elb" = "1"
  }
}

module "eks" {
  source  = "terraform-aws-modules/eks/aws"
  version = "~> 20.0"

  cluster_name    = "${var.project_name}-cluster"
  cluster_version = var.cluster_version

  tags = local.common_tags

  vpc_id     = module.vpc.vpc_id
  subnet_ids = module.vpc.private_subnets

  cluster_endpoint_public_access  = false
  cluster_endpoint_private_access = true

  enable_cluster_creator_admin_permissions = true

  eks_managed_node_groups = {
    default = {
      instance_types = var.node_instance_types
      min_size       = var.node_min_size
      max_size       = var.node_max_size
      desired_size   = var.node_desired_size
    }
  }
}

data "aws_ami" "ubuntu" {
  most_recent = true
  owners      = ["099720109477"] # Canonical

  filter {
    name   = "name"
    values = ["ubuntu/images/hvm-ssd/ubuntu-jammy-22.04-amd64-server-*"]
  }

  filter {
    name   = "virtualization-type"
    values = ["hvm"]
  }
}

resource "aws_security_group" "wireguard" {
  name_prefix = "${var.project_name}-wireguard-"
  vpc_id      = module.vpc.vpc_id
  description = "WireGuard server security group"

  ingress {
    description = "WireGuard UDP"
    from_port   = 51820
    to_port     = 51820
    protocol    = "udp"
    cidr_blocks = [var.vpn_ingress_cidr]
  }

  ingress {
    description = "SSH admin"
    from_port   = 22
    to_port     = 22
    protocol    = "tcp"
    cidr_blocks = [var.admin_ssh_ingress_cidr]
  }

  egress {
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }

  lifecycle {
    create_before_destroy = true
  }
}

resource "aws_instance" "wireguard" {
  ami                         = data.aws_ami.ubuntu.id
  instance_type               = "t3.small"
  subnet_id                   = module.vpc.public_subnets[0]
  vpc_security_group_ids      = [aws_security_group.wireguard.id]
  associate_public_ip_address = true
  source_dest_check           = false

  user_data = templatefile("${path.module}/wireguard_userdata.sh.tpl", {
    vpc_cidr          = var.vpc_cidr
    vpc_cidr_mask    = local.vpc_cidr_mask
    vpc_dns_ip       = local.vpc_dns_ip

    vpn_client_cidr     = var.vpn_client_cidr
    vpn_client_prefix   = local.vpn_client_prefix
    wg_server_ip        = local.wg_server_ip
    wg_client1_ip       = local.wg_client1_ip
  })

  tags = {
    Name = "${var.project_name}-wireguard"
  }
}

resource "aws_eip" "wireguard" {
  instance = aws_instance.wireguard.id
  domain   = "vpc"
}

# EKS private API(443) 접근 허용: OpenVPN 서버(및 그 SG) -> EKS cluster SG
resource "aws_security_group_rule" "vpn_to_eks_api" {
  description              = "Allow VPN server to access EKS API (private endpoint)"
  type                     = "ingress"
  from_port                = 443
  to_port                  = 443
  protocol                 = "tcp"
  security_group_id        = module.eks.cluster_security_group_id
  source_security_group_id = aws_security_group.wireguard.id
}

# Ingress controller는 보통 NodePort/Target 방식이므로 Node SG에 최소 포트 허용
resource "aws_security_group_rule" "vpn_to_node_http_https" {
  description              = "Allow VPN traffic to nodes (80/443)"
  type                     = "ingress"
  from_port                = 80
  to_port                  = 443
  protocol                 = "tcp"
  security_group_id        = module.eks.node_security_group_id
  source_security_group_id = aws_security_group.wireguard.id
}

resource "aws_security_group_rule" "vpn_to_node_nodeport_range" {
  description              = "Allow VPN traffic to nodes (NodePort range)"
  type                     = "ingress"
  from_port                = var.nodeport_from
  to_port                  = var.nodeport_to
  protocol                 = "tcp"
  security_group_id        = module.eks.node_security_group_id
  source_security_group_id = aws_security_group.wireguard.id
}

