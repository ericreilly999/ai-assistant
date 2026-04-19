# Deployment Log

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
