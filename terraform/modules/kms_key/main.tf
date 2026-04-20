data "aws_caller_identity" "current" {}
data "aws_region" "current" {}

# CKV2_AWS_64: explicit key policy — denies all if no policy is attached and grants
# the owning account root full control so that IAM policies can further delegate access.
data "aws_iam_policy_document" "key_policy" {
  # checkov:skip=CKV_AWS_109:KMS key policies must use resources = ["*"] — AWS requires
  # the resource element in a key policy to be "*" because the policy is scoped to the key
  # it is attached to; a more-specific ARN is not possible here. IAM condition keys and
  # principal scoping are the correct constraints for key policies (AWS docs: Key policy format).
  # checkov:skip=CKV_AWS_111:Same reason as CKV_AWS_109 — resources = ["*"] is required
  # by the KMS key policy syntax and does not grant cross-resource write access.
  # checkov:skip=CKV_AWS_356:Same reason as CKV_AWS_109 — the wildcard is mandatory in a
  # KMS key policy resource element and is already constrained by principal (root account only).
  statement {
    sid    = "EnableRootAccountAccess"
    effect = "Allow"

    principals {
      type        = "AWS"
      identifiers = ["arn:aws:iam::${data.aws_caller_identity.current.account_id}:root"]
    }

    actions   = ["kms:*"]
    resources = ["*"]
  }

  # CloudWatch Logs requires explicit permission in the KMS key policy to create and use
  # encrypted log groups. IAM identity policies alone are insufficient — the service
  # principal must be granted directly in the key policy (AWS docs: Encrypt log data in
  # CloudWatch Logs using AWS KMS). Scoped to the current region and account.
  statement {
    sid    = "AllowCloudWatchLogsEncryption"
    effect = "Allow"

    principals {
      type        = "Service"
      identifiers = ["logs.${data.aws_region.current.name}.amazonaws.com"]
    }

    actions = [
      "kms:Encrypt",
      "kms:Decrypt",
      "kms:ReEncrypt*",
      "kms:GenerateDataKey",
      "kms:DescribeKey"
    ]
    resources = ["*"]

    condition {
      test     = "ArnLike"
      variable = "kms:EncryptionContext:aws:logs:arn"
      values   = ["arn:aws:logs:${data.aws_region.current.name}:${data.aws_caller_identity.current.account_id}:log-group:*"]
    }
  }

  # Secrets Manager and DynamoDB require explicit permission in the KMS key policy to
  # create and use CMK-encrypted resources. IAM identity policies alone are not sufficient
  # for cross-service KMS usage when the service acts on behalf of an IAM principal.
  # Scoped to the current region via the ViaService condition.
  statement {
    sid    = "AllowAWSServiceEncryption"
    effect = "Allow"

    principals {
      type        = "AWS"
      identifiers = ["arn:aws:iam::${data.aws_caller_identity.current.account_id}:root"]
    }

    actions = [
      "kms:Encrypt",
      "kms:Decrypt",
      "kms:ReEncrypt*",
      "kms:GenerateDataKey",
      "kms:DescribeKey",
      "kms:CreateGrant"
    ]
    resources = ["*"]

    condition {
      test     = "StringEquals"
      variable = "kms:ViaService"
      values = [
        "secretsmanager.${data.aws_region.current.name}.amazonaws.com",
        "dynamodb.${data.aws_region.current.name}.amazonaws.com"
      ]
    }
  }
}

resource "aws_kms_key" "this" {
  description             = var.description
  deletion_window_in_days = var.deletion_window_in_days
  enable_key_rotation     = true
  policy                  = data.aws_iam_policy_document.key_policy.json

  tags = var.tags
}

resource "aws_kms_alias" "this" {
  name          = "alias/${var.name}"
  target_key_id = aws_kms_key.this.key_id
}

# Optional KMS grant for the Lambda execution role.
#
# NOTE: No environment currently passes lambda_role_arn so this resource is never created
# (count = 0). Lambda's ability to decrypt environment variables and write encrypted CloudWatch
# logs is instead guaranteed by the aws_iam_role_policy.kms_decrypt resource in the
# lambda_service module, which is always created when kms_key_arn is set. That inline IAM
# policy is the active enforcement path; this grant exists as an alternative mechanism for
# callers that prefer the KMS grant model over IAM policies (e.g. cross-account scenarios).
resource "aws_kms_grant" "lambda" {
  count             = var.lambda_role_arn != null ? 1 : 0
  name              = "${var.name}-lambda-grant"
  grantee_principal = var.lambda_role_arn
  operations = [
    "Decrypt",
    "GenerateDataKey",
    "DescribeKey"
  ]
  key_id = aws_kms_key.this.id
}
