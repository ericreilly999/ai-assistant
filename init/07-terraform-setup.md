# Terraform Setup

All infrastructure is managed by Terraform. No manual AWS console changes are allowed after initial bootstrap.

## Repository Layout

```
terraform/
  modules/
    api_gateway/
    lambda_function/
    lambda_authorizer/
    iam_role/
    cognito_user_pool/
    bedrock_guardrail/
    bedrock_prompt/
    bedrock_inference_profile/
    kms_key/
    secrets_manager_secret/
    cloudwatch_alarms/
    cloudwatch_dashboard/
    s3_bucket/
    route53_records/
    acm_certificate/
  environments/
    dev/
    staging/
    prod/
```

## Prerequisites

- Terraform 1.7+ installed.
- AWS CLI configured with credentials for the target environment.
- An S3 bucket for Terraform state already exists in the target AWS account (bootstrap step below).
- `terraform.tfvars` filled in for the target environment (see `04-environment-config.md`).

## Step 1 — Bootstrap the State Bucket (once per AWS account)

Terraform state is stored in S3 with `use_lockfile = true` (no DynamoDB required). Create the bucket manually once before the first `terraform init`:

```bash
aws s3api create-bucket \
  --bucket ai-assistant-tfstate-dev \
  --region us-east-1 \
  --create-bucket-configuration LocationConstraint=us-east-1

aws s3api put-bucket-versioning \
  --bucket ai-assistant-tfstate-dev \
  --versioning-configuration Status=Enabled

aws s3api put-bucket-encryption \
  --bucket ai-assistant-tfstate-dev \
  --server-side-encryption-configuration '{"Rules":[{"ApplyServerSideEncryptionByDefault":{"SSEAlgorithm":"AES256"}}]}'
```

Repeat with a different bucket name for `staging` and `prod`.

## Step 2 — Initialize

```bash
cd ai-assistant/terraform/environments/dev
terraform init
```

This downloads providers and sets up the remote state backend.

## Step 3 — Copy and Fill tfvars

```bash
cp terraform.tfvars.example terraform.tfvars
# Edit terraform.tfvars with your real values
```

Key values to fill in:
- `aws_account_id`
- `domain_name` (if using Route 53 / ACM)
- `bedrock_router_model_id`, `bedrock_summary_model_id`
- Secrets Manager ARNs (created after first apply)

## Step 4 — Validate

```powershell
cd ai-assistant
.\scripts\validate-terraform.ps1
```

Or manually:

```bash
cd terraform/environments/dev
terraform validate
terraform fmt -check -recursive
```

## Step 5 — Plan

```bash
cd terraform/environments/dev
terraform plan -var-file=terraform.tfvars -out=tfplan.binary
```

Review the plan carefully before applying, especially for:
- IAM policy changes
- KMS key creation / deletion
- Secrets Manager secret creation
- Lambda alias shifts

## Step 6 — Apply

```bash
terraform apply tfplan.binary
```

Note the outputs — you will need them for mobile app configuration and for filling in Secrets Manager secret values.

## Key Outputs

| Output | Used for |
|---|---|
| `api_gateway_url` | `EXPO_PUBLIC_API_BASE_URL` in mobile |
| `cognito_user_pool_id` | Mobile Cognito config |
| `cognito_client_id` | Mobile Cognito config |
| `google_oauth_secret_arn` | `GOOGLE_OAUTH_SECRET_ARN` Lambda env var |
| `microsoft_oauth_secret_arn` | `MICROSOFT_OAUTH_SECRET_ARN` Lambda env var |
| `plaid_secret_arn` | `PLAID_SECRET_ARN` Lambda env var |
| `bedrock_guardrail_id` | `BEDROCK_GUARDRAIL_ID` Lambda env var |

## Populating Secrets After First Apply

After Terraform creates the Secrets Manager secrets (with placeholder values), populate them with real credentials:

```bash
aws secretsmanager put-secret-value \
  --secret-id <google_oauth_secret_arn> \
  --secret-string '{"client_id":"...","client_secret":"...","redirect_uri":"..."}'

aws secretsmanager put-secret-value \
  --secret-id <microsoft_oauth_secret_arn> \
  --secret-string '{"client_id":"...","client_secret":"...","tenant_id":"common","redirect_uri":"..."}'

aws secretsmanager put-secret-value \
  --secret-id <plaid_secret_arn> \
  --secret-string '{"client_id":"...","secret":"...","environment":"sandbox"}'
```

## Environment Promotion

| From | To | Trigger |
|---|---|---|
| `dev` | `staging` | Release candidate tag |
| `staging` | `prod` | Manual approval in CI |

Never apply `prod` from a local workstation. All `prod` applies go through CI with a manual approval gate.

## Terraform Standards (enforced in CI)

- `required_version` is pinned in each environment root.
- All provider versions are pinned in `required_providers`.
- All resources live inside reusable modules — no bare resources in environment roots except glue.
- Naming derived from `locals`, not hardcoded strings.
- All resources have standardized tags.
- No DynamoDB state locking — `use_lockfile = true` only.
- No wildcard IAM `*` permissions except where AWS service APIs require constrained service wildcards.
