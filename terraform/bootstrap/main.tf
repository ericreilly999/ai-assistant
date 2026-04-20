locals {
  repo = "${var.github_org}/${var.github_repo}"
}

# ── Terraform state bucket ──────────────────────────────────────────────────

resource "aws_s3_bucket" "tfstate" {
  bucket = var.tfstate_bucket_name

  tags = {
    Project   = var.github_repo
    ManagedBy = "terraform-bootstrap"
  }
}

resource "aws_s3_bucket_versioning" "tfstate" {
  bucket = aws_s3_bucket.tfstate.id

  versioning_configuration {
    status = "Enabled"
  }
}

resource "aws_s3_bucket_server_side_encryption_configuration" "tfstate" {
  bucket = aws_s3_bucket.tfstate.id

  rule {
    apply_server_side_encryption_by_default {
      sse_algorithm = "AES256"
    }
  }
}

resource "aws_s3_bucket_public_access_block" "tfstate" {
  bucket = aws_s3_bucket.tfstate.id

  block_public_acls       = true
  block_public_policy     = true
  ignore_public_acls      = true
  restrict_public_buckets = true
}

# ── GitHub Actions OIDC role ────────────────────────────────────────────────

data "aws_caller_identity" "current" {}
data "aws_region" "current" {}

locals {
  oidc_provider_arn = "arn:aws:iam::${data.aws_caller_identity.current.account_id}:oidc-provider/token.actions.githubusercontent.com"
}

data "aws_iam_policy_document" "github_actions_trust" {
  statement {
    effect  = "Allow"
    actions = ["sts:AssumeRoleWithWebIdentity"]

    principals {
      type        = "Federated"
      identifiers = [local.oidc_provider_arn]
    }

    condition {
      test     = "StringEquals"
      variable = "token.actions.githubusercontent.com:aud"
      values   = ["sts.amazonaws.com"]
    }

    condition {
      test     = "StringLike"
      variable = "token.actions.githubusercontent.com:sub"
      values = [
        # Jobs with environment: <env> (e.g. deploy-dev uses environment: dev)
        "repo:${local.repo}:environment:*",
        # Jobs without environment (e.g. plan-only, CI on main)
        "repo:${local.repo}:ref:refs/heads/main",
      ]
    }
  }
}

resource "aws_iam_role" "github_actions" {
  name               = "${var.github_repo}-github-actions-deploy"
  assume_role_policy = data.aws_iam_policy_document.github_actions_trust.json

  tags = {
    Project   = var.github_repo
    ManagedBy = "terraform-bootstrap"
  }
}

# ── Deploy permissions policy ───────────────────────────────────────────────

data "aws_iam_policy_document" "deploy_permissions" {
  # Lambda
  statement {
    sid = "Lambda"
    actions = [
      "lambda:CreateFunction",
      "lambda:UpdateFunctionCode",
      "lambda:UpdateFunctionConfiguration",
      "lambda:DeleteFunction",
      "lambda:GetFunction",
      "lambda:GetFunctionConfiguration",
      "lambda:ListVersionsByFunction",
      "lambda:PublishVersion",
      "lambda:AddPermission",
      "lambda:RemovePermission",
      "lambda:GetPolicy",
      "lambda:TagResource",
      "lambda:UntagResource",
      "lambda:ListTags",
    ]
    resources = ["arn:aws:lambda:*:${data.aws_caller_identity.current.account_id}:function:ai-assistant-*"]
  }

  # API Gateway
  statement {
    sid = "ApiGateway"
    actions = [
      "apigateway:GET",
      "apigateway:POST",
      "apigateway:PUT",
      "apigateway:PATCH",
      "apigateway:DELETE",
      "apigateway:TagResource",
    ]
    resources = ["arn:aws:apigateway:*::*"]
  }

  # Cognito
  statement {
    sid = "Cognito"
    actions = [
      "cognito-idp:CreateUserPool",
      "cognito-idp:UpdateUserPool",
      "cognito-idp:DeleteUserPool",
      "cognito-idp:DescribeUserPool",
      "cognito-idp:CreateUserPoolClient",
      "cognito-idp:UpdateUserPoolClient",
      "cognito-idp:DeleteUserPoolClient",
      "cognito-idp:DescribeUserPoolClient",
      "cognito-idp:GetUserPoolMfaConfig",
      "cognito-idp:SetUserPoolMfaConfig",
      "cognito-idp:TagResource",
      "cognito-idp:UntagResource",
      "cognito-idp:ListTagsForResource",
    ]
    resources = ["arn:aws:cognito-idp:*:${data.aws_caller_identity.current.account_id}:userpool/*"]
  }

  # Cognito Hosted UI Domain (domain actions are not scoped to a userpool ARN)
  statement {
    sid = "CognitoDomain"
    actions = [
      "cognito-idp:CreateUserPoolDomain",
      "cognito-idp:UpdateUserPoolDomain",
      "cognito-idp:DeleteUserPoolDomain",
      "cognito-idp:DescribeUserPoolDomain",
    ]
    resources = ["*"]
  }

  # Secrets Manager
  statement {
    sid = "SecretsManager"
    actions = [
      "secretsmanager:CreateSecret",
      "secretsmanager:UpdateSecret",
      "secretsmanager:DeleteSecret",
      "secretsmanager:DescribeSecret",
      "secretsmanager:GetSecretValue",
      "secretsmanager:GetResourcePolicy",
      "secretsmanager:TagResource",
    ]
    resources = ["arn:aws:secretsmanager:*:${data.aws_caller_identity.current.account_id}:secret:ai-assistant-*"]
  }

  # IAM (scoped to project roles/policies)
  statement {
    sid = "IAM"
    actions = [
      "iam:CreateRole",
      "iam:UpdateRole",
      "iam:DeleteRole",
      "iam:GetRole",
      "iam:PassRole",
      "iam:CreatePolicy",
      "iam:DeletePolicy",
      "iam:GetPolicy",
      "iam:GetPolicyVersion",
      "iam:CreatePolicyVersion",
      "iam:DeletePolicyVersion",
      "iam:AttachRolePolicy",
      "iam:DetachRolePolicy",
      "iam:PutRolePolicy",
      "iam:DeleteRolePolicy",
      "iam:GetRolePolicy",
      "iam:ListRolePolicies",
      "iam:ListAttachedRolePolicies",
      "iam:TagRole",
      "iam:TagPolicy",
    ]
    resources = [
      "arn:aws:iam::${data.aws_caller_identity.current.account_id}:role/ai-assistant-*",
      "arn:aws:iam::${data.aws_caller_identity.current.account_id}:policy/ai-assistant-*",
    ]
  }

  # KMS — data operations (Encrypt/Decrypt/GenerateDataKey) required for Terraform
  # to create and manage KMS-encrypted resources (log groups, secrets, DynamoDB tables).
  # Management actions (CreateKey, PutKeyPolicy, etc.) are handled by the KMS statement
  # in the per-environment role policy; this covers the data plane for CI.
  statement {
    sid = "KMSDataOperations"
    actions = [
      "kms:Encrypt",
      "kms:Decrypt",
      "kms:ReEncryptFrom",
      "kms:ReEncryptTo",
      "kms:GenerateDataKey",
      "kms:GenerateDataKeyWithoutPlaintext",
      "kms:DescribeKey",
    ]
    resources = ["arn:aws:kms:*:${data.aws_caller_identity.current.account_id}:key/*"]
  }

  # CloudWatch
  statement {
    sid = "CloudWatch"
    actions = [
      "cloudwatch:PutMetricAlarm",
      "cloudwatch:DeleteAlarms",
      "cloudwatch:DescribeAlarms",
      "cloudwatch:ListTagsForResource",
      "cloudwatch:PutDashboard",
      "cloudwatch:DeleteDashboards",
      "cloudwatch:GetDashboard",
      "logs:CreateLogGroup",
      "logs:DeleteLogGroup",
      "logs:DescribeLogGroups",
      "logs:PutRetentionPolicy",
      "logs:TagLogGroup",
      "logs:ListTagsForResource",
      # Required for API Gateway v2 access logging (CreateStage with access_log_settings)
      "logs:CreateLogDelivery",
      "logs:DeleteLogDelivery",
      "logs:GetLogDelivery",
      "logs:UpdateLogDelivery",
      "logs:ListLogDeliveries",
      "logs:PutResourcePolicy",
      "logs:DescribeResourcePolicies",
      # Required for KMS-encrypted log groups
      "logs:AssociateKmsKey",
      "logs:DisassociateKmsKey",
    ]
    resources = ["*"]
  }

  # DynamoDB — required for oauth_token_store module (CreateTable, UpdateTimeToLive, etc.)
  statement {
    sid = "DynamoDB"
    actions = [
      "dynamodb:CreateTable",
      "dynamodb:DeleteTable",
      "dynamodb:DescribeTable",
      "dynamodb:DescribeContinuousBackups",
      "dynamodb:DescribeTimeToLive",
      "dynamodb:ListTagsOfResource",
      "dynamodb:TagResource",
      "dynamodb:UntagResource",
      "dynamodb:UpdateTable",
      "dynamodb:UpdateTimeToLive",
    ]
    resources = ["arn:aws:dynamodb:*:${data.aws_caller_identity.current.account_id}:table/ai-assistant-*"]
  }

  # Bedrock
  statement {
    sid = "Bedrock"
    actions = [
      "bedrock:CreateGuardrail",
      "bedrock:UpdateGuardrail",
      "bedrock:DeleteGuardrail",
      "bedrock:GetGuardrail",
      "bedrock:ListGuardrails",
      "bedrock:CreateGuardrailVersion",
      "bedrock:DeleteGuardrailVersion",
      "bedrock:ApplyGuardrail",
      "bedrock:InvokeModel",
      "bedrock:InvokeModelWithResponseStream",
      "bedrock:TagResource",
      "bedrock:UntagResource",
      "bedrock:ListTagsForResource",
    ]
    resources = ["*"]
  }

  # S3 — tfstate bucket only
  statement {
    sid = "TfStateBucket"
    actions = [
      "s3:GetObject",
      "s3:PutObject",
      "s3:DeleteObject",
      "s3:ListBucket",
    ]
    resources = [
      aws_s3_bucket.tfstate.arn,
      "${aws_s3_bucket.tfstate.arn}/*",
    ]
  }
}

resource "aws_iam_role_policy" "deploy_permissions" {
  name   = "deploy-permissions"
  role   = aws_iam_role.github_actions.id
  policy = data.aws_iam_policy_document.deploy_permissions.json
}
