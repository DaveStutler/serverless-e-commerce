import boto3
import os

class EC2InstanceCreator:
    """ 
    Create EC2 instances and related resources 
    - 1. VPC and Network Setup
        * Make sure to get the correct subnet for the EC2 (private/public)
        * Configure correct security groups for inbound / outbound rules (SSH, HTTP/HTTPs)
        * Key pairs for SSH access (if not existing, create new)
        * Elastic IPs (if needed)
    - 2. EC2 Instance Setup
        * Define instance type, AMI, storage, tags
        * User data scripts for bootstrapping
    - 3. Additional Configurations
        * IAM roles and policies
        * Monitoring and logging (CloudWatch)
    - 4. Cleanup
        * Terminate instances
        * Release Elastic IPs
        * Delete security groups, key pairs if created

    """
    def __init__(self):
        self.ec2_client = boto3.client("ec2")
    
    def create_ec2_instance(self):
        pass