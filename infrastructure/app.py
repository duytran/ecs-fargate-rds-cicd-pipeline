#!/usr/bin/env python3
import os

import aws_cdk as cdk

from infrastructure.ecr_stack import EcrStack
from infrastructure.vpc_stack import VpcStack
from infrastructure.ecs_stack import ElasticContainerStack

app = cdk.App()
ecr = EcrStack(app, EcrStack.__name__)
vpc = VpcStack(app, VpcStack.__name__)
ElasticContainerStack(
    app, ElasticContainerStack.__name__, vpc=vpc.vpc, repository=ecr.repository
)


app.synth()
