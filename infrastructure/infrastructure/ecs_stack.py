from aws_cdk import Stack, Duration
from aws_cdk import aws_ecs as ecs
from aws_cdk import aws_ec2 as ec2
from aws_cdk import aws_ecr as ecr
from aws_cdk import aws_elasticloadbalancingv2 as elbv2

from constructs import Construct

from infrastructure.config import PROJECT_NAME, CONTAINER_PORT


class ElasticContainerStack(Stack):
    def __init__(self, scope: Construct, construct_id: str, **kwargs):
        super().__init__(scope, construct_id)

        # ----------------------------------------------------------------------
        # Create ECS Cluster
        self.cluster = ecs.Cluster(
            self,
            f"{PROJECT_NAME}-Cluster",
            vpc=kwargs["vpc"],
            cluster_name=f"{PROJECT_NAME}-Cluster",
            container_insights=True,
        )

        # # ----------------------------------------------------------------------
        # # Create Security group for Application load balancer
        # self.alb_sg = ec2.SecurityGroup(
        #     self,
        #     f"{PROJECT_NAME}-Security-Group-Load-Balancer",
        #     vpc=kwargs["vpc"],
        #     allow_all_outbound=True,
        # )

        # self.alb_sg.add_ingress_rule(ec2.Peer.any_ipv4(), ec2.Port.tcp(CONTAINER_PORT))

        # # ----------------------------------------------------------------------
        # # Create Application load balancer
        # self.load_balancer = elbv2.ApplicationLoadBalancer(
        #     self,
        #     f"{PROJECT_NAME}-Ecs-Alb",
        #     vpc=kwargs["vpc"],
        #     load_balancer_name=f"{PROJECT_NAME}-Ecs-Alb",
        #     internet_facing=True,
        #     idle_timeout=Duration.minutes(10),
        #     security_group=self.alb_sg,
        #     http2_enabled=False,
        #     deletion_protection=False,
        # )

        # # Load balancer add listener
        # self.http_listener = self.load_balancer.add_listener(
        #     "http listener",
        #     port=80,
        #     open=True,
        # )

        # # listener add target
        # self.target_group = self.http_listener.add_targets(
        #     "tcp-listener-target",
        #     target_group_name="tcp-target-ecs-service",
        #     protocol=elbv2.ApplicationProtocol.HTTP,
        #     protocol_version=elbv2.ApplicationProtocolVersion.HTTP1,
        # )

        # ----------------------------------------------------------------------
        # Create task defination

        self.task_defination = ecs.FargateTaskDefinition(
            self,
            f"{PROJECT_NAME}-Fargate-Task-Definition",
            runtime_platform=ecs.RuntimePlatform(
                cpu_architecture=ecs.CpuArchitecture.ARM64,
                operating_system_family=ecs.OperatingSystemFamily.LINUX,
            ),
        )

        self.container = self.task_defination.add_container(
            f"{PROJECT_NAME}-Web-Server",
            image=ecs.EcrImage.from_ecr_repository(kwargs["repository"]),
        )

        self.container.add_port_mappings(ecs.PortMapping(container_port=CONTAINER_PORT))

        # self.http_sg = ec2.SecurityGroup(
        #     self, f"{PROJECT_NAME}-Security-Group-Http", vpc=kwargs["vpc"]
        # )

        # self.http_sg.add_ingress_rule(
        #     ec2.Peer.security_group_id(self.alb_sg.security_group_id),
        #     ec2.Port.tcp(CONTAINER_PORT),
        #     "Allow inbound connections from ALB",
        # )

        # ----------------------------------------------------------------------
        # Create service

        self.fargate_service = ecs.FargateService(
            self,
            f"{PROJECT_NAME}-Fargate-Service",
            cluster=self.cluster,
            assign_public_ip=False,
            task_definition=self.task_defination,
            # security_groups=[self.http_sg],
            desired_count=1,
        )

        # self.target_group.add_target(self.fargate_service)
