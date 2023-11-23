from aws_cdk import Stack, SecretValue
from aws_cdk import aws_rds as rds
from aws_cdk import aws_ec2 as ec2

from constructs import Construct

from src.config import PROJECT_NAME


class RdsStack(Stack):
    def __init__(self, scope: Construct, construct_id: str, **kwargs):
        super().__init__(scope, construct_id)

        vpc = kwargs["vpc"]
        db_username = kwargs["db_username"]
        db_password = kwargs["db_password"]
        db_name = kwargs["db_name"]
        db_security_group = kwargs["db_security_group"]

        self.db = rds.DatabaseInstance(
            self,
            f"{PROJECT_NAME}Database",
            engine=rds.DatabaseInstanceEngine.POSTGRES,
            vpc=vpc,
            credentials={
                "username": db_username,
                "password": SecretValue.plain_text(db_password),
            },
            database_name=db_name,
            storage_type=rds.StorageType.STANDARD,
            instance_type=ec2.InstanceType.of(
                ec2.InstanceClass.BURSTABLE3, ec2.InstanceSize.SMALL
            ),
            parameter_group=rds.ParameterGroup(
                self, f"{PROJECT_NAME}PostgresInstanceGroup", "postgre14"
            ),
            security_groups=db_security_group,
        )
