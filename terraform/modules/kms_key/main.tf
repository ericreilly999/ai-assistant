data "aws_caller_identity" "current" {}

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
