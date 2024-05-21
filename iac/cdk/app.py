#!/usr/bin/env python3

import aws_cdk as cdk

from stacks.ecr_stack import EcrStack
from stacks.app_stack import AppStack

app = cdk.App()
ecr_stack = EcrStack(app, "cdk-ecr-stack")
app_stack = AppStack(app, "cdk-app-stack", imports=ecr_stack.exports )

app.synth()
