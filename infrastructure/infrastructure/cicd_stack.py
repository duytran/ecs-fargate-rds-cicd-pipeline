from aws_cdk import Aws, Stack, SecretValue, DefaultStackSynthesizer, RemovalPolicy
from aws_cdk import aws_codepipeline as codepipeline
from aws_cdk import aws_codepipeline_actions as cpactions
from aws_cdk import aws_codebuild as codebuild
from aws_cdk import aws_iam as iam
from aws_cdk import aws_ecr as ecr
from constructs import Construct

from infrastructure.config import PROJECT_NAME


class CiCdStack(Stack):
    def __init__(self, scope: Construct, construct_id: str, **kwargs):
        super().__init__(scope, construct_id)
        # ----------------------------------------------------------------------
        repository: ecr.IRepository = kwargs["repository"]
        # container = kwargs["container"]
        # vpc = kwargs["vpc"]

        # ----------------------------------------------------------------------
        # Configuration
        secret_config = {"id": "githubtoken", "arn": ""}
        github_config = {
            "owner": "duytran",
            "repo": "ecs-fargate-rds-cicd-pipeline",
            "branch": "main",
        }

        # ----------------------------------------------------------------------
        # Artifact Bucket
        source_output = codepipeline.Artifact(f"{PROJECT_NAME}SourceOutput")
        # unittest_output = codepipeline.Artifact(f"{PROJECT_NAME}UnittestOuput")
        docker_build_output = codepipeline.Artifact(f"{PROJECT_NAME}DockerBuildOuput")
        # cdk_build_output = codepipeline.Artifact(f"{PROJECT_NAME}CDKBuildOutput")

        # ----------------------------------------------------------------------
        # Code build project
        # Unit test
        # unittest_cb_pj = codebuild.PipelineProject(
        #     self,
        #     f"{PROJECT_NAME}UnittestCodeBuildProject",
        #     project_name=f"{PROJECT_NAME}-unittest-codebuild-project",
        #     environment=codebuild.BuildEnvironment(
        #         build_image=codebuild.LinuxBuildImage.STANDARD_5_0
        #     ),
        #     build_spec=self.get_unittest_build_spec(),
        # )

        docker_cb_pj = codebuild.PipelineProject(
            self,
            f"{PROJECT_NAME}DockerCodeBuildProject",
            project_name=f"{PROJECT_NAME}-docker-codebuild-project",
            environment=codebuild.BuildEnvironment(
                build_image=codebuild.LinuxBuildImage.STANDARD_5_0
            ),
            build_spec=self.get_docker_build_spec(),
            environment_variables={
                "REPOSITORY_URI": {
                    "value": repository.repository_uri,
                },
                "AWS_ACCOUNT_ID": {
                    "value": Aws.ACCOUNT_ID,
                },
                "AWS_STACK_REGION": {
                    "value": Aws.REGION,
                },
                "CONTAINER_NAME": {
                    "value": "vulture-container-name"  # container.container_name,
                },
            },
        )

        # grant access repository
        repository.grant_pull_push(docker_cb_pj)

        # # Code Build CDK template
        # cdk_cb_pj = codebuild.PipelineProject(
        #     self,
        #     f"{PROJECT_NAME}CodeBuildCDK",
        #     project_name=f"{PROJECT_NAME}-cdk-codebuild-project",
        #     environment=codebuild.BuildEnvironment(
        #         build_image=codebuild.LinuxBuildImage.STANDARD_5_0
        #     ),
        #     build_spec=self.get_cdk_build_spec(),
        # )

        # # create permission to assume the file asset publishing role
        # assets_publishing_permissions = iam.PolicyStatement(
        #     sid="extraPermissionsRequiredForPublishingAssets",
        #     effect=iam.Effect.ALLOW,
        #     actions=["sts:AssumeRole"],
        #     resources=[
        #         f"arn:aws:iam::{Aws.ACCOUNT_ID}:role/cdk-{DefaultStackSynthesizer.DEFAULT_QUALIFIER}-file-publishing-role-{Aws.ACCOUNT_ID}-{Aws.REGION}"
        #     ],
        # )
        # # attach the permission to the role created with build cdk job
        # cdk_cb_pj.add_to_role_policy(assets_publishing_permissions)

        # ----------------------------------------------------------------------
        # Codebuild action

        # Github connection action
        source_action = cpactions.GitHubSourceAction(
            action_name="Github",
            owner=github_config.get("owner"),
            repo=github_config.get("repo"),
            branch=github_config.get("branch"),
            output=source_output,
            oauth_token=SecretValue.secrets_manager(secret_config.get("id")),
        )

        # # Build action
        # unittest_build_action = cpactions.CodeBuildAction(
        #     environment_variables={
        #         "CODE_COMMIT_ID": {"value": source_action.variables.commit_id}
        #     },
        #     action_name="DoUnitTest",
        #     project=unittest_cb_pj,
        #     input=source_output,
        #     outputs=[unittest_output],
        # )

        # Docker build action
        docker_build_action = cpactions.CodeBuildAction(
            action_name="BuildDockerImage",
            project=docker_cb_pj,
            input=source_output,
            outputs=[docker_build_output],
        )

        # # CDK build action
        # cdk_build_action = cpactions.CodeBuildAction(
        #     action_name="BuildCfnTemplate",
        #     project=cdk_cb_pj,
        #     input=source_output,
        #     outputs=[cdk_build_output],
        # )

        # # Manual approval action
        # manual_approval_action = cpactions.ManualApprovalAction(action_name="Approve")

        # ----------------------------------------------------------------------
        # Codedeploy

        # ----------------------------------------------------------------------
        # Finally create pipeline
        # pipeline
        pipeline = codepipeline.Pipeline(
            self,
            "CicdPipelineDemo",
            pipeline_name="CicdPipelineDemo",
            cross_account_keys=False,
            stages=[
                {"stageName": "Source", "actions": [source_action]},
                # {"stageName": "UnitTest", "actions": [unittest_build_action]},
                {"stageName": "BuildImage", "actions": [docker_build_action]},
                # {"stageName": "Approve", "actions": [manual_approval_action]},
                # {"stageName": "DeployDev", "actions": [deploy_dev]},
            ],
        )

        # destroy artifact bucket when deleling pipeline
        pipeline.artifact_bucket.apply_removal_policy(RemovalPolicy.DESTROY)

    def get_cdk_build_spec(self):
        return codebuild.BuildSpec.from_object(
            {
                "version": "0.2",
                "phases": {
                    "install": {
                        "commands": [
                            "npm install -g aws-cdk",
                            "npm install -g cdk-assets",
                            "pip install -r requirements.txt",
                        ]
                    },
                    "build": {"commands": ["cdk synth --no-lookups"]},
                    "post_build": {
                        "commands": [
                            "for FILE in cdk.out/*.assets.json; do cdk-assets -p $FILE publish; done"
                        ]
                    },
                },
                "artifacts": {
                    "base-directory": "cdk.out",
                    "files": ["*.template.json"],
                },
            }
        )

    def get_unittest_build_spec(self):
        return codebuild.BuildSpec.from_object(
            {
                "version": "0.2",
                "phases": {
                    "install": {
                        "commands": [
                            "npm install",
                            "echo $CODE_COMMIT_ID",
                        ]
                    },
                    "build": {"commands": ["npm test"]},
                },
                "artifacts": {},
            },
        )

    def get_docker_build_spec(self):
        return codebuild.BuildSpec.from_object(
            {
                "version": "0.2",
                "env": {"shell": "bash"},
                "phases": {
                    "pre_build": {
                        "commands": [
                            "echo logging in to AWS ECR",
                            "aws --version",
                            "echo $AWS_STACK_REGION",
                            "echo $CONTAINER_NAME",
                            "aws ecr get-login-password --region ${AWS_STACK_REGION} | docker login --username AWS --password-stdin ${AWS_ACCOUNT_ID}.dkr.ecr.${AWS_STACK_REGION}.amazonaws.com",
                            "COMMIT_HASH=$(echo $CODEBUILD_RESOLVED_SOURCE_VERSION | cut -c 1-7)",
                            "echo $COMMIT_HASH",
                            "IMAGE_TAG=${COMMIT_HASH:=latest}",
                            "echo $IMAGE_TAG",
                        ],
                    },
                    "build": {
                        "commands": [
                            "echo Build started on `date`",
                            "echo Build Docker image",
                            "docker build -f ${CODEBUILD_SRC_DIR}/backend/Dockerfile -t ${REPOSITORY_URI}:latest ./backend",
                            'echo Running "docker tag ${REPOSITORY_URI}:latest ${REPOSITORY_URI}:${IMAGE_TAG}"',
                            "docker tag ${REPOSITORY_URI}:latest ${REPOSITORY_URI}:${IMAGE_TAG}",
                        ],
                    },
                    "post_build": {
                        "commands": [
                            "echo Build completed on `date`",
                            "echo Push Docker image",
                            "docker push ${REPOSITORY_URI}:latest",
                            "docker push ${REPOSITORY_URI}:${IMAGE_TAG}",
                            'printf "[{\\"name\\": \\"$CONTAINER_NAME\\", \\"imageUri\\": \\"$REPOSITORY_URI:$IMAGE_TAG\\"}]" > docker_image_definition.json',
                        ]
                    },
                },
                "artifacts": {"files": ["docker_image_definition.json"]},
            }
        )
