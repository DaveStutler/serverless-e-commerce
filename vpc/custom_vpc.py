import boto3
import sys

class VPCInstanceCreator:
    """
    Create VPCs and associated resources.
    - 1. VPC Creation
        def create_vpc: create a VPC with tags.
        def get_vpc_id: get the ID of the first VPC.
        def get_availability_zones: get available AZs in the current region.
        def create_subnet: create a subnet in the specified VPC and AZ.
        def get_subnet_id: get the ID of the first subnet.
        def create_security_group: create a security group for RDS.

        def create_internet_gateway: create an internet gateway and attach to VPC.
        def create_route_table: create a route table and associate with subnets.
        def create_route: create a route in the route table.
        def attach_internet_gateway: attach an internet gateway to a VPC.
        def create_nat_gateway: create a NAT gateway in a public subnet.
        def create_route_to_nat: create a route to the NAT gateway in the private subnet's route table.

    - 2. Cleanup
        # clean up methods:
        def cleanup_specific_vpc: clean up a specific VPC and all its resources.
        def cleanup_existing_infrastructure: clean up existing infrastructure with the same name.

        def create_complete_infrastructure: create complete infrastructure: VPC, subnets, security group
    """

    def __init__(self):
        self.rds_client = boto3.client('rds')
        self.ec2_client = boto3.client('ec2')

    def create_vpc(self, cidr_block='10.0.0.0/16', instance_identifier="devInstance"):
        """Create a VPC with tags for easy identification"""
        try:
            response = self.ec2_client.create_vpc(CidrBlock=cidr_block)
            vpc_id = response['Vpc']['VpcId']
            
            # Wait for VPC to be available
            self.ec2_client.get_waiter('vpc_available').wait(VpcIds=[vpc_id])
            
            # Add tags to identify this VPC
            self.ec2_client.create_tags(
                Resources=[vpc_id],
                Tags=[
                    {'Key': 'Name', 'Value': f'{instance_identifier}-vpc'},
                    {'Key': 'CreatedBy', 'Value': 'VPCInstanceCreator'},
                    {'Key': 'Project', 'Value': instance_identifier}
                ]
            )
            
            # Enable DNS support and DNS hostnames
            self.ec2_client.modify_vpc_attribute(VpcId=vpc_id, EnableDnsSupport={'Value': True})
            self.ec2_client.modify_vpc_attribute(VpcId=vpc_id, EnableDnsHostnames={'Value': True})
            
            print(f"Created VPC with ID: {vpc_id}")
            return vpc_id
        except Exception as e:
            print(f"Error creating VPC: {e}")
            raise

    def get_vpc_id(self):
        return self.ec2_client.describe_vpcs()['Vpcs'][0]['VpcId']

    def get_availability_zones(self):
        """
        Get available AZs in the current region
        Return at least 2 different Availability Zones for high availability and fault tolerance.
        """
        try:
            response = self.ec2_client.describe_availability_zones(
                Filters=[{'Name': 'state', 'Values': ['available']}]
            )
            az_names = [az['ZoneName'] for az in response['AvailabilityZones']]
            print(f"Available AZs: {az_names}")
            return az_names[:2]  # Return first 2 AZs for subnet group
        except Exception as e:
            print(f"Error getting availability zones: {e}")
            raise

    def create_subnet(self, vpc_id, cidr_block, availability_zone):
        """Create a subnet in the specified VPC and AZ"""
        try:
            response = self.ec2_client.create_subnet(
                VpcId=vpc_id,
                CidrBlock=cidr_block,
                AvailabilityZone=availability_zone
            )
            subnet_id = response['Subnet']['SubnetId']
            
            # Wait for subnet to be available
            self.ec2_client.get_waiter('subnet_available').wait(SubnetIds=[subnet_id])

            # Add tags to identify this subnet
            self.ec2_client.create_tags(
                Resources=[subnet_id],
                Tags=[
                    {'Key': 'Name', 'Value': f'subnet-{availability_zone}'},
                    {'Key': 'CreatedBy', 'Value': 'VPCInstanceCreator'}
                ]
            )
            
            print(f"Created subnet {subnet_id} in AZ {availability_zone}")
            return subnet_id
        except Exception as e:
            print(f"Error creating subnet: {e}")
            raise

    def get_subnet_id(self):
        return self.ec2_client.describe_subnets()['Subnets'][0]['SubnetId']


    def create_internet_gateway(self, vpc_id, instance_identifier="devInstance"):
        """Create an internet gateway and attach to VPC"""
        try:
            # Create Internet Gateway
            response = self.ec2_client.create_internet_gateway()
            igw_id = response['InternetGateway']['InternetGatewayId']
            
            # Add tags
            self.ec2_client.create_tags(
                Resources=[igw_id],
                Tags=[
                    {'Key': 'Name', 'Value': f'{instance_identifier}-igw'},
                    {'Key': 'CreatedBy', 'Value': 'VPCInstanceCreator'},
                    {'Key': 'Project', 'Value': instance_identifier}
                ]
            )
            
            # Attach to VPC
            self.ec2_client.attach_internet_gateway(
                InternetGatewayId=igw_id,
                VpcId=vpc_id
            )
            
            print(f"Created and attached Internet Gateway: {igw_id}")
            return igw_id
        except Exception as e:
            print(f"Error creating internet gateway: {e}")
            raise

    def create_route_table(self, vpc_id, subnet_id, instance_identifier="devInstance", is_public=True):
        """Create a route table and associate with subnet"""
        try:
            # Create route table
            response = self.ec2_client.create_route_table(VpcId=vpc_id)
            route_table_id = response['RouteTable']['RouteTableId']
            
            # Add tags
            table_type = "public" if is_public else "private"
            self.ec2_client.create_tags(
                Resources=[route_table_id],
                Tags=[
                    {'Key': 'Name', 'Value': f'{instance_identifier}-{table_type}-rt'},
                    {'Key': 'CreatedBy', 'Value': 'VPCInstanceCreator'},
                    {'Key': 'Project', 'Value': instance_identifier},
                    {'Key': 'Type', 'Value': table_type}
                ]
            )
            
            # Associate with subnet
            self.ec2_client.associate_route_table(
                RouteTableId=route_table_id,
                SubnetId=subnet_id
            )
            
            print(f"Created {table_type} route table {route_table_id} and associated with subnet {subnet_id}")
            return route_table_id
        except Exception as e:
            print(f"Error creating route table: {e}")
            raise
    
    def create_route(self, route_table_id, destination_cidr='0.0.0.0/0', gateway_id=None, nat_gateway_id=None):
        """Create a route in the route table"""
        try:
            if gateway_id:
                # Route to Internet Gateway (for public subnets)
                self.ec2_client.create_route(
                    RouteTableId=route_table_id,
                    DestinationCidrBlock=destination_cidr,
                    GatewayId=gateway_id
                )
                print(f"Created route to IGW {gateway_id} in route table {route_table_id}")
            elif nat_gateway_id:
                # Route to NAT Gateway (for private subnets)
                self.ec2_client.create_route(
                    RouteTableId=route_table_id,
                    DestinationCidrBlock=destination_cidr,
                    NatGatewayId=nat_gateway_id
                )
                print(f"Created route to NAT Gateway {nat_gateway_id} in route table {route_table_id}")
        except Exception as e:
            print(f"Error creating route: {e}")
            raise

    def create_nat_gateway(self, public_subnet_id, instance_identifier="devInstance"):
        """Create a NAT Gateway in a public subnet for private subnet internet access"""
        try:
            # First, allocate an Elastic IP for the NAT Gateway
            eip_response = self.ec2_client.allocate_address(Domain='vpc')
            allocation_id = eip_response['AllocationId']
            
            # Tag the Elastic IP
            self.ec2_client.create_tags(
                Resources=[allocation_id],
                Tags=[
                    {'Key': 'Name', 'Value': f'{instance_identifier}-nat-eip'},
                    {'Key': 'CreatedBy', 'Value': 'VPCInstanceCreator'},
                    {'Key': 'Project', 'Value': instance_identifier}
                ]
            )
            
            # Create NAT Gateway
            response = self.ec2_client.create_nat_gateway(
                SubnetId=public_subnet_id,
                AllocationId=allocation_id
            )
            nat_gateway_id = response['NatGateway']['NatGatewayId']
            
            # Wait for NAT Gateway to be available
            print(f"Waiting for NAT Gateway {nat_gateway_id} to be available...")
            waiter = self.ec2_client.get_waiter('nat_gateway_available')
            waiter.wait(NatGatewayIds=[nat_gateway_id])
            
            # Tag the NAT Gateway
            self.ec2_client.create_tags(
                Resources=[nat_gateway_id],
                Tags=[
                    {'Key': 'Name', 'Value': f'{instance_identifier}-nat-gateway'},
                    {'Key': 'CreatedBy', 'Value': 'VPCInstanceCreator'},
                    {'Key': 'Project', 'Value': instance_identifier}
                ]
            )
            
            print(f"Created NAT Gateway {nat_gateway_id} in subnet {public_subnet_id}")
            return nat_gateway_id
        except Exception as e:
            print(f"Error creating NAT Gateway: {e}")
            raise

    def create_rds_postgres_security_group(self, vpc_id, instance_identifier="devInstance"):
        """Create a security group for PostgreSQL access"""
        try:
            response = self.ec2_client.create_security_group(
                GroupName=f"{instance_identifier}-sg",
                Description='Security group for instance',
                VpcId=vpc_id
            )
            security_group_id = response['GroupId']
            
            # Add inbound rule for PostgreSQL (port 5432)
            self.ec2_client.authorize_security_group_ingress(
                GroupId=security_group_id,
                IpPermissions=[
                    {
                        'IpProtocol': 'tcp',
                        'FromPort': 5432,
                        'ToPort': 5432,
                        'IpRanges': [{'CidrIp': '10.0.0.0/16'}]  # Allow access from VPC
                    }
                ]
            )
            
            print(f"Created security group {security_group_id}")
            return security_group_id
        except Exception as e:
            print(f"Error creating security group: {e}")
            raise

    def create_rds_subnet_group(self, subnet_group_name, subnet_ids):
        try:
            # Check if subnet group already exists
            try:
                response = self.rds_client.describe_db_subnet_groups(
                    DBSubnetGroupName=subnet_group_name
                )
                print(f"RDS subnet group '{subnet_group_name}' already exists, using existing one")
                return response['DBSubnetGroups'][0]['DBSubnetGroupName']
            except self.rds_client.exceptions.DBSubnetGroupNotFoundFault:
                # Subnet group doesn't exist, create it
                pass
            
            response = self.rds_client.create_db_subnet_group(
                DBSubnetGroupName=subnet_group_name,
                DBSubnetGroupDescription='Subnet group for RDS',
                SubnetIds=subnet_ids
            )

            # Add tags
            self.rds_client.add_tags_to_resource(
                ResourceName=response['DBSubnetGroup']['DBSubnetGroupArn'],
                Tags=[
                    {'Key': 'Name', 'Value': subnet_group_name},
                    {'Key': 'CreatedBy', 'Value': 'VPCInstanceCreator'}
                ]
            )

            print(f"Created RDS subnet group '{subnet_group_name}'")
            return response['DBSubnetGroup']['DBSubnetGroupName']
        except Exception as e:
            print(f"Error creating RDS subnet group: {e}")
            raise

    def cleanup_specific_vpc(self, vpc_id):
        """Clean up a specific VPC and all its resources"""
        print(f"=== Cleaning up VPC {vpc_id} and all its resources ===")
        
        try:
            # Step 1: Delete NAT Gateways and their Elastic IPs
            print("1. Cleaning up NAT Gateways...")
            nat_gateways_response = self.ec2_client.describe_nat_gateways(
                Filters=[{'Name': 'vpc-id', 'Values': [vpc_id]}]
            )
            
            for nat_gw in nat_gateways_response['NatGateways']:
                if nat_gw['State'] not in ['deleted', 'deleting']:
                    nat_gw_id = nat_gw['NatGatewayId']
                    try:
                        # Get the Elastic IP allocation ID before deleting NAT Gateway
                        allocation_ids = []
                        for address in nat_gw.get('NatGatewayAddresses', []):
                            if 'AllocationId' in address:
                                allocation_ids.append(address['AllocationId'])
                        
                        print(f"Deleting NAT Gateway '{nat_gw_id}'...")
                        self.ec2_client.delete_nat_gateway(NatGatewayId=nat_gw_id)
                        
                        # Wait for NAT Gateway to be deleted before releasing EIPs
                        print(f"Waiting for NAT Gateway {nat_gw_id} to be deleted...")
                        waiter = self.ec2_client.get_waiter('nat_gateway_deleted')
                        waiter.wait(NatGatewayIds=[nat_gw_id])
                        print(f"NAT Gateway {nat_gw_id} deleted")
                        
                        # Release the Elastic IPs
                        for allocation_id in allocation_ids:
                            try:
                                print(f"Releasing Elastic IP {allocation_id}...")
                                self.ec2_client.release_address(AllocationId=allocation_id)
                                print(f"Released Elastic IP {allocation_id}")
                            except Exception as eip_error:
                                print(f"Error releasing Elastic IP {allocation_id}: {eip_error}")
                                
                    except Exception as e:
                        print(f"Error deleting NAT Gateway {nat_gw_id}: {e}")

            # Step 2: Delete custom route tables (before deleting subnets)
            print("2. Cleaning up custom route tables...")
            route_tables_response = self.ec2_client.describe_route_tables(
                Filters=[{'Name': 'vpc-id', 'Values': [vpc_id]}]
            )
            
            for rt in route_tables_response['RouteTables']:
                # Skip the main route table (it gets deleted with the VPC)
                is_main = any(assoc.get('Main', False) for assoc in rt.get('Associations', []))
                if not is_main:
                    rt_id = rt['RouteTableId']
                    try:
                        # Disassociate from subnets first
                        for association in rt.get('Associations', []):
                            if 'SubnetId' in association:
                                assoc_id = association['RouteTableAssociationId']
                                try:
                                    print(f"Disassociating route table {rt_id} from subnet...")
                                    self.ec2_client.disassociate_route_table(AssociationId=assoc_id)
                                except Exception as disassoc_error:
                                    print(f"Error disassociating route table: {disassoc_error}")
                        
                        print(f"Deleting route table '{rt_id}'...")
                        self.ec2_client.delete_route_table(RouteTableId=rt_id)
                        print(f"Deleted route table '{rt_id}'")
                    except Exception as e:
                        print(f"Error deleting route table {rt_id}: {e}")

            # Step 3: Detach and delete Internet Gateways
            print("3. Cleaning up Internet Gateways...")
            igw_response = self.ec2_client.describe_internet_gateways(
                Filters=[{'Name': 'attachment.vpc-id', 'Values': [vpc_id]}]
            )
            
            for igw in igw_response['InternetGateways']:
                igw_id = igw['InternetGatewayId']
                try:
                    print(f"Detaching Internet Gateway '{igw_id}' from VPC '{vpc_id}'...")
                    self.ec2_client.detach_internet_gateway(
                        InternetGatewayId=igw_id,
                        VpcId=vpc_id
                    )
                    print(f"Deleting Internet Gateway '{igw_id}'...")
                    self.ec2_client.delete_internet_gateway(InternetGatewayId=igw_id)
                    print(f"Deleted Internet Gateway '{igw_id}'")
                except Exception as e:
                    print(f"Error deleting Internet Gateway {igw_id}: {e}")

            # Step 4: Delete subnets
            print("4. Cleaning up subnets...")
            subnets_response = self.ec2_client.describe_subnets(
                Filters=[{'Name': 'vpc-id', 'Values': [vpc_id]}]
            )
            
            for subnet in subnets_response['Subnets']:
                subnet_id = subnet['SubnetId']
                try:
                    print(f"Deleting subnet '{subnet_id}'...")
                    self.ec2_client.delete_subnet(SubnetId=subnet_id)
                    print(f"Deleted subnet '{subnet_id}'")
                except Exception as e:
                    print(f"Error deleting subnet {subnet_id}: {e}")
            
            # Step 5: Delete non-default security groups
            print("5. Cleaning up security groups...")
            sg_response = self.ec2_client.describe_security_groups(
                Filters=[{'Name': 'vpc-id', 'Values': [vpc_id]}]
            )
            
            for sg in sg_response['SecurityGroups']:
                if sg['GroupName'] != 'default':
                    try:
                        print(f"Deleting security group '{sg['GroupId']}'...")
                        self.ec2_client.delete_security_group(GroupId=sg['GroupId'])
                        print(f"Deleted security group '{sg['GroupId']}'")
                    except Exception as e:
                        print(f"Error deleting security group {sg['GroupId']}: {e}")
            
            # Step 6: Delete the VPC
            print("6. Deleting VPC...")
            print(f"Deleting VPC '{vpc_id}'...")
            self.ec2_client.delete_vpc(VpcId=vpc_id)
            print(f"Deleted VPC '{vpc_id}'")
            
        except Exception as e:
            print(f"Error cleaning up VPC {vpc_id}: {e}")

    def cleanup_existing_infrastructure(self, instance_identifier="devInstance"):
        """Clean up existing infrastructure with the same name"""
        print("=== Cleaning up existing infrastructure ===")

        # Delete subnet group if it exists
        subnet_group_name = f"{instance_identifier}-subnet-group"
        try:
            self.rds_client.describe_db_subnet_groups(DBSubnetGroupName=subnet_group_name)
            print(f"Deleting existing subnet group '{subnet_group_name}'...")
            self.rds_client.delete_db_subnet_group(DBSubnetGroupName=subnet_group_name)
            print(f"Subnet group '{subnet_group_name}' deleted")
        except self.rds_client.exceptions.DBSubnetGroupNotFoundFault:
            print(f"Subnet group '{subnet_group_name}' doesn't exist")

        # Find and delete VPCs using cleanup_specific_vpc and tags
        try:
            vpcs_response = self.ec2_client.describe_vpcs(
                Filters=[
                    {'Name': 'tag:Project', 'Values': [instance_identifier]},
                    {'Name': 'tag:CreatedBy', 'Values': ['VPCInstanceCreator']}
                ]
            )
            
            for vpc in vpcs_response['Vpcs']:
                vpc_id = vpc['VpcId']
                print(f"Found VPC created by this script: {vpc_id}")
                self.cleanup_specific_vpc(vpc_id)
                
        except Exception as e:
            print(f"Error during targeted VPC cleanup: {e}")
            
        # Fallback: Clean up any non-default VPCs (be careful with this!)
        print("\n--- Fallback cleanup for non-default VPCs ---")
        try:
            vpcs = self.ec2_client.describe_vpcs()['Vpcs']
            
            for vpc in vpcs:
                vpc_id = vpc['VpcId']
                
                # Skip default VPC 
                if vpc.get('IsDefault', False):
                    continue
                    
                print(f"Processing non-default VPC: {vpc_id}")
                
                # Use the comprehensive cleanup method
                self.cleanup_specific_vpc(vpc_id)
                    
        except Exception as e:
            print(f"Error during VPC cleanup: {e}")

    def create_complete_infrastructure(self, db_instance_identifier="mydbinstance"):
        """Create complete infrastructure following AWS best practices"""
        print("=== Creating Complete AWS Infrastructure (Best Practices) ===")
        
        # Step 1: Create VPC
        print("\n1. Creating VPC...")
        vpc_id = self.create_vpc(instance_identifier=db_instance_identifier)
        
        # Step 2: Get availability zones and create subnets
        print("\n2. Creating subnets in multiple AZs...")
        availability_zones = self.get_availability_zones()
        public_subnet_ids = []
        private_subnet_ids = []
        
        # Create public and private subnets in each AZ
        for i, az in enumerate(availability_zones):
            # Public subnet for each AZ (for NAT Gateway, Bastion, etc.)
            public_cidr = f"10.0.{i*2+1}.0/24"  # 10.0.1.0/24, 10.0.3.0/24
            public_subnet_id = self.create_subnet(vpc_id, public_cidr, az)
            
            # Tag as public subnet
            self.ec2_client.create_tags(
                Resources=[public_subnet_id],
                Tags=[
                    {'Key': 'Name', 'Value': f'{db_instance_identifier}-public-subnet-{i+1}'},
                    {'Key': 'Type', 'Value': 'public'},
                    {'Key': 'Project', 'Value': db_instance_identifier}
                ]
            )
            public_subnet_ids.append(public_subnet_id)
            
            # Private subnet for each AZ (for RDS, Lambda, etc.)
            private_cidr = f"10.0.{i*2+2}.0/24"  # 10.0.2.0/24, 10.0.4.0/24
            private_subnet_id = self.create_subnet(vpc_id, private_cidr, az)
            
            # Tag as private subnet
            self.ec2_client.create_tags(
                Resources=[private_subnet_id],
                Tags=[
                    {'Key': 'Name', 'Value': f'{db_instance_identifier}-private-subnet-{i+1}'},
                    {'Key': 'Type', 'Value': 'private'},
                    {'Key': 'Project', 'Value': db_instance_identifier}
                ]
            )
            private_subnet_ids.append(private_subnet_id)

        # Step 3: Create Internet Gateway and attach to VPC
        print("\n3. Creating Internet Gateway...")
        igw_id = self.create_internet_gateway(vpc_id, instance_identifier=db_instance_identifier)

        # Step 4: Create route tables for public subnets
        print("\n4. Creating public route tables...")
        public_route_table_ids = []
        for i, public_subnet_id in enumerate(public_subnet_ids):
            public_rt_id = self.create_route_table(vpc_id, public_subnet_id, instance_identifier=db_instance_identifier, is_public=True)
            self.create_route(public_rt_id, gateway_id=igw_id)
            public_route_table_ids.append(public_rt_id)

        # Step 5: Create NAT Gateway in first public subnet (for private subnet internet access)
        print("\n5. Creating NAT Gateway...")
        nat_gateway_id = self.create_nat_gateway(public_subnet_ids[0], db_instance_identifier)

        # Step 6: Create route tables for private subnets
        print("\n6. Creating private route tables...")
        private_route_table_ids = []
        for i, private_subnet_id in enumerate(private_subnet_ids):
            private_rt_id = self.create_route_table(vpc_id, private_subnet_id, instance_identifier=db_instance_identifier, is_public=False)
            self.create_route(private_rt_id, nat_gateway_id=nat_gateway_id)
            private_route_table_ids.append(private_rt_id)

        # Step 7: Create security group
        print("\n7. Creating security group...")
        security_group_id = self.create_rds_postgres_security_group(vpc_id, db_instance_identifier)

        # Step 8: Create RDS subnet group (using only private subnets)
        print("\n8. Creating RDS subnet group...")
        subnet_group_name = f"{db_instance_identifier}-subnet-group"
        rds_subnet_group = self.create_rds_subnet_group(subnet_group_name, private_subnet_ids)
        
        print(f"\n=== Infrastructure Creation Complete ===")
        print(f"VPC ID: {vpc_id}")
        print(f"Public Subnet IDs: {public_subnet_ids}")
        print(f"Private Subnet IDs: {private_subnet_ids}")
        print(f"Internet Gateway ID: {igw_id}")
        print(f"NAT Gateway ID: {nat_gateway_id}")
        print(f"Security Group ID: {security_group_id}")
        print(f"RDS Subnet Group: {rds_subnet_group}")
        
        return {
            'vpc_id': vpc_id,
            'public_subnet_ids': public_subnet_ids,
            'private_subnet_ids': private_subnet_ids,
            'internet_gateway_id': igw_id,
            'nat_gateway_id': nat_gateway_id,
            'security_group_id': security_group_id,
            'rds_subnet_group': rds_subnet_group,
        }

def main():
    if len(sys.argv) < 2:
        print("Usage: python run_vpc.py <method> [instance_identifier]")
        print("Methods: infrastructure, cleanup, create_vpc")
        return

    method = sys.argv[1]
    instance_id = sys.argv[2] if len(sys.argv) > 2 else "test-instance"
    
    vpc_creator = VPCInstanceCreator()
    
    if method == "infrastructure":
        print(f"Creating complete infrastructure for: {instance_id}")
        try:
            infrastructure = vpc_creator.create_complete_infrastructure(instance_id)
            print("✅ Infrastructure created successfully!")
            print(f"VPC ID: {infrastructure['vpc_id']}")
        except Exception as e:
            print(f"❌ Failed: {e}")
            
    elif method == "cleanup":
        print(f"Cleaning up infrastructure for: {instance_id}")
        vpc_creator.cleanup_existing_infrastructure(instance_id)
        print("✅ Cleanup completed!")
        
    elif method == "create_vpc":
        print(f"Creating VPC for: {instance_id}")
        vpc_id = vpc_creator.create_vpc(instance_identifier=instance_id)
        print(f"✅ VPC created: {vpc_id}")
        
    else:
        print(f"Unknown method: {method}")

if __name__ == "__main__":
    main()