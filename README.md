# Serverless E-commerce AWS Infrastructure

A comprehensive AWS infrastructure automation project that provides both **Python (Boto3)** and **Terraform** implementations for creating production-ready VPC architectures suitable for serverless e-commerce applications.

## 🏗️ Architecture Overview

This project creates a robust AWS VPC infrastructure with the following components:

- **VPC** with DNS support enabled
- **Public Subnets** (2 AZs) for NAT Gateway, Load Balancers
- **Private Subnets** (2 AZs) for RDS, Lambda functions
- **Internet Gateway** for public internet access
- **NAT Gateway** for private subnet outbound connectivity
- **Route Tables** with proper routing configuration
- **Security Groups** with database-specific rules
- **RDS Subnet Group** for high-availability database deployment

```
┌─────────────────────────────────────────────────────────────┐
│                    VPC (10.0.0.0/16)                       │
├─────────────────────────┬───────────────────────────────────┤
│   Public Subnet AZ-1a   │      Public Subnet AZ-1b         │
│     (10.0.1.0/24)       │        (10.0.3.0/24)             │
│                         │                                   │
│     NAT Gateway         │         (Future: ALB)             │
├─────────────────────────┼───────────────────────────────────┤
│   Private Subnet AZ-1a  │     Private Subnet AZ-1b          │
│     (10.0.2.0/24)       │        (10.0.4.0/24)             │
│                         │                                   │
│     RDS Primary         │        RDS Standby                │
│     Lambda Functions    │        Lambda Functions           │
└─────────────────────────┴───────────────────────────────────┘
```

## 🚀 Features

### ✅ **Production-Ready**
- Multi-AZ deployment for high availability
- Proper public/private subnet separation
- NAT Gateway for secure outbound connectivity
- Comprehensive resource tagging

### ✅ **Dual Implementation**
- **Python/Boto3**: Programmatic infrastructure management
- **Terraform**: Infrastructure as Code (IaC)

### ✅ **Database Support**
- PostgreSQL (default)
- MySQL
- Oracle
- SQL Server

### ✅ **Testing & Validation**
- Comprehensive test suite using `moto`
- Infrastructure validation
- Cleanup automation

## 📁 Project Structure

```
serverless-e-commerce/
├── main.tf                    # Main Terraform configuration
├── variables.tf               # Terraform variables
├── outputs.tf                 # Terraform outputs
├── terraform.tfvars.example   # Example variables file
├── vpc/
│   └── custom_vpc.py          # Python VPC implementation
├── pytest/
│   └── vpc_test.py            # Comprehensive test suite
├── requirements.txt           # Python dependencies
└── README.md                  # This file
```

## 🛠️ Prerequisites

### For Terraform
- [Terraform](https://www.terraform.io/downloads.html) >= 1.0
- AWS CLI configured with appropriate credentials
- AWS account with necessary permissions

### For Python
- Python 3.8+
- AWS CLI configured
- Virtual environment (recommended)

## 🚀 Quick Start

### Option 1: Terraform Deployment

1. **Clone and Setup**
   ```bash
   git clone <your-repo-url>
   cd serverless-e-commerce
   ```

2. **Configure Variables**
   ```bash
   cp terraform.tfvars.example terraform.tfvars
   # Edit terraform.tfvars with your values
   ```

3. **Deploy Infrastructure**
   ```bash
   terraform init
   terraform plan
   terraform apply
   ```

4. **Clean Up**
   ```bash
   terraform destroy
   ```

### Option 2: Python Deployment

1. **Setup Python Environment**
   ```bash
   python -m venv .venv
   source .venv/bin/activate  # Linux/Mac
   # .venv\Scripts\activate   # Windows
   pip install -r requirements.txt
   ```

2. **Deploy Infrastructure**
   ```bash
   python -c "
   from vpc.custom_vpc import VPCInstanceCreator
   vpc = VPCInstanceCreator()
   infrastructure = vpc.create_complete_infrastructure('my-ecommerce')
   print('Infrastructure created:', infrastructure)
   "
   ```

3. **Clean Up**
   ```bash
   python -c "
   from vpc.custom_vpc import VPCInstanceCreator
   vpc = VPCInstanceCreator()
   vpc.cleanup_existing_infrastructure('my-ecommerce')
   "
   ```

## ⚙️ Configuration

### Terraform Variables

Key variables you can customize in `terraform.tfvars`:

```hcl
# Project Configuration
instance_identifier = "my-serverless-ecommerce"
environment        = "dev"
aws_region         = "us-east-1"

# Network Configuration
vpc_cidr = "10.0.0.0/16"

# Database Configuration
db_engine    = "postgres"
db_username  = "admin"
db_password  = "your-secure-password"
```

### Python Configuration

Customize the infrastructure by modifying parameters in the VPCInstanceCreator methods:

```python
from vpc.custom_vpc import VPCInstanceCreator

vpc = VPCInstanceCreator()

# Create infrastructure with custom identifier
infrastructure = vpc.create_complete_infrastructure("production-ecommerce")

# Create individual components
vpc_id = vpc.create_vpc(instance_identifier="custom-vpc")
```

## 🧪 Testing

Run the comprehensive test suite:

```bash
# Activate virtual environment
source .venv/bin/activate

# Run all tests
python -m unittest pytest.vpc_test.TestVPCInstanceCreator -v

# Run specific test
python -m unittest pytest.vpc_test.TestVPCInstanceCreator.test_create_complete_infrastructure -v
```

### Test Coverage
- VPC creation and configuration
- Subnet creation across multiple AZs
- Internet Gateway attachment
- NAT Gateway deployment
- Route table configuration
- Security group rules validation
- RDS subnet group creation
- Complete infrastructure integration
- Cleanup verification

## 📋 Infrastructure Details

### AWS Resources Created

| Resource Type | Count | Purpose |
|---------------|-------|---------|
| VPC | 1 | Main network container |
| Public Subnets | 2 | NAT Gateway, future load balancers |
| Private Subnets | 2 | RDS, Lambda functions |
| Internet Gateway | 1 | Public internet access |
| NAT Gateway | 1 | Private subnet outbound access |
| Elastic IP | 1 | NAT Gateway static IP |
| Route Tables | 4 | Network routing (2 public, 2 private) |
| Security Group | 1 | Database access control |
| RDS Subnet Group | 1 | Database high availability |

### Network Architecture

- **VPC CIDR**: `10.0.0.0/16` (65,534 IP addresses)
- **Public Subnets**: `10.0.1.0/24`, `10.0.3.0/24`
- **Private Subnets**: `10.0.2.0/24`, `10.0.4.0/24`
- **Multi-AZ**: Deployed across 2 availability zones
- **DNS**: Enabled for hostname resolution

## 🔒 Security Best Practices

### ✅ **Network Security**
- Private subnets for database and application tiers
- Security groups with least-privilege access
- NAT Gateway for controlled outbound access

### ✅ **Database Security**
- RDS in private subnets only
- Security group restricts access to VPC CIDR
- Database subnet group across multiple AZs

### ✅ **Access Control**
- No direct internet access to private resources
- Controlled routing through NAT Gateway
- Proper resource tagging for governance

## 🎯 Use Cases

### Perfect For:
- **Serverless E-commerce Applications**
- **Web Applications with Database**
- **API Services with RDS Backend**
- **Lambda Functions requiring Database Access**
- **Development and Testing Environments**

### Production Considerations:
- Enable deletion protection for RDS
- Use Multi-AZ RDS deployment
- Implement proper backup strategies
- Monitor with CloudWatch
- Use AWS WAF for web applications

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch
3. Add tests for new functionality
4. Ensure all tests pass
5. Submit a pull request

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## 🆘 Troubleshooting

### Common Issues

**Issue**: Terraform state conflicts
```bash
# Solution: Remove state lock
terraform force-unlock <lock-id>
```

**Issue**: AWS credentials not configured
```bash
# Solution: Configure AWS CLI
aws configure
```

**Issue**: Python import errors
```bash
# Solution: Ensure virtual environment is activated
source .venv/bin/activate
pip install -r requirements.txt
```

**Issue**: Resource already exists errors
```bash
# Solution: Clean up existing resources first
terraform destroy
# or for Python:
python -c "from vpc.custom_vpc import VPCInstanceCreator; VPCInstanceCreator().cleanup_existing_infrastructure('instance-name')"
```

## 📞 Support

For issues and questions:
- Open an issue on GitHub
- Check the troubleshooting section
- Review AWS documentation for specific services

---

**Built with ❤️ for the AWS community**