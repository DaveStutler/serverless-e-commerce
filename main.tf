# Terraform configuration for AWS VPC infrastructure
# This recreates the same infrastructure as the Python VPCInstanceCreator class

terraform {
  required_version = ">= 1.0"
  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.0"
    }
  }
}

# Configure the AWS Provider
provider "aws" {
  region = var.aws_region
}

# Data source for availability zones
data "aws_availability_zones" "available" {
  state = "available"
}

# Local values
locals {
  availability_zones = slice(data.aws_availability_zones.available.names, 0, 2)

  common_tags = {
    Project     = var.instance_identifier
    CreatedBy   = "Terraform"
    Environment = var.environment
  }
}

# VPC
resource "aws_vpc" "main" {
  cidr_block           = var.vpc_cidr
  enable_dns_hostnames = true
  enable_dns_support   = true

  tags = merge(local.common_tags, {
    Name = "${var.instance_identifier}-vpc"
  })
}

# Internet Gateway
resource "aws_internet_gateway" "main" {
  vpc_id = aws_vpc.main.id

  tags = merge(local.common_tags, {
    Name = "${var.instance_identifier}-igw"
  })
}

# Elastic IP for NAT Gateway
resource "aws_eip" "nat" {
  domain = "vpc"

  depends_on = [aws_internet_gateway.main]

  tags = merge(local.common_tags, {
    Name = "${var.instance_identifier}-nat-eip"
  })
}

# Public Subnets
resource "aws_subnet" "public" {
  count = length(local.availability_zones)

  vpc_id                  = aws_vpc.main.id
  cidr_block              = cidrsubnet(var.vpc_cidr, 8, count.index * 2 + 1)
  availability_zone       = local.availability_zones[count.index]
  map_public_ip_on_launch = true

  tags = merge(local.common_tags, {
    Name = "${var.instance_identifier}-public-subnet-${count.index + 1}"
    Type = "public"
  })
}

# Private Subnets
resource "aws_subnet" "private" {
  count = length(local.availability_zones)

  vpc_id            = aws_vpc.main.id
  cidr_block        = cidrsubnet(var.vpc_cidr, 8, count.index * 2 + 2)
  availability_zone = local.availability_zones[count.index]

  tags = merge(local.common_tags, {
    Name = "${var.instance_identifier}-private-subnet-${count.index + 1}"
    Type = "private"
  })
}

# NAT Gateway
resource "aws_nat_gateway" "main" {
  allocation_id = aws_eip.nat.id
  subnet_id     = aws_subnet.public[0].id

  depends_on = [aws_internet_gateway.main]

  tags = merge(local.common_tags, {
    Name = "${var.instance_identifier}-nat-gateway"
  })
}

# Route Tables - Public
resource "aws_route_table" "public" {
  count = length(aws_subnet.public)

  vpc_id = aws_vpc.main.id

  route {
    cidr_block = "0.0.0.0/0"
    gateway_id = aws_internet_gateway.main.id
  }

  tags = merge(local.common_tags, {
    Name = "${var.instance_identifier}-public-rt-${count.index + 1}"
    Type = "public"
  })
}

# Route Tables - Private
resource "aws_route_table" "private" {
  count = length(aws_subnet.private)

  vpc_id = aws_vpc.main.id

  route {
    cidr_block     = "0.0.0.0/0"
    nat_gateway_id = aws_nat_gateway.main.id
  }

  tags = merge(local.common_tags, {
    Name = "${var.instance_identifier}-private-rt-${count.index + 1}"
    Type = "private"
  })
}

# Route Table Associations - Public
resource "aws_route_table_association" "public" {
  count = length(aws_subnet.public)

  subnet_id      = aws_subnet.public[count.index].id
  route_table_id = aws_route_table.public[count.index].id
}

# Route Table Associations - Private
resource "aws_route_table_association" "private" {
  count = length(aws_subnet.private)

  subnet_id      = aws_subnet.private[count.index].id
  route_table_id = aws_route_table.private[count.index].id
}

# Security Group for RDS
resource "aws_security_group" "rds" {
  name_prefix = "${var.instance_identifier}-rds-"
  description = "Security group for ${var.db_engine} RDS instance"
  vpc_id      = aws_vpc.main.id

  ingress {
    description = "Database access from VPC"
    from_port   = var.db_port
    to_port     = var.db_port
    protocol    = "tcp"
    cidr_blocks = [var.vpc_cidr]
  }

  egress {
    description = "All outbound traffic"
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }

  tags = merge(local.common_tags, {
    Name         = "${var.instance_identifier}-${var.db_engine}-sg"
    DatabaseType = var.db_engine
  })
}

# RDS Subnet Group
resource "aws_db_subnet_group" "main" {
  name       = "${var.instance_identifier}-subnet-group"
  subnet_ids = aws_subnet.private[*].id

  tags = merge(local.common_tags, {
    Name = "${var.instance_identifier}-subnet-group"
  })
}

# Optional: RDS Instance (commented out by default)
# resource "aws_db_instance" "main" {
#   identifier     = var.instance_identifier
#   engine         = var.db_engine
#   engine_version = var.db_engine_version
#   instance_class = var.db_instance_class
#   
#   allocated_storage     = var.db_allocated_storage
#   max_allocated_storage = var.db_max_allocated_storage
#   storage_type          = "gp3"
#   storage_encrypted     = true
#   
#   db_name  = var.db_name
#   username = var.db_username
#   password = var.db_password
#   
#   vpc_security_group_ids = [aws_security_group.rds.id]
#   db_subnet_group_name   = aws_db_subnet_group.main.name
#   
#   backup_retention_period = var.backup_retention_period
#   backup_window          = var.backup_window
#   maintenance_window     = var.maintenance_window
#   
#   skip_final_snapshot = var.skip_final_snapshot
#   deletion_protection = var.deletion_protection
#   
#   tags = merge(local.common_tags, {
#     Name = "${var.instance_identifier}-database"
#   })
# }