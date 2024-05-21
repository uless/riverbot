from constructs import Construct
from aws_cdk import (
    Duration,
    Stack,
    aws_ecs as ecs,
    aws_ecr as ecr,
    aws_ec2 as ec2,
    aws_secretsmanager as secretsmanager,
    aws_iam as iam,
    SecretValue
)
import os


class AppStack(Stack):

    def __init__(self, scope: Construct, construct_id: str, imports: dict, **kwargs) -> None:
        super().__init__(scope, construct_id, **kwargs)

        # Get the secret value from an environment variable
        secret_value = os.environ.get("OPENAI_API_KEY")
        if not secret_value:
            raise ValueError("OPENAI_API_KEY environment variable is not set")
        

        # Create a VPC for the Fargate cluster
        vpc = ec2.Vpc(self, "WaterbotVPC", max_azs=2)

        # Get the repository URL
        repository = imports["repository"]

        # Create the Fargate cluster
        cluster = ecs.Cluster(
            self, "WaterbotFargateCluster",
            vpc=vpc,
            cluster_name="WaterbotFargateCluster"
        )

        # !!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!! #
        #         We will likely want different approach   #
        #         for production as this will have secret  #
        #         in plaintext of CDK outputs              #
        # !!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!! #
        # Create a Secrets Manager secret
        secret = secretsmanager.Secret(
            self, "OpenAI-APIKey",
            secret_name="openai-api-key",
            description="Open API Key",
            secret_string_value=SecretValue.unsafe_plain_text(secret_value)
        )

        # Create a task definition for the Fargate service
        task_definition = ecs.FargateTaskDefinition(
            self, "WaterbotTaskDefinition",
            memory_limit_mib=512,
            cpu=256,
        )
        # Grant the task permission to log to CloudWatch
        task_definition.add_to_task_role_policy(
            iam.PolicyStatement(
                actions=[
                    "logs:CreateLogGroup",
                    "logs:CreateLogStream",
                    "logs:PutLogEvents",
                ],
                resources=["*"],
            )
        )

        # Grant the task permission to invoke Amazon Bedrock models
        task_definition.add_to_task_role_policy(
            iam.PolicyStatement(
                actions=["bedrock:InvokeModel"],
                resources=["*"],  # Replace with appropriate resource ARNs
            )
        )

        # Grant the task permission to access the secret
        task_definition.add_to_task_role_policy(
            iam.PolicyStatement(
                actions=["secretsmanager:GetSecretValue"],
                resources=[secret.secret_arn]
            )
        )

        # Create a container in the task definition & inject the secret into the container as an environment variable
        container = task_definition.add_container(
            "WaterbotAppContainer",
            image=ecs.ContainerImage.from_ecr_repository(repository, tag="latest"),
            port_mappings=[ecs.PortMapping(container_port=8000)],
            secrets={
                "OPENAI_API_KEY": ecs.Secret.from_secrets_manager(secret)
            }
        )

        # Create a Fargate service
        service = ecs.FargateService(
            self, "WaterbotFargateService",
            cluster=cluster,
            task_definition=task_definition,
            desired_count=1,
        )

