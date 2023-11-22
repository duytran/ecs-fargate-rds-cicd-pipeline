from aws_cdk import Stack, Duration, RemovalPolicy, CfnOutput
from aws_cdk import aws_ecs as ecs
from aws_cdk import aws_ec2 as ec2
from aws_cdk import aws_ecr as ecr
from aws_cdk import aws_elasticloadbalancingv2 as elbv2
from aws_cdk import aws_iam as iam
from aws_cdk import aws_logs as logs

from constructs import Construct

from infrastructure.config import PROJECT_NAME, CONTAINER_PORT


class ElasticContainerStack(Stack):
    def __init__(self, scope: Construct, construct_id: str, **kwargs):
        super().__init__(scope, construct_id)

        vpc = kwargs["vpc"]
        repository = kwargs["repository"]

        # Create Cloudwatch log group
        log_group = logs.LogGroup(
            self,
            f"{PROJECT_NAME}LogGroup",
            log_group_name=f"{PROJECT_NAME}-ecs-cdk-log",
            retention=logs.RetentionDays("ONE_YEAR"),
            removal_policy=RemovalPolicy("DESTROY"),
        )

        alb_sg = ec2.SecurityGroup(
            self,
            f"{PROJECT_NAME}AlbSG",
            vpc=vpc,
            allow_all_outbound=None,
            description=f"{PROJECT_NAME} ALB Security Group",
            security_group_name=f"{PROJECT_NAME}-ecs-cdk-alb-sg",
        )

        alb_sg.add_ingress_rule(peer=ec2.Peer.any_ipv4(), connection=ec2.Port.tcp(80))

        # Setup ALB
        alb = elbv2.ApplicationLoadBalancer(
            self,
            f"{PROJECT_NAME}ALB",
            vpc=vpc,
            internet_facing=True,
            security_group=alb_sg,
        )

        # Setup ECS Cluster
        ecs_cluster = ecs.Cluster(
            self,
            f"{PROJECT_NAME}ECSCluster",
            vpc=vpc,
            cluster_name=f"{PROJECT_NAME}-ecs-cdk-cluster",
        )

        # ECS Execution Role - Grants ECS agent to call AWS APIs
        ecs_execution_role = iam.Role(
            self,
            f"{PROJECT_NAME}ECSExecutionRole",
            assumed_by=iam.ServicePrincipal("ecs-tasks.amazonaws.com"),
            role_name=f"{PROJECT_NAME}-ecs-cdk-execution-role",
        )

        # Setup Role Permissions
        ecs_execution_role.add_to_policy(
            iam.PolicyStatement(
                effect=iam.Effect.ALLOW,
                actions=[
                    "elasticloadbalancing:DeregisterInstancesFromLoadBalancer",
                    "elasticloadbalancing:DeregisterTargets",
                    "elasticloadbalancing:Describe*",
                    "elasticloadbalancing:RegisterInstancesWithLoadBalancer",
                    "elasticloadbalancing:RegisterTargets",
                    "ec2:Describe*",
                    "ec2:AuthorizeSecurityGroupIngress",
                    "sts:AssumeRole",
                ],
                resources=["*"],
            )
        )

        # ECS Task Role - Grants containers in task permission to AWS APIs
        ecs_task_role = iam.Role(
            self,
            f"{PROJECT_NAME}ECSTaskRole",
            assumed_by=iam.ServicePrincipal("ecs-tasks.amazonaws.com"),
            role_name="ecs-cdk-task-role",
        )

        # Setup Role Permissions
        ecs_task_role.add_to_policy(
            iam.PolicyStatement(
                effect=iam.Effect.ALLOW,
                actions=[
                    "ecr:GetAuthorizationToken",
                    "ecr:BatchCheckLayerAvailability",
                    "ecr:GetDownloadUrlForLayer",
                    "ecr:BatchGetImage",
                    "logs:CreateLogStream",
                    "logs:PutLogEvents",
                ],
                resources=["*"],
            )
        )

        # Setup Fargate Task Definition
        fargate_taskdef = ecs.FargateTaskDefinition(
            self,
            f"{PROJECT_NAME}ECSFargateTask",
            memory_limit_mib=512,
            cpu=256,
            execution_role=ecs_execution_role,
            task_role=ecs_task_role,
            family=f"{PROJECT_NAME}-ecs-cdk-taskdef",
        )

        # Add Container Info to Task
        self.ecs_container = fargate_taskdef.add_container(
            f"{PROJECT_NAME}FargateImage",
            image=ecs.EcrImage.from_ecr_repository(repository),
            logging=ecs.LogDriver.aws_logs(
                stream_prefix=f"{PROJECT_NAME}-ecs-fargate-logs", log_group=log_group
            ),
        )

        # Setup Port Mappings
        self.ecs_container.add_port_mappings(
            ecs.PortMapping(
                container_port=CONTAINER_PORT, host_port=80, protocol=ecs.Protocol.TCP
            )
        )

        # Setup Fargate Service
        fargate_service = ecs.FargateService(
            self,
            f"{PROJECT_NAME}FargateService",
            task_definition=fargate_taskdef,
            cluster=ecs_cluster,
            desired_count=1,
            service_name=f"{PROJECT_NAME}-ecs-cdk-service",
        )

        # Setup ALB Listener
        alb_listener = alb.add_listener(
            f"{PROJECT_NAME}Listener",
            port=80,
            open=False,
            protocol=elbv2.ApplicationProtocol.HTTP,
        )

        # Attach ALB to ECS Service
        alb_listener.add_targets(
            f"{PROJECT_NAME}ECS", port=80, targets=[fargate_service]
        )

        CfnOutput(
            self, f"{PROJECT_NAME}LoadBalancerDNS", value=alb.load_balancer_dns_name
        )
