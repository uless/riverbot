from constructs import Construct
from aws_cdk import (
    Duration,
    Stack,
    aws_ecr as ecr
)


class EcrStack(Stack):

    def __init__(self, scope: Construct, construct_id: str, **kwargs) -> None:
        super().__init__(scope, construct_id, **kwargs)

        repository = ecr.Repository(self, "waterbot")


        self.exports = {
            "repository": repository
        }