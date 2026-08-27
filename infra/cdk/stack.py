"""CDK stack for the on-demand dbt-build compute (ADR-009).

Everything here exists for one job: let GitHub Actions launch a single
EC2 instance that runs `dbt build` against S3-hosted raw parquet, uploads
the finished DuckDB warehouse file(s) back to S3, and terminates itself.
No VPC, no NAT gateway, no always-on compute -- see
docs/architecture/Infrastructure.md and rule 7 in .claude/rules.md before
adding anything to this file.

Deploy (from a developer machine with real AWS credentials -- never from
CI in this project, per the task constraints):

    cd infra/cdk
    pip install -r requirements.txt
    cdk deploy

Then copy the three CfnOutputs (bucket name, GitHub Actions role ARN,
instance profile ARN) into the repo's GitHub Actions repository
variables/secrets -- see .github/workflows/dbt-build-aws.yml.
"""
from __future__ import annotations  # noqa: I001

from aws_cdk import (
    CfnOutput,
    Duration,
    RemovalPolicy,
    Stack,
    aws_ec2 as ec2,
    aws_iam as iam,
    aws_s3 as s3,
)
from constructs import Construct

# Tag used to scope the GitHub Actions role's RunInstances/TerminateInstances
# permissions to exactly the instances this pipeline creates -- nothing else
# in the account. Keep this string in sync with scripts/aws_dbt_build_userdata.sh
# and the workflow (both reference it when tagging/looking up the instance).
BUILD_TAG_KEY = "Project"
BUILD_TAG_VALUE = "nyc-tlc-dbt-build"

# r6i.xlarge: 4 vCPU / 32 GiB RAM, memory-optimized (the "r" family). The
# 113M-row int_trips_enriched materialization is a memory-bound DuckDB
# aggregation/join workload, not compute-bound, so RAM headroom matters more
# than vCPU count here. On-demand only, for the ~30-60 min a build takes --
# not sized for anything that runs continuously.
BUILD_INSTANCE_TYPE = "r6i.xlarge"
BUILD_VOLUME_SIZE_GIB = 200  # raw parquet + DuckDB working files + spill


class DbtBuildStack(Stack):
    def __init__(
        self,
        scope: Construct,
        construct_id: str,
        *,
        github_org: str,
        github_repo: str,
        existing_oidc_provider_arn: str | None = None,
        **kwargs,
    ) -> None:
        super().__init__(scope, construct_id, **kwargs)

        # ── S3: one bucket, two prefixes with distinct purposes ────────
        # raw/      -- input, uploaded once (manually) by the developer from
        #              the local data/raw/ + data/lookup/ contents.
        # warehouse/ -- output, overwritten by every build: the finished
        #              nyc_rides.duckdb / london_cycles.duckdb + dbt target
        #              json + the _SUCCESS marker the workflow polls for.
        bucket = s3.Bucket(
            self,
            "DbtBuildBucket",
            removal_policy=RemovalPolicy.RETAIN,  # holds raw data; never auto-delete
            block_public_access=s3.BlockPublicAccess.BLOCK_ALL,
            lifecycle_rules=[
                # Raw parquet is read once per build and otherwise sits idle
                # between on-demand runs -- cheaper storage class after 30
                # days is free money, not speculative infra (still readable,
                # just billed less).
                s3.LifecycleRule(
                    id="raw-to-infrequent-access",
                    prefix="raw/",
                    transitions=[
                        s3.Transition(
                            storage_class=s3.StorageClass.INFREQUENT_ACCESS,
                            transition_after=Duration.days(30),
                        )
                    ],
                ),
            ],
        )

        # ── IAM role assumed by the EC2 build instance ──────────────────
        instance_role = iam.Role(
            self,
            "BuildInstanceRole",
            assumed_by=iam.ServicePrincipal("ec2.amazonaws.com"),
            description="Least-privilege role for the on-demand dbt-build EC2 instance (ADR-009)",
        )
        bucket.grant_read(instance_role, "raw/*")
        bucket.grant_write(instance_role, "warehouse/*")
        # Instance never calls TerminateInstances on itself -- self-termination
        # is `shutdown -h now` + InstanceInitiatedShutdownBehavior=terminate,
        # which needs zero IAM permissions.

        instance_profile = iam.CfnInstanceProfile(
            self,
            "BuildInstanceProfile",
            roles=[instance_role.role_name],
        )

        # ── Security group: outbound only, nothing listens on this box ──
        vpc = ec2.Vpc.from_lookup(self, "DefaultVpc", is_default=True)
        security_group = ec2.SecurityGroup(
            self,
            "BuildSecurityGroup",
            vpc=vpc,
            description="Outbound-only SG for the on-demand dbt-build instance -- no inbound rules, no SSH key pair",
            allow_all_outbound=True,
        )

        # ── GitHub OIDC federation -- no long-lived AWS keys in CI ──────
        if existing_oidc_provider_arn:
            # AWS accounts allow only one GitHub OIDC provider; if one
            # already exists (common if this account runs other GitHub
            # Actions -> AWS pipelines), pass its ARN via CDK context
            # instead of creating a duplicate.
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
            "GitHubActionsBuildRole",
            assumed_by=iam.WebIdentityPrincipal(
                oidc_provider.open_id_connect_provider_arn,
                conditions={
                    "StringEquals": {
                        "token.actions.githubusercontent.com:aud": "sts.amazonaws.com"
                    },
                    # Restrict to this repo's main branch and manual dispatch --
                    # matches the workflow's `on:` triggers, not every ref.
                    "StringLike": {
                        "token.actions.githubusercontent.com:sub": (
                            f"repo:{github_org}/{github_repo}:ref:refs/heads/main"
                        )
                    },
                },
            ),
            description="Assumed by .github/workflows/dbt-build-aws.yml via OIDC -- no static AWS keys (ADR-009)",
            max_session_duration=Duration.hours(2),
        )

        # RunInstances/CreateTags scoped to the resources it needs to touch;
        # the account-level EC2 API doesn't support resource ARNs for
        # image/subnet/security-group in a way that lets us drop them
        # entirely, so scope by resource type + a RequestTag condition so
        # this role can never launch anything outside this pipeline's tag.
        run_instances_condition = {"StringEquals": {f"aws:RequestTag/{BUILD_TAG_KEY}": BUILD_TAG_VALUE}}
        github_actions_role.add_to_policy(
            iam.PolicyStatement(
                sid="LaunchBuildInstance",
                actions=["ec2:RunInstances"],
                resources=[
                    self.format_arn(service="ec2", resource="instance", resource_name="*"),
                    self.format_arn(service="ec2", resource="volume", resource_name="*"),
                    self.format_arn(service="ec2", resource="network-interface", resource_name="*"),
                    self.format_arn(
                        service="ec2",
                        resource="security-group",
                        resource_name=security_group.security_group_id,
                    ),
                    self.format_arn(service="ec2", resource="subnet", resource_name="*"),
                    # AMI lookup resolves to a specific ID at deploy time; any
                    # ID is fine here since the workflow always passes the
                    # same SSM-resolved Amazon Linux 2023 AMI, not attacker input.
                    self.format_arn(service="ec2", resource="image", resource_name="*"),
                ],
                conditions=run_instances_condition,
            )
        )
        github_actions_role.add_to_policy(
            iam.PolicyStatement(
                sid="TagBuildInstance",
                actions=["ec2:CreateTags"],
                resources=[self.format_arn(service="ec2", resource="instance", resource_name="*")],
                conditions={"StringEquals": {"ec2:CreateAction": "RunInstances"}},
            )
        )
        github_actions_role.add_to_policy(
            iam.PolicyStatement(
                sid="TerminateOwnBuildInstance",
                actions=["ec2:TerminateInstances"],
                resources=[self.format_arn(service="ec2", resource="instance", resource_name="*")],
                conditions={"StringEquals": {f"ec2:ResourceTag/{BUILD_TAG_KEY}": BUILD_TAG_VALUE}},
            )
        )
        github_actions_role.add_to_policy(
            iam.PolicyStatement(
                # DescribeInstances has no resource-level permissions in the
                # EC2 API -- "*" is the only valid resource for this action.
                sid="PollBuildInstanceStatus",
                actions=["ec2:DescribeInstances"],
                resources=["*"],
            )
        )
        github_actions_role.add_to_policy(
            iam.PolicyStatement(
                sid="PassBuildInstanceRole",
                actions=["iam:PassRole"],
                resources=[instance_role.role_arn],
                conditions={"StringEquals": {"iam:PassedToService": "ec2.amazonaws.com"}},
            )
        )
        bucket.grant_read(github_actions_role, "warehouse/*")  # to poll for the _SUCCESS/_FAILURE marker

        CfnOutput(self, "BucketName", value=bucket.bucket_name)
        CfnOutput(self, "GitHubActionsRoleArn", value=github_actions_role.role_arn)
        CfnOutput(self, "InstanceProfileArn", value=instance_profile.attr_arn)
        CfnOutput(self, "SecurityGroupId", value=security_group.security_group_id)
        CfnOutput(self, "SubnetIds", value=",".join(s.subnet_id for s in vpc.public_subnets))
