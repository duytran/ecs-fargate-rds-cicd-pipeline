from aws_cdk import Stack
from aws_cdk import aws_ec2 as ec2

from constructs import Construct

from infrastructure.config import PROJECT_NAME


class VpcStack(Stack):
    def __init__(self, scope: Construct, construct_id: str, **kwargs):
        super().__init__(scope, construct_id, **kwargs)

        self.vpc = ec2.Vpc(
            self,
            f"{PROJECT_NAME}-Vpc",
            cidr="10.0.0.0/16",
            max_azs=2,
            subnet_configuration=[
                ec2.SubnetConfiguration(
                    name="public-1", cidr_mask=24, subnet_type=ec2.SubnetType.PUBLIC
                ),
                ec2.SubnetConfiguration(
                    name="private-1",
                    cidr_mask=24,
                    subnet_type=ec2.SubnetType.PRIVATE_WITH_NAT,
                ),
            ],
        )
