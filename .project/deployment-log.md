# Deployment Log

## 2026-04-19 — Staging Environment Bootstrap (non-deployment infrastructure setup)

**Type:** Environment bootstrap — IAM role creation, GitHub environment setup, tfvars creation
**Branch:** feature/staging-pipeline
**PR:** #31
**Author:** DevOps Engineer

### Actions Taken

1. Inspected dev IAM role `ai-assistant-github-actions-deploy` to capture exact trust policy and inline `deploy-permissions` policy.

2. Created AWS IAM role `ai-assistant-github-actions-deploy-staging`:
   - ARN: `arn:aws:iam::290993374431:role/ai-assistant-github-actions-deploy-staging`
   - OIDC trust scoped to `repo:ericreilly999/ai-assistant:environment:staging` (StringLike, single environment — tighter than dev role which also allows `ref:refs/heads/main`)
   - Inline policy `deploy-permissions` attached: identical to dev role (Lambda, ApiGateway, Cognito, SecretsManager, KMS, IAM, CloudWatch, Bedrock, TfStateBucket, CognitoDomain)
   - Tags: `Project=ai-assistant`, `Environment=staging`, `ManagedBy=terraform-bootstrap`

3. Created GitHub environment `staging` on repo `ericreilly999/ai-assistant`.
   - Secrets set: `AWS_DEPLOY_ROLE_ARN`, `TF_BACKEND_BUCKET`
   - Variables set: `AWS_REGION`, `MOCK_PROVIDER_MODE`, `TF_CORS_ORIGINS`, `TF_CALLBACK_URLS`, `TF_LOGOUT_URLS`, `TF_BEDROCK_MODEL_ID`, `TF_COGNITO_DOMAIN`

4. Created `terraform/environments/staging/terraform.tfvars` with staging values.
   - CORS: `["*"]` (no custom domain yet)
   - Callback/logout URLs: `["ai-assistant://"]` (mobile app, same as dev)
   - Cognito domain: `ai-assistant-staging`

5. Committed and pushed `terraform.tfvars` on `feature/staging-pipeline`; opened PR #31 for code review.

### Verification

| Check | Result |
|-------|--------|
| IAM role ARN exists | PASS — `arn:aws:iam::290993374431:role/ai-assistant-github-actions-deploy-staging` |
| Trust policy sub condition | PASS — `repo:ericreilly999/ai-assistant:environment:staging` |
| Inline policy Sids (10 statements) | PASS — Lambda, ApiGateway, Cognito, SecretsManager, KMS, IAM, CloudWatch, Bedrock, TfStateBucket, CognitoDomain |
| GitHub environment created | PASS — staging environment exists |
| GitHub secrets (2) | PASS — `AWS_DEPLOY_ROLE_ARN`, `TF_BACKEND_BUCKET` |
| GitHub variables (7) | PASS — all 7 variables confirmed via API |
| terraform.tfvars committed | PASS — PR #31 |

### Notes / Follow-ups

- The dev IAM role trust policy uses `StringLike` with two conditions (environment:* and ref:refs/heads/main). The staging role uses a single exact `environment:staging` subject — tighter trust surface, no branch-level bypass.
- When a custom staging domain is provisioned, update `TF_CORS_ORIGINS`, `TF_CALLBACK_URLS`, `TF_LOGOUT_URLS` on the GitHub staging environment, and update `terraform.tfvars` accordingly.
- No protection rules added to the GitHub staging environment (no required reviewers). Add if desired before first production promotion gate.


## 2026-04-18 — PR #25 Branch Maintenance (fix/checkov-findings)

**Type:** Branch maintenance (rebase + code fix — not a deploy to environment)
**Branch:** fix/checkov-findings
**Commit:** 9a3ebdd
**Author:** DevOps Engineer

### Actions Taken

1. Rebased `fix/checkov-findings` onto current `main` (which included PRs #23 and #24).
   - Resolved conflict in `terraform/modules/http_api/main.tf`: restored `kms_key_id = var.kms_key_arn` on the API Gateway access log group (CKV_AWS_158 fix; PR #23 had dropped it as a side-effect).
   - Resolved conflict in `terraform/environments/dev/dynamodb.tf`: kept PR #25's `checkov:skip=CKV_AWS_119` annotation.

2. Wired KMS decrypt permissions to Lambda execution role:
   - Added `aws_iam_role_policy.kms_decrypt` resource to `terraform/modules/lambda_service/main.tf`, gated on `var.kms_key_arn != null`. Grants `kms:Decrypt`, `kms:GenerateDataKey*`, `kms:DescribeKey` scoped to the exact key ARN (satisfies CKV_AWS_356).
   - Root cause: `AWSLambdaBasicExecutionRole` does not include KMS actions. Lambda env vars encrypted with the CMK (`kms_key_arn` set in all three environments) would fail to decrypt at runtime without these permissions.
   - The `aws_kms_grant.lambda` in the `kms_key` module is an alternative mechanism but was never wired (no environment passes `lambda_role_arn`). Added comment explaining the inline IAM policy is the active path.

3. Added `role_arn` output to `terraform/modules/lambda_service/outputs.tf`.

4. Fixed staging KMS `deletion_window_in_days` from 10 to 30 (to match prod).

### Validation Results

| Environment | terraform validate | Checkov (0 failures) |
|-------------|-------------------|----------------------|
| dev         | PASS              | 78 passed, 0 failed  |
| staging     | PASS              | 77 passed, 0 failed  |
| prod        | PASS              | 77 passed, 0 failed  |

Checkov skip flags applied (same as CI): `CKV_AWS_272,CKV_AWS_116,CKV_AWS_50`

### Force Push
Remote branch `fix/checkov-findings` force-pushed: `34888f7 -> 9a3ebdd`
