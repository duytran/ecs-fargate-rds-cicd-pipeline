from aws_cdk import Stack, RemovalPolicy
from aws_cdk import aws_ecr as ecr
from constructs import Construct

from infrastructure.config import PROJECT_NAME


class EcrStack(Stack):
    def __init__(self, scope: Construct, construct_id: str, **kwargs):
        super().__init__(scope, construct_id, **kwargs)

        self.repository = ecr.Repository(
            self,
            f"{PROJECT_NAME}-Repository",
            image_scan_on_push=True,
            removal_policy=RemovalPolicy.DESTROY,
        )
