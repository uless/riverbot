from constructs import Construct
from aws_cdk import (
    Duration,
    Stack,
    aws_ecs as ecs,
    aws_ecr as ecr,
    aws_ec2 as ec2,
)


class AppStack(Stack):

    def __init__(self, scope: Construct, construct_id: str, imports: dict, **kwargs) -> None:
        super().__init__(scope, construct_id, **kwargs)

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

        # Create a task definition for the Fargate service
        task_definition = ecs.FargateTaskDefinition(
            self, "WaterbotTaskDefinition",
            memory_limit_mib=512,
            cpu=256,
        )

        # Create a container in the task definition
        container = task_definition.add_container(
            "WaterbotAppContainer",
            image=ecs.ContainerImage.from_ecr_repository(repository, tag="latest"),
            port_mappings=[ecs.PortMapping(container_port=8000)]
        )

        # Create a Fargate service
        service = ecs.FargateService(
            self, "WaterbotFargateService",
            cluster=cluster,
            task_definition=task_definition,
            desired_count=1,
        )

