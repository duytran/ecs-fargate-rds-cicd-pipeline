#!/usr/bin/env python3
import os

import aws_cdk as cdk

from src.ecr_stack import EcrStack
from src.vpc_stack import VpcStack
from src.ecs_stack import ElasticContainerStack
from src.cicd_stack import CiCdStack

app = cdk.App()
ecr = EcrStack(app, EcrStack.__name__)
vpc = VpcStack(app, VpcStack.__name__)
# ecs = ElasticContainerStack(
#     app, ElasticContainerStack.__name__, vpc=vpc.vpc, repository=ecr.repository
# )
CiCdStack(
    # app, CiCdStack.__name__, repository=ecr.repository, container=ecs.ecs_container
    app,
    CiCdStack.__name__,
    repository=ecr.repository,
)


app.synth()
