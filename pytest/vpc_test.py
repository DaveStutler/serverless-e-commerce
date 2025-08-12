import boto3
from botocore.exceptions import ClientError
import unittest
import sys
import os
from moto import mock_aws

from vpc.custom_vpc import VPCInstanceCreator

class TestVPCInstanceCreator(unittest.TestCase):
    """Unit tests for VPCInstanceCreator class using moto mocks"""

    @mock_aws
    def setUp(self):
        """Set up test fixtures before each test method"""
        # Initialize VPC creator with mocked AWS
        self.vpc_creator = VPCInstanceCreator()
        self.test_instance_id = "test-instance"

    @mock_aws
    def test_create_vpc(self):
        """Test VPC creation"""
        vpc_id = self.vpc_creator.create_vpc(instance_identifier=self.test_instance_id)
        
        # Verify VPC was created
        self.assertIsNotNone(vpc_id)
        self.assertTrue(vpc_id.startswith('vpc-'))
        
        # Verify VPC properties using boto3 client
        ec2_client = boto3.client('ec2', region_name='us-east-1')
        vpcs = ec2_client.describe_vpcs(VpcIds=[vpc_id])['Vpcs']
        self.assertEqual(len(vpcs), 1)
        self.assertEqual(vpcs[0]['CidrBlock'], '10.0.0.0/16')

    @mock_aws
    def test_create_subnet(self):
        """Test subnet creation"""
        # First create a VPC
        vpc_id = self.vpc_creator.create_vpc(instance_identifier=self.test_instance_id)
        
        # Get availability zones
        azs = self.vpc_creator.get_availability_zones()
        self.assertGreaterEqual(len(azs), 1)
        
        # Create subnet
        subnet_id = self.vpc_creator.create_subnet(vpc_id, "10.0.1.0/24", azs[0])
        
        # Verify subnet was created
        self.assertIsNotNone(subnet_id)
        self.assertTrue(subnet_id.startswith('subnet-'))
        
        # Verify subnet properties
        ec2_client = boto3.client('ec2', region_name='us-east-1')
        subnets = ec2_client.describe_subnets(SubnetIds=[subnet_id])['Subnets']
        self.assertEqual(len(subnets), 1)
        self.assertEqual(subnets[0]['CidrBlock'], '10.0.1.0/24')
        self.assertEqual(subnets[0]['VpcId'], vpc_id)

    @mock_aws
    def test_create_internet_gateway(self):
        """Test Internet Gateway creation"""
        # Create VPC first
        vpc_id = self.vpc_creator.create_vpc(instance_identifier=self.test_instance_id)
        
        # Create Internet Gateway
        igw_id = self.vpc_creator.create_internet_gateway(vpc_id, self.test_instance_id)
        
        # Verify IGW was created and attached
        self.assertIsNotNone(igw_id)
        self.assertTrue(igw_id.startswith('igw-'))
        
        # Verify IGW is attached to VPC
        ec2_client = boto3.client('ec2', region_name='us-east-1')
        igws = ec2_client.describe_internet_gateways(InternetGatewayIds=[igw_id])['InternetGateways']
        self.assertEqual(len(igws), 1)
        
        attachments = igws[0]['Attachments']
        self.assertEqual(len(attachments), 1)
        self.assertEqual(attachments[0]['VpcId'], vpc_id)
        self.assertEqual(attachments[0]['State'], 'available')

    @mock_aws
    def test_create_security_group(self):
        """Test security group creation"""
        # Create VPC first
        vpc_id = self.vpc_creator.create_vpc(instance_identifier=self.test_instance_id)
        
        # Create security group
        sg_id = self.vpc_creator.create_rds_postgres_security_group(vpc_id, self.test_instance_id)
        
        # Verify security group was created
        self.assertIsNotNone(sg_id)
        self.assertTrue(sg_id.startswith('sg-'))
        
        # Verify security group properties and rules
        ec2_client = boto3.client('ec2', region_name='us-east-1')
        sgs = ec2_client.describe_security_groups(GroupIds=[sg_id])['SecurityGroups']
        self.assertEqual(len(sgs), 1)
        self.assertEqual(sgs[0]['VpcId'], vpc_id)
        
        # Check inbound rules for PostgreSQL (port 5432)
        rules = sgs[0]['IpPermissions']
        postgres_rule = next((rule for rule in rules if rule['FromPort'] == 5432), None)
        self.assertIsNotNone(postgres_rule)
        self.assertEqual(postgres_rule['ToPort'], 5432)
        self.assertEqual(postgres_rule['IpProtocol'], 'tcp')

    @mock_aws
    def test_create_rds_subnet_group(self):
        """Test RDS subnet group creation"""
        # Create VPC first
        vpc_id = self.vpc_creator.create_vpc(instance_identifier=self.test_instance_id)
        
        # Create subnets in different AZs
        azs = self.vpc_creator.get_availability_zones()
        subnet_ids = []
        for i, az in enumerate(azs[:2]):  # Create 2 subnets for RDS requirement
            subnet_id = self.vpc_creator.create_subnet(vpc_id, f"10.0.{i+1}.0/24", az)
            subnet_ids.append(subnet_id)
        
        # Create RDS subnet group
        subnet_group_name = f"{self.test_instance_id}-subnet-group"
        result = self.vpc_creator.create_rds_subnet_group(subnet_group_name, subnet_ids)
        
        # Verify subnet group was created
        self.assertEqual(result, subnet_group_name)
        
        # Verify using RDS client
        rds_client = boto3.client('rds', region_name='us-east-1')
        subnet_groups = rds_client.describe_db_subnet_groups(
            DBSubnetGroupName=subnet_group_name
        )['DBSubnetGroups']
        self.assertEqual(len(subnet_groups), 1)
        self.assertEqual(subnet_groups[0]['DBSubnetGroupName'], subnet_group_name)
        self.assertEqual(len(subnet_groups[0]['Subnets']), 2)

    @mock_aws
    def test_create_route_table_and_routes(self):
        """Test route table creation and route management"""
        # Create VPC
        vpc_id = self.vpc_creator.create_vpc(instance_identifier=self.test_instance_id)
        
        # Create subnet
        azs = self.vpc_creator.get_availability_zones()
        subnet_id = self.vpc_creator.create_subnet(vpc_id, "10.0.1.0/24", azs[0])
        
        # Create Internet Gateway
        igw_id = self.vpc_creator.create_internet_gateway(vpc_id, self.test_instance_id)
        
        # Create route table
        route_table_id = self.vpc_creator.create_route_table(
            vpc_id, subnet_id, self.test_instance_id, is_public=True
        )
        
        # Verify route table was created
        self.assertIsNotNone(route_table_id)
        self.assertTrue(route_table_id.startswith('rtb-'))
        
        # Create route to Internet Gateway
        self.vpc_creator.create_route(route_table_id, gateway_id=igw_id)
        
        # Verify route table and routes
        ec2_client = boto3.client('ec2', region_name='us-east-1')
        route_tables = ec2_client.describe_route_tables(RouteTableIds=[route_table_id])['RouteTables']
        self.assertEqual(len(route_tables), 1)
        
        # Check that route to IGW exists
        routes = route_tables[0]['Routes']
        igw_route = next((route for route in routes if route.get('GatewayId') == igw_id), None)
        self.assertIsNotNone(igw_route)
        self.assertEqual(igw_route['DestinationCidrBlock'], '0.0.0.0/0')

    @mock_aws
    def test_create_complete_infrastructure(self):
        """Test complete infrastructure creation"""
        # Clean up any existing infrastructure (shouldn't exist in mock, but good practice)
        self.vpc_creator.cleanup_existing_infrastructure(self.test_instance_id)
        
        # Create complete infrastructure
        infrastructure = self.vpc_creator.create_complete_infrastructure(self.test_instance_id)
        
        # Verify return structure
        expected_keys = [
            'vpc_id', 'public_subnet_ids', 'private_subnet_ids', 
            'internet_gateway_id', 'nat_gateway_id', 'security_group_id', 'rds_subnet_group'
        ]
        for key in expected_keys:
            self.assertIn(key, infrastructure)
        
        # Verify VPC
        vpc_id = infrastructure['vpc_id']
        self.assertTrue(vpc_id.startswith('vpc-'))
        
        # Verify subnets
        public_subnets = infrastructure['public_subnet_ids']
        private_subnets = infrastructure['private_subnet_ids']
        self.assertEqual(len(public_subnets), 2)  # Should create 2 public subnets
        self.assertEqual(len(private_subnets), 2)  # Should create 2 private subnets
        
        # Verify all subnets are valid
        all_subnets = public_subnets + private_subnets
        for subnet_id in all_subnets:
            self.assertTrue(subnet_id.startswith('subnet-'))
        
        # Verify Internet Gateway
        igw_id = infrastructure['internet_gateway_id']
        self.assertTrue(igw_id.startswith('igw-'))
        
        # Verify NAT Gateway
        nat_gw_id = infrastructure['nat_gateway_id']
        self.assertTrue(nat_gw_id.startswith('nat-'))
        
        # Verify Security Group
        sg_id = infrastructure['security_group_id']
        self.assertTrue(sg_id.startswith('sg-'))
        
        # Verify RDS Subnet Group
        rds_subnet_group = infrastructure['rds_subnet_group']
        self.assertEqual(rds_subnet_group, f"{self.test_instance_id}-subnet-group")
        
        # Verify infrastructure is properly connected using AWS clients
        ec2_client = boto3.client('ec2', region_name='us-east-1')
        
        # Check VPC exists
        vpcs = ec2_client.describe_vpcs(VpcIds=[vpc_id])['Vpcs']
        self.assertEqual(len(vpcs), 1)
        
        # Check subnets are in correct VPC
        subnets = ec2_client.describe_subnets(SubnetIds=all_subnets)['Subnets']
        for subnet in subnets:
            self.assertEqual(subnet['VpcId'], vpc_id)
        
        # Check Internet Gateway is attached to VPC
        igws = ec2_client.describe_internet_gateways(InternetGatewayIds=[igw_id])['InternetGateways']
        self.assertEqual(len(igws[0]['Attachments']), 1)
        self.assertEqual(igws[0]['Attachments'][0]['VpcId'], vpc_id)

    @mock_aws
    def test_cleanup_infrastructure(self):
        """Test infrastructure cleanup"""
        # First create infrastructure
        infrastructure = self.vpc_creator.create_complete_infrastructure(self.test_instance_id)
        vpc_id = infrastructure['vpc_id']
        
        # Verify infrastructure exists
        ec2_client = boto3.client('ec2', region_name='us-east-1')
        vpcs_before = ec2_client.describe_vpcs(VpcIds=[vpc_id])['Vpcs']
        self.assertEqual(len(vpcs_before), 1)
        
        # Clean up infrastructure
        self.vpc_creator.cleanup_existing_infrastructure(self.test_instance_id)
        
        # Verify VPC is deleted (this should raise an exception in moto)
        with self.assertRaises(ClientError):
            ec2_client.describe_vpcs(VpcIds=[vpc_id])

if __name__ == "__main__":
    unittest.main()   
