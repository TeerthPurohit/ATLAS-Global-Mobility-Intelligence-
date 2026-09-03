"""Entry point for `cdk deploy` / `cdk synth`. See stack.py for what this
actually builds and why (ADR-009).

Set the GitHub org/repo via `cdk deploy -c github_org=... -c github_repo=...`
(or edit the defaults below) so the OIDC trust policy only lets *this* repo's
main-branch workflow assume the build role.
"""
import os  # noqa: I001

import aws_cdk as cdk

from backend_stack import BackendServingStack
from stack import DbtBuildStack

app = cdk.App()

_env = cdk.Environment(
    account=os.environ.get("CDK_DEFAULT_ACCOUNT"),
    region=os.environ.get("CDK_DEFAULT_REGION", "us-east-1"),
)
_github_org = app.node.try_get_context("github_org") or "CHANGE-ME"
_github_repo = app.node.try_get_context("github_repo") or "Uber-nyc-TLC-Dataset"
_existing_oidc_provider_arn = app.node.try_get_context("existing_oidc_provider_arn")

DbtBuildStack(
    app,
    "NycTlcDbtBuildStack",
    github_org=_github_org,
    github_repo=_github_repo,
    existing_oidc_provider_arn=_existing_oidc_provider_arn,
    env=_env,
)

# ADR-014. Deploy this one with `-c existing_oidc_provider_arn=<arn>` once
# NycTlcDbtBuildStack has been deployed at least once -- AWS allows only one
# GitHub OIDC provider per account, and that stack creates it first.
BackendServingStack(
    app,
    "NycTlcBackendServingStack",
    github_org=_github_org,
    github_repo=_github_repo,
    existing_oidc_provider_arn=_existing_oidc_provider_arn,
    env=_env,
)

app.synth()
