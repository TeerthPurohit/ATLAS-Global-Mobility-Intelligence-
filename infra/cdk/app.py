"""Entry point for `cdk deploy` / `cdk synth`. See stack.py for what this
actually builds and why (ADR-009).

Set the GitHub org/repo via `cdk deploy -c github_org=... -c github_repo=...`
(or edit the defaults below) so the OIDC trust policy only lets *this* repo's
main-branch workflow assume the build role.

github_org_id/github_repo_id are the org/repo's immutable numeric GitHub
IDs -- required, no silent default, because GitHub's OIDC `sub` claim
includes them (repo:ORG@ORG_ID/REPO@REPO_ID:ref:...) and a trust policy
missing them will never match a real token (found the hard way: both
existing roles were deployed with the plain-name-only condition and every
AssumeRoleWithWebIdentity call failed -- confirmed via CloudTrail). Get
them with:
    gh api users/<org> --jq .id
    gh api repos/<org>/<repo> --jq .id
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
_github_repo = app.node.try_get_context("github_repo") or "ATLAS-Global-Mobility-Intelligence-"
_github_org_id = app.node.try_get_context("github_org_id")
_github_repo_id = app.node.try_get_context("github_repo_id")
_existing_oidc_provider_arn = app.node.try_get_context("existing_oidc_provider_arn")

if not _github_org_id or not _github_repo_id:
    raise SystemExit(
        "Pass -c github_org_id=<id> -c github_repo_id=<id> -- get them with "
        "`gh api users/<org> --jq .id` and `gh api repos/<org>/<repo> --jq .id`. "
        "No default is provided on purpose: a wrong/placeholder ID silently "
        "creates a trust policy that will never match a real GitHub Actions token."
    )

DbtBuildStack(
    app,
    "NycTlcDbtBuildStack",
    github_org=_github_org,
    github_repo=_github_repo,
    github_org_id=_github_org_id,
    github_repo_id=_github_repo_id,
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
    github_org_id=_github_org_id,
    github_repo_id=_github_repo_id,
    existing_oidc_provider_arn=_existing_oidc_provider_arn,
    env=_env,
)

app.synth()
