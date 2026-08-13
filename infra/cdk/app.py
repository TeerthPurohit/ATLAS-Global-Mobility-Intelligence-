#!/usr/bin/env python3
"""Entry point for `cdk deploy` / `cdk synth`. See stack.py for what this
actually builds and why (ADR-009).

Set the GitHub org/repo via `cdk deploy -c github_org=... -c github_repo=...`
(or edit the defaults below) so the OIDC trust policy only lets *this* repo's
main-branch workflow assume the build role.
"""
import os

import aws_cdk as cdk

from stack import DbtBuildStack

app = cdk.App()

DbtBuildStack(
    app,
    "NycTlcDbtBuildStack",
    github_org=app.node.try_get_context("github_org") or "CHANGE-ME",
    github_repo=app.node.try_get_context("github_repo") or "Uber-nyc-TLC-Dataset",
    existing_oidc_provider_arn=app.node.try_get_context("existing_oidc_provider_arn"),
    env=cdk.Environment(
        account=os.environ.get("CDK_DEFAULT_ACCOUNT"),
        region=os.environ.get("CDK_DEFAULT_REGION", "us-east-1"),
    ),
)

app.synth()
