#!/usr/bin/env python3

import aws_cdk as cdk

from stacks.ecr_stack import EcrStack
from stacks.app_stack import AppStack

app = cdk.App()

# Get the context value
context_value = app.node.try_get_context("env")

stacks = {
    "cdk-ecr-stack": "cdk-ecr-stack" + ("-" + context_value if context_value else ""),
    "cdk-app-stack": "cdk-app-stack" + ("-" + context_value if context_value else "")
}



ecr_stack = EcrStack(app, stacks["cdk-ecr-stack"])
app_stack = AppStack(app, stacks["cdk-app-stack"], imports=ecr_stack.exports )

app.synth()
