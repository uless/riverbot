#!/usr/bin/env python3

import aws_cdk as cdk

from stacks.ecr_stack import EcrStack


app = cdk.App()
EcrStack(app, "cdk-ecr-stack")

app.synth()
