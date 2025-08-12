#!/usr/bin/env python3
"""
Example usage of the modular VPC and RDS creation system
"""

from rds.custom_rds import RDSManager
from vpc.custom_vpc import VPCInstanceCreator

def example_1_complete_setup():
    """Example 1: Create everything from scratch"""
    print("=== Example 1: Complete Setup ===")
    
    rds_manager = RDSManager()
    
    # This will:
    # 1. Clean up any existing infrastructure
    # 2. Create VPC, subnets, security groups
    # 3. Create RDS subnet group
    # 4. Create RDS PostgreSQL instance
    
    result = rds_manager.create_complete_rds_setup(
        db_instance_identifier="my-ecommerce-db",
        instance_identifier="ecommerce-app"
    )
    
    print("Infrastructure created:")
    print(f"  VPC ID: {result['vpc_info']['vpc_id']}")
    print(f"  RDS Instance: my-ecommerce-db")

def example_2_vpc_first_then_rds():
    """Example 2: Create VPC first, then RDS separately"""
    print("\n=== Example 2: VPC First, Then RDS ===")
    
    # Step 1: Create VPC infrastructure only
    vpc_creator = VPCInstanceCreator()
    vpc_info = vpc_creator.create_complete_infrastructure("my-app")
    
    # Step 2: Create RDS using the VPC info
    rds_manager = RDSManager()
    
    # Get the subnet group name (created by VPC creator)
    subnet_group_name = "my-app-subnet-group"
    
    rds_response = rds_manager.create_rds_instance(
        db_instance_identifier="my-app-database",
        db_subnet_group_name=subnet_group_name,
        vpc_security_group_ids=[vpc_info['security_group_id']]
    )
    
    print("Created VPC and RDS separately")

def example_3_check_existing_infrastructure():
    """Example 3: Check what infrastructure already exists"""
    print("\n=== Example 3: Check Existing Infrastructure ===")
    
    rds_manager = RDSManager()
    
    vpc_info = rds_manager.get_vpc_infrastructure_info("ecommerce-app")
    
    if vpc_info:
        print("Found existing infrastructure:")
        print(f"  VPC ID: {vpc_info['vpc_id']}")
        print(f"  Subnets: {vpc_info['subnet_ids']}")
        print(f"  Security Group: {vpc_info['security_group_id']}")
        print(f"  Subnet Group Exists: {vpc_info['subnet_group_exists']}")
        
        # Can create RDS using existing infrastructure
        # rds_manager.create_rds_instance(
        #     db_instance_identifier="another-db",
        #     db_subnet_group_name=vpc_info['subnet_group_name'],
        #     vpc_security_group_ids=[vpc_info['security_group_id']]
        # )
    else:
        print("No existing infrastructure found")

def example_4_cleanup():
    """Example 4: Clean up everything"""
    print("\n=== Example 4: Cleanup ===")
    
    rds_manager = RDSManager()
    
    # This will delete:
    # 1. RDS instance
    # 2. RDS subnet group
    # 3. Security groups
    # 4. Subnets
    # 5. VPC
    
    rds_manager.cleanup_complete_setup(
        db_instance_identifier="my-ecommerce-db",
        instance_identifier="ecommerce-app"
    )
    
    print("Cleanup complete")



if __name__ == "__main__":
    print("Choose an example to run:")
    print("1. Complete setup (VPC + RDS)")
    print("2. VPC first, then RDS")
    print("3. Check existing infrastructure")
    print("4. Cleanup everything")
    
    # Uncomment the example you want to run:
    
    # example_1_complete_setup()
    # example_2_vpc_first_then_rds()
    example_3_check_existing_infrastructure()
    # example_4_cleanup()
