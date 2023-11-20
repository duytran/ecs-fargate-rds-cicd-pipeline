from aws_cdk import Stack, Duration, RemovalPolicy, CfnOutput
from aws_cdk import aws_ecs as ecs
from aws_cdk import aws_ec2 as ec2
from aws_cdk import aws_ecr as ecr
from aws_cdk import aws_elasticloadbalancingv2 as elbv2
from aws_cdk import aws_iam as iam
from aws_cdk import aws_logs as logs

from constructs import Construct


class ECSFargateStack(Stack):
    def __init__(self, scope: Construct, id: str, **kwargs) -> None:
        super().__init__(scope, id, *kwargs)

        # If wanted you can update this and use it.
        custom_vpn_connection = ec2.Peer.ipv4("10.0.0.0/16")

        # Setup IAM user for logs
        vpc_flow_role = iam.Role(
            self,
            "FlowLog",
            assumed_by=iam.ServicePrincipal("vpc-flow-logs.amazonaws.com"),
        )

        # Create Cloudwatch log group
        log_group = logs.LogGroup(
            self,
            "LogGroup",
            log_group_name="ecs-cdk-log",
            retention=logs.RetentionDays("ONE_YEAR"),
            removal_policy=RemovalPolicy("DESTROY"),
        )

        vpc_log_group = logs.LogGroup(
            self,
            "VPCLogGroup",
            log_group_name="ecs-cdk-vpc-flow",
            retention=logs.RetentionDays("ONE_YEAR"),
            removal_policy=RemovalPolicy("DESTROY"),
        )

        # Setup VPC resource
        vpc = ec2.Vpc(self, "ec2-sg-vpc", cidr="10.66.0.0/16", max_azs=2)

        # Setup VPC flow logs
        vpc_log = ec2.CfnFlowLog(
            self,
            "FlowLogs",
            resource_id=vpc.vpc_id,
            resource_type="VPC",
            traffic_type="ALL",
            deliver_logs_permission_arn=vpc_flow_role.role_arn,
            log_destination_type="cloud-watch-logs",
            log_group_name=vpc_log_group.log_group_name,
        )

        # Setup Security Group in VPC
        vpc_sg = ec2.SecurityGroup(
            self,
            "EcSSG",
            vpc=vpc,
            allow_all_outbound=None,
            description="Security Group created by CDK examples repo",
            security_group_name="ecs-vpc-sg-cdk",
        )

        # Add Rules to Security Group - Just test for ssh for example
        vpc_sg.add_ingress_rule(peer=custom_vpn_connection, connection=ec2.Port.tcp(22))

        # ALB Security Group
        alb_sg = ec2.SecurityGroup(
            self,
            "AlbSG",
            vpc=vpc,
            allow_all_outbound=None,
            description="Security Group created by CDK examples repo",
            security_group_name="ecs-cdk-alb",
        )

        alb_sg.add_ingress_rule(peer=custom_vpn_connection, connection=ec2.Port.tcp(80))

        # Setup ALB
        alb = elbv2.ApplicationLoadBalancer(
            self, "ALB", vpc=vpc, internet_facing=True, security_group=alb_sg
        )

        # Default Target Group
        fargate_tg = elbv2.ApplicationTargetGroup(
            self,
            "DefaultTargetGroup",
            port=80,
            protocol=elbv2.ApplicationProtocol.HTTP,
            vpc=vpc,
        )

        # Setup ECS Cluster
        ecs_cluster = ecs.Cluster(
            self, "ECSCluster", vpc=vpc, cluster_name="ecs-cdk-example"
        )

        # ECS Execution Role - Grants ECS agent to call AWS APIs
        ecs_execution_role = iam.Role(
            self,
            "ECSExecutionRole",
            assumed_by=iam.ServicePrincipal("ecs-tasks.amazonaws.com"),
            role_name="ecs-cdk-execution-role",
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
            "ECSTaskRole",
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
            "ECSFargateTask",
            memory_limit_mib=512,
            cpu=256,
            execution_role=ecs_execution_role,
            task_role=ecs_task_role,
            family="ecs-cdk-taskdef",
        )

        # Add Container Info to Task
        ecs_container = fargate_taskdef.add_container(
            "FargateImage",
            image=ecs.EcrImage.from_ecr_repository(kwargs["repository"]),
            logging=ecs.LogDriver.aws_logs(
                stream_prefix="ecs-fargate-logs", log_group=log_group
            ),
        )

        # Setup Port Mappings
        ecs_container.add_port_mappings(
            ecs.PortMapping(container_port=80, host_port=80, protocol=ecs.Protocol.TCP)
        )

        # Setup Fargate Service
        fargate_service = ecs.FargateService(
            self,
            "FargateService",
            task_definition=fargate_taskdef,
            cluster=ecs_cluster,
            desired_count=1,
            service_name="ecs-cdk-service",
        )

        # Setup ALB Listener
        alb_listener = alb.add_listener(
            "Listener", port=80, open=False, protocol=elbv2.ApplicationProtocol.HTTP
        )

        # Attach ALB to ECS Service
        alb_listener.add_targets("ECS", port=80, targets=[fargate_service])

        CfnOutput(self, "LoadBalancerDNS", value=alb.load_balancer_dns_name)
