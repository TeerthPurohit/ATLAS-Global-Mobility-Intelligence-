"""CDK stack for the backend serving instance (ADR-014).

A single EC2 instance runs the backend + Caddy via Docker Compose --
the same shape as the already-working docker-compose.oracle.yml/
infra/Caddyfile pattern, just on AWS instead of Oracle. Deliberately not
ECS/Fargate+ALB: this is one task with no autoscaling, so Fargate's
actual selling point (elastic scaling) isn't in play, and an ALB's fixed
monthly cost roughly triples the bill for no benefit at this scale --
see ADR-014.

Deploy (from a developer machine with real AWS credentials -- never from
CI in this project, matching NycTlcDbtBuildStack's own policy):

    cd infra/cdk
    pip install -r requirements.txt
    cdk deploy NycTlcBackendServingStack \
        -c existing_oidc_provider_arn=<the ARN from NycTlcDbtBuildStack's
           deploy, if that stack is already deployed -- AWS allows only
           one GitHub OIDC provider per account>

Then: copy the CfnOutputs into the repo's GitHub Actions variables (see
.github/workflows/deploy-backend-aws.yml), point DNS at the Elastic IP,
and manually place the real .env at /opt/app/.env on the instance via
SSM Session Manager (see docs/architecture/Infrastructure.md -- a
secrets manager beyond .env is deliberately out of scope for now).
"""
from __future__ import annotations  # noqa: I001

from pathlib import Path

from aws_cdk import (
    CfnOutput,
    Duration,
    RemovalPolicy,
    Stack,
    Tags,
    aws_ec2 as ec2,
    aws_ecr as ecr,
    aws_iam as iam,
)
from constructs import Construct

# Tag used to scope the GitHub Actions role's ssm:SendCommand permission to
# exactly this instance -- mirrors NycTlcDbtBuildStack's BUILD_TAG_KEY/VALUE
# pattern for the same reason (least privilege via resource tag, not a
# hand-copied instance ID that goes stale if the instance is ever replaced).
SERVE_TAG_KEY = "Project"
SERVE_TAG_VALUE = "nyc-tlc-backend-serving"

# t4g.small: 2 vCPU / 2 GiB, Graviton (ARM64) -- cheaper per vCPU-hour than
# an equivalent x86 instance, and the backend's own dependencies (duckdb,
# xgboost, torch, pandas) all ship arm64 wheels. Sized against the actual
# measured container footprint (backend + Caddy only -- no self-hosted OSRM
# or Qdrant, see ADR-014); bump to t4g.medium if `docker stats` shows it
# doesn't fit (one-line change below).
SERVE_INSTANCE_TYPE = ec2.InstanceType.of(ec2.InstanceClass.T4G, ec2.InstanceSize.SMALL)

USER_DATA_PATH = Path(__file__).resolve().parents[1] / "aws-backend-vm" / "setup-userdata.sh"


class BackendServingStack(Stack):
    def __init__(
        self,
        scope: Construct,
        construct_id: str,
        *,
        github_org: str,
        github_repo: str,
        github_org_id: str,
        github_repo_id: str,
        existing_oidc_provider_arn: str | None = None,
        **kwargs,
    ) -> None:
        super().__init__(scope, construct_id, **kwargs)

        # ── ECR: one repository for the backend image ───────────────────
        repo = ecr.Repository(
            self,
            "BackendRepo",
            repository_name="nyc-tlc-backend",
            image_scan_on_push=True,
            lifecycle_rules=[
                ecr.LifecycleRule(
                    description="Expire untagged images after 14 days",
                    tag_status=ecr.TagStatus.UNTAGGED,
                    max_image_age=Duration.days(14),
                )
            ],
            removal_policy=RemovalPolicy.RETAIN,  # don't lose image history on stack changes
        )

        # ── Networking: default VPC, public subnet, no NAT gateway ──────
        # The instance gets a public IP directly (via the Elastic IP below)
        # and reaches Neon/Qdrant Cloud/ECR over the Internet Gateway --
        # a NAT gateway is only needed for private-subnet resources, and
        # its ~$32/mo fixed cost would roughly double this stack's bill for
        # a single stateless instance that has no reason to hide its IP.
        vpc = ec2.Vpc.from_lookup(self, "DefaultVpc", is_default=True)
        security_group = ec2.SecurityGroup(
            self,
            "BackendSecurityGroup",
            vpc=vpc,
            description="Backend serving instance -- 80/443 inbound for Caddy, no SSH port (Session Manager instead)",
            allow_all_outbound=True,
        )
        security_group.add_ingress_rule(ec2.Peer.any_ipv4(), ec2.Port.tcp(80), "HTTP (Caddy ACME challenge + redirect)")
        security_group.add_ingress_rule(ec2.Peer.any_ipv4(), ec2.Port.tcp(443), "HTTPS")

        # ── IAM role assumed by the instance ─────────────────────────────
        instance_role = iam.Role(
            self,
            "BackendInstanceRole",
            assumed_by=iam.ServicePrincipal("ec2.amazonaws.com"),
            description="Backend serving instance role (ADR-014) -- SSM Session Manager for shell access, no SSH key pair",
            managed_policies=[
                iam.ManagedPolicy.from_aws_managed_policy_name("AmazonSSMManagedInstanceCore"),
            ],
        )
        repo.grant_pull(instance_role)

        # ── EC2 instance ──────────────────────────────────────────────────
        user_data = ec2.UserData.for_linux()
        user_data.add_commands(USER_DATA_PATH.read_text())

        instance = ec2.Instance(
            self,
            "BackendInstance",
            vpc=vpc,
            vpc_subnets=ec2.SubnetSelection(subnet_type=ec2.SubnetType.PUBLIC),
            instance_type=SERVE_INSTANCE_TYPE,
            machine_image=ec2.MachineImage.latest_amazon_linux2023(cpu_type=ec2.AmazonLinuxCpuType.ARM_64),
            security_group=security_group,
            role=instance_role,
            user_data=user_data,
        )
        Tags.of(instance).add(SERVE_TAG_KEY, SERVE_TAG_VALUE)

        eip = ec2.CfnEIP(self, "BackendEip", domain="vpc", instance_id=instance.instance_id)

        # ── GitHub OIDC federation -- no long-lived AWS keys in CI ──────
        # AWS accounts allow only one GitHub OIDC provider; if
        # NycTlcDbtBuildStack (ADR-009) already created one, pass its ARN
        # via CDK context instead of creating a duplicate (same fallback
        # NycTlcDbtBuildStack itself uses).
        if existing_oidc_provider_arn:
            oidc_provider = iam.OpenIdConnectProvider.from_open_id_connect_provider_arn(
                self, "GitHubOidc", existing_oidc_provider_arn
            )
        else:
            oidc_provider = iam.OpenIdConnectProvider(
                self,
                "GitHubOidc",
                url="https://token.actions.githubusercontent.com",
                client_ids=["sts.amazonaws.com"],
            )

        github_actions_role = iam.Role(
            self,
            "GitHubActionsDeployRole",
            assumed_by=iam.WebIdentityPrincipal(
                oidc_provider.open_id_connect_provider_arn,
                conditions={
                    "StringEquals": {
                        "token.actions.githubusercontent.com:aud": "sts.amazonaws.com"
                    },
                    # GitHub's OIDC `sub` claim includes each side's immutable
                    # numeric ID (repo:ORG@ORG_ID/REPO@REPO_ID:ref:...), not
                    # just the display name -- a plain-name-only condition
                    # never matches a real token (confirmed via CloudTrail
                    # against a real failed AssumeRoleWithWebIdentity call).
                    # Get the IDs with `gh api users/<org> --jq .id` and
                    # `gh api repos/<org>/<repo> --jq .id`. Using the IDs also
                    # means this condition survives a future org/repo rename
                    # without redeploying.
                    "StringLike": {
                        "token.actions.githubusercontent.com:sub": (
                            f"repo:{github_org}@{github_org_id}/{github_repo}@{github_repo_id}:ref:refs/heads/main"
                        )
                    },
                },
            ),
            description="Assumed by .github/workflows/deploy-backend-aws.yml via OIDC -- no static AWS keys (ADR-014)",
            max_session_duration=Duration.hours(1),
        )

        repo.grant_pull_push(github_actions_role)

        github_actions_role.add_to_policy(
            iam.PolicyStatement(
                sid="SendDeployCommand",
                actions=["ssm:SendCommand"],
                resources=[
                    self.format_arn(service="ssm", resource="document", resource_name="AWS-RunShellScript"),
                    self.format_arn(service="ec2", resource="instance", resource_name=instance.instance_id),
                ],
                conditions={"StringEquals": {f"ssm:resourceTag/{SERVE_TAG_KEY}": SERVE_TAG_VALUE}},
            )
        )
        github_actions_role.add_to_policy(
            iam.PolicyStatement(
                # GetCommandInvocation/ListCommandInvocations have no
                # resource-level permissions in the SSM API -- "*" is the
                # only valid resource, same constraint the dbt-build
                # stack's DescribeInstances polling permission documents.
                sid="ReadDeployCommandResult",
                actions=["ssm:GetCommandInvocation", "ssm:ListCommandInvocations"],
                resources=["*"],
            )
        )

        CfnOutput(self, "EcrRepositoryUri", value=repo.repository_uri)
        CfnOutput(self, "InstanceId", value=instance.instance_id)
        CfnOutput(self, "ElasticIp", value=eip.attr_public_ip)
        CfnOutput(self, "GitHubActionsRoleArn", value=github_actions_role.role_arn)
        CfnOutput(self, "SecurityGroupId", value=security_group.security_group_id)
