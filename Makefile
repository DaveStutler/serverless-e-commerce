# Makefile for Serverless E-commerce Infrastructure

.PHONY: help setup terraform-init terraform-plan terraform-apply terraform-destroy python-setup python-deploy python-cleanup test clean

help: ## Show this help message
	@echo "Available commands:"
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | awk 'BEGIN {FS = ":.*?## "}; {printf "\033[36m%-20s\033[0m %s\n", $$1, $$2}'

# Python Setup
python-setup: ## Setup Python virtual environment and install dependencies
	python -m venv .venv
	.venv/bin/pip install --upgrade pip
	.venv/bin/pip install -r requirements.txt

python-deploy: ## Deploy infrastructure using Python
	.venv/bin/python -c "from vpc.custom_vpc import VPCInstanceCreator; vpc = VPCInstanceCreator(); infrastructure = vpc.create_complete_infrastructure('serverless-ecommerce'); print('Infrastructure created:', infrastructure)"

python-cleanup: ## Clean up infrastructure using Python
	.venv/bin/python -c "from vpc.custom_vpc import VPCInstanceCreator; vpc = VPCInstanceCreator(); vpc.cleanup_existing_infrastructure('serverless-ecommerce')"

# Terraform Operations
terraform-init: ## Initialize Terraform
	terraform init

terraform-plan: ## Plan Terraform deployment
	terraform plan -var-file="terraform.tfvars"

terraform-apply: ## Apply Terraform configuration
	terraform apply -var-file="terraform.tfvars"

terraform-destroy: ## Destroy Terraform infrastructure
	terraform destroy -var-file="terraform.tfvars"

# Testing
test: ## Run all tests
	.venv/bin/python -m unittest pytest.vpc_test.TestVPCInstanceCreator -v

test-vpc: ## Test VPC creation only
	.venv/bin/python -m unittest pytest.vpc_test.TestVPCInstanceCreator.test_create_vpc -v

test-complete: ## Test complete infrastructure
	.venv/bin/python -m unittest pytest.vpc_test.TestVPCInstanceCreator.test_create_complete_infrastructure -v

# Setup and Configuration
setup: python-setup terraform-init ## Complete project setup

config: ## Copy example configuration files
	cp terraform.tfvars.example terraform.tfvars
	@echo "Please edit terraform.tfvars with your configuration"

# Cleanup
clean: ## Clean up temporary files
	rm -rf .venv/
	rm -rf __pycache__/
	rm -rf */__pycache__/
	rm -rf .terraform/
	rm -f *.tfstate*
	rm -f terraform.tfplan

# Validation
validate: ## Validate Terraform configuration
	terraform validate
	terraform fmt -check

format: ## Format Terraform files
	terraform fmt

# Documentation
docs: ## Generate documentation
	@echo "Documentation available in README.md"
	@echo "Terraform outputs:"
	@terraform output 2>/dev/null || echo "Run 'terraform apply' first"
