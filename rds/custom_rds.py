import boto3
from botocore.exceptions import ClientError
from vpc.custom_vpc import VPCInstanceCreator  # Import the VPC creator


class RDSManager:
    def __init__(self):
        self.rds_client = boto3.client("rds")
        self.vpc_client = boto3.client("ec2")
        self.vpc_creator = VPCInstanceCreator()  # Initialize VPC creator
        

    def create_rds_instance(
            self,
            db_instance_identifier=None,
            db_subnet_group_name=None,
            db_instance_class="db.t3.micro",
            engine="postgres",
            engine_version="14.18",
            master_username="dbuser",
            master_user_password="YourSecurePassword123!",
            vpc_security_group_ids=None,
        ):

        try:
            response = self.rds_client.create_db_instance(
                DBInstanceIdentifier=db_instance_identifier,
                DBSubnetGroupName=db_subnet_group_name,
                DBInstanceClass=db_instance_class,
                Engine=engine,
                EngineVersion=engine_version,
                MasterUsername=master_username,
                MasterUserPassword=master_user_password,
                AllocatedStorage=20,
                VpcSecurityGroupIds=vpc_security_group_ids,
                PubliclyAccessible=False,
                BackupRetentionPeriod=0  # Disable backups for cost savings in dev
            )
            print(f"Creating RDS instance '{db_instance_identifier}'...")
            return response
        except Exception as e:
            print(f"Error creating RDS instance: {e}")
            raise

    def delete_rds_instance(self, db_instance_identifier):
        try:
            print(f"Deleting RDS instance '{db_instance_identifier}'...")
            response = self.rds_client.delete_db_instance(
                DBInstanceIdentifier=db_instance_identifier,
                SkipFinalSnapshot=True
            )
            return response
        except ClientError as e:
            print(f"Error deleting RDS instance: {e}")
            raise

    def get_vpc_infrastructure_info(self, instance_identifier):
        """Get existing VPC infrastructure information by tags"""
        try:
            # Find VPC by tags
            vpcs_response = self.vpc_client.describe_vpcs(
                Filters=[
                    {'Name': 'tag:Project', 'Values': [instance_identifier]},
                    {'Name': 'tag:CreatedBy', 'Values': ['VPCInstanceCreator']}
                ]
            )
            
            if not vpcs_response['Vpcs']:
                return None
                
            vpc_id = vpcs_response['Vpcs'][0]['VpcId']
            
            # Get subnets in this VPC
            subnets_response = self.vpc_client.describe_subnets(
                Filters=[{'Name': 'vpc-id', 'Values': [vpc_id]}]
            )
            subnet_ids = [subnet['SubnetId'] for subnet in subnets_response['Subnets']]
            
            # Get security groups in this VPC (non-default)
            sg_response = self.vpc_client.describe_security_groups(
                Filters=[
                    {'Name': 'vpc-id', 'Values': [vpc_id]},
                    {'Name': 'group-name', 'Values': [f'{instance_identifier}-sg']}
                ]
            )
            
            security_group_id = None
            if sg_response['SecurityGroups']:
                security_group_id = sg_response['SecurityGroups'][0]['GroupId']
            
            # Check if subnet group exists
            subnet_group_name = f"{instance_identifier}-subnet-group"
            subnet_group_exists = False
            try:
                self.rds_client.describe_db_subnet_groups(DBSubnetGroupName=subnet_group_name)
                subnet_group_exists = True
            except self.rds_client.exceptions.DBSubnetGroupNotFoundFault:
                pass
            
            return {
                'vpc_id': vpc_id,
                'subnet_ids': subnet_ids,
                'security_group_id': security_group_id,
                'subnet_group_name': subnet_group_name,
                'subnet_group_exists': subnet_group_exists
            }
            
        except Exception as e:
            print(f"Error getting VPC infrastructure info: {e}")
            return None

    def create_complete_rds_setup(self, db_instance_identifier, instance_identifier=None):
        """Create complete RDS setup: VPC infrastructure + RDS instance"""
        if instance_identifier is None:
            instance_identifier = db_instance_identifier
            
        print("=== Creating Complete RDS Setup ===")
        
        # Step 1: Check if VPC infrastructure already exists
        print("\n1. Checking for existing VPC infrastructure...")
        vpc_info = self.get_vpc_infrastructure_info(instance_identifier)
        
        if vpc_info:
            print(f"Found existing VPC infrastructure:")
            print(f"  VPC ID: {vpc_info['vpc_id']}")
            print(f"  Subnet IDs: {vpc_info['subnet_ids']}")
            print(f"  Security Group ID: {vpc_info['security_group_id']}")
            print(f"  Subnet Group Exists: {vpc_info['subnet_group_exists']}")
        else:
            # Step 2: Create VPC infrastructure
            print("\n2. Creating VPC infrastructure...")
            vpc_info_raw = self.vpc_creator.create_complete_infrastructure(instance_identifier)
            
            # Convert to our expected format
            vpc_info = {
                'vpc_id': vpc_info_raw['vpc_id'],
                'public_subnet_ids': vpc_info_raw['public_subnet_ids'],
                'private_subnet_ids': vpc_info_raw['private_subnet_ids'],
                'internet_gateway': vpc_info_raw['igw_id'],
                'nat_gateway': vpc_info_raw['nat_gateway_id'],
                'security_group_id': vpc_info_raw['security_group_id'],
                'subnet_group_name': f"{instance_identifier}-subnet-group",
                'subnet_group_exists': True  # Just created
            }
        
        # Step 3: Create RDS instance
        print(f"\n3. Creating RDS PostgreSQL instance...")
        
        # Ensure we have all required components
        if not vpc_info['subnet_group_exists']:
            print("Creating missing subnet group...")
            self.vpc_creator.create_rds_subnet_group(
                vpc_info['subnet_group_name'], 
                vpc_info['subnet_ids']
            )
        
        # Create the RDS instance
        response = self.create_rds_instance(
            db_instance_identifier=db_instance_identifier,
            db_subnet_group_name=vpc_info['subnet_group_name'],
            vpc_security_group_ids=[vpc_info['security_group_id']]
        )
        
        print(f"\n=== RDS Setup Complete ===")
        print(f"RDS Instance: {db_instance_identifier}")
        print(f"VPC ID: {vpc_info['vpc_id']}")
        print(f"Subnet Group: {vpc_info['subnet_group_name']}")
        print(f"Security Group: {vpc_info['security_group_id']}")
        
        return {
            'rds_response': response,
            'vpc_info': vpc_info
        }

    def cleanup_complete_setup(self, db_instance_identifier, instance_identifier=None):
        """Clean up both RDS instance and VPC infrastructure"""
        if instance_identifier is None:
            instance_identifier = db_instance_identifier
            
        print("=== Cleaning up complete setup ===")
        
        # Delete RDS instance first
        try:
            self.rds_client.describe_db_instances(DBInstanceIdentifier=db_instance_identifier)
            print(f"Deleting RDS instance '{db_instance_identifier}'...")
            self.rds_client.delete_db_instance(
                DBInstanceIdentifier=db_instance_identifier,
                SkipFinalSnapshot=True
            )
            
            # Wait for deletion
            print("Waiting for RDS instance deletion...")
            self.rds_client.get_waiter('db_instance_deleted').wait(
                DBInstanceIdentifier=db_instance_identifier,
                WaiterConfig={'Delay': 30, 'MaxAttempts': 40}
            )
            print(f"RDS instance '{db_instance_identifier}' deleted")
        except self.rds_client.exceptions.DBInstanceNotFoundFault:
            print(f"RDS instance '{db_instance_identifier}' doesn't exist")
        except Exception as e:
            print(f"Error deleting RDS instance: {e}")
        
        # Then clean up VPC infrastructure
        self.vpc_creator.cleanup_existing_infrastructure(instance_identifier)

if __name__ == "__main__":
    rds_manager = RDSManager()
    
    # Configuration
    db_instance_identifier = "mypostgresdb"
    instance_identifier = "ecommerce-app"  # Used for VPC naming
    
    # Option 1: Clean up everything first
    # print("🧹 Cleaning up existing infrastructure...")
    # rds_manager.cleanup_complete_setup(db_instance_identifier, instance_identifier)
    
    # Option 2: Create complete setup (VPC + RDS)
    try:
        print("\n🚀 Creating complete RDS setup...")
        result = rds_manager.create_complete_rds_setup(db_instance_identifier, instance_identifier)
        print("\n✅ Complete RDS setup created successfully!")
        
    except Exception as e:
        print(f"\n❌ Failed to create RDS setup: {e}")
    
    # Option 3: Create RDS only (if VPC already exists)
    # vpc_info = rds_manager.get_vpc_infrastructure_info("myinstance")
    # if vpc_info:
    #     rds_manager.create_rds_instance(
    #         db_instance_identifier="mypostgresdb",
    #         db_subnet_group_name=vpc_info['subnet_group_name'],
    #         vpc_security_group_ids=[vpc_info['security_group_id']]
    #     )
