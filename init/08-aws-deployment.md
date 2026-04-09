# AWS Deployment

This guide covers deploying the application to AWS. All infrastructure is Terraform-managed. No manual console changes.

## Deployment Flow

```
merge to main
  └─> CI auto-deploys dev

release candidate tag (e.g. v1.2.0-rc1)
  └─> CI deploys staging

manual approval in CI
  └─> CI deploys prod
```

## What Gets Deployed

| Component | How |
|---|---|
| Lambda (orchestrator) | `dist/orchestrator.zip` uploaded by CI |
| Lambda (authorizer) | Packaged and uploaded separately |
| API Gateway | Terraform `api_gateway` module |
| Cognito User Pool | Terraform `cognito_user_pool` module |
| Bedrock Guardrails | Terraform `bedrock_guardrail` module |
| Bedrock Prompts | Terraform `bedrock_prompt` module |
| Bedrock Inference Profiles | Terraform `bedrock_inference_profile` module |
| Secrets Manager secrets | Terraform `secrets_manager_secret` module (empty on first apply — populate manually) |
| KMS keys | Terraform `kms_key` module |
| CloudWatch alarms and dashboards | Terraform `cloudwatch_alarms` + `cloudwatch_dashboard` modules |
| Route 53 records + ACM certificates | Terraform `route53_records` + `acm_certificate` modules |

## Manual First-Time Steps (per environment)

These steps are done once before CI takes over:

1. Create the S3 state bucket (see `07-terraform-setup.md`, Step 1).
2. Run `terraform init` and `terraform apply` locally for the first time.
3. Populate Secrets Manager secrets with real credentials (see `07-terraform-setup.md`, Populating Secrets).
4. Verify the Cognito hosted UI domain is accessible.
5. Set `EXPO_PUBLIC_API_BASE_URL` and Cognito config in the mobile app and build the first `dev` binary.

## Lambda Deployment Steps (CI-automated)

1. Run backend tests — fail fast on any test failure.
2. Run `.\scripts\package-lambda.ps1` → produces `dist/orchestrator.zip`.
3. Upload artifact to the S3 artifacts bucket.
4. Run `terraform apply` for the target environment, which updates the Lambda function code and publishes a new version.
5. The Lambda alias is shifted to the new version atomically.

## Rollback

### Lambda

Shift the Lambda alias back to the previous published version:

```bash
aws lambda update-alias \
  --function-name ai-assistant-orchestrator-dev \
  --name live \
  --function-version <previous-version-number>
```

### Infrastructure

Roll back via a previous Terraform state and re-apply:

```bash
# List state versions in S3
aws s3api list-object-versions --bucket ai-assistant-tfstate-dev --prefix dev/terraform.tfstate

# Restore a previous version (get VersionId from above)
aws s3api get-object \
  --bucket ai-assistant-tfstate-dev \
  --key dev/terraform.tfstate \
  --version-id <version-id> \
  terraform.tfstate.restored
```

## Networking

Lambdas run **outside a VPC** by default:
- No database access required (stateless design).
- No NAT gateway cost.
- Direct outbound access to Google, Microsoft, Plaid, and Bedrock.

If a compliance requirement forces VPC placement, add a NAT Gateway for outbound internet access and update the `lambda_function` module `vpc_config`.

## IAM Summary

- Each Lambda function has its own execution role.
- Least-privilege policies for: Bedrock (`InvokeModel`, `ApplyGuardrail`), Secrets Manager (`GetSecretValue`), CloudWatch (`PutMetricData`, `CreateLogGroup`, `CreateLogStream`, `PutLogEvents`), KMS (`Decrypt` on the CMK).
- No `*` resource wildcards in custom policies.

## Performance Targets

| Metric | Target |
|---|---|
| p95 read-only request latency | < 8 seconds |
| p95 write-plan request latency | < 10 seconds |
| p95 execute request latency | < 6 seconds |

Provisioned concurrency should only be added if cold-start impact is measured and justified by usage patterns.

## Alarms (prod and staging)

- 5xx error rate above threshold
- Lambda duration above threshold
- Lambda throttles
- Bedrock invocation failures
- External provider error surge
- p95 latency above target

Alarms are configured in the Terraform `cloudwatch_alarms` module per environment.

## Logging Rules

**Never log:**
- OAuth access tokens or refresh tokens
- Plaid access tokens
- Raw document content (except in `dev` with explicit flag)
- Unredacted PII

**Always log:**
- `request_id`
- `user_id` (hashed)
- Route
- Provider
- Action type
- Latency
- Success/failure status code
