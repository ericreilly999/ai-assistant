data "aws_iam_policy_document" "assume_role" {
  statement {
    actions = ["sts:AssumeRole"]

    principals {
      type        = "Service"
      identifiers = ["lambda.amazonaws.com"]
    }
  }
}

resource "aws_iam_role" "this" {
  name               = "${var.function_name}-role"
  assume_role_policy = data.aws_iam_policy_document.assume_role.json
  tags               = var.tags
}

resource "aws_iam_role_policy_attachment" "basic" {
  role       = aws_iam_role.this.name
  policy_arn = "arn:aws:iam::aws:policy/service-role/AWSLambdaBasicExecutionRole"
}

resource "aws_iam_role_policy_attachment" "managed" {
  for_each   = var.managed_policy_arns
  role       = aws_iam_role.this.name
  policy_arn = each.value
}

resource "aws_iam_role_policy" "additional" {
  count  = var.has_additional_policy ? 1 : 0
  name   = "${var.function_name}-additional"
  role   = aws_iam_role.this.id
  policy = var.additional_policy_json
}

resource "aws_cloudwatch_log_group" "this" {
  name = "/aws/lambda/${var.function_name}"
  # CKV_AWS_338: retain logs for at least 1 year (365 days) to satisfy compliance baseline.
  retention_in_days = 365
  # CKV_AWS_158: encrypt log group with caller-supplied KMS key when provided.
  kms_key_id = var.kms_key_arn
  tags       = var.tags
}

resource "aws_lambda_function" "this" {
  # checkov:skip=CKV_AWS_115:Reserved concurrency limit is not set — no per-function throttle target
  # has been established yet; a blanket limit without load data risks false throttling. This will be
  # revisited once p99 invocation metrics are available post-launch.
  # checkov:skip=CKV_AWS_117:Lambda is not placed inside a VPC — this is a public-facing API handler
  # that only calls AWS-managed service endpoints (Bedrock, Secrets Manager) via their public
  # regional endpoints. Adding a VPC requires NAT Gateway which adds significant cost and operational
  # complexity; deferred to post-MVP security hardening.
  function_name    = var.function_name
  role             = aws_iam_role.this.arn
  runtime          = var.runtime
  handler          = var.handler
  filename         = var.filename
  source_code_hash = var.source_code_hash
  timeout          = var.timeout
  memory_size      = var.memory_size
  publish          = true

  # CKV_AWS_173: encrypt Lambda environment variables with the caller-supplied KMS key when provided.
  kms_key_arn = var.kms_key_arn

  environment {
    variables = var.environment_variables
  }

  depends_on = [aws_cloudwatch_log_group.this]
  tags       = var.tags
}

# Create an alias pointing to the latest version for stable references
resource "aws_lambda_alias" "live" {
  name             = "live"
  description      = "Live alias pointing to the latest version of ${var.function_name}"
  function_name    = aws_lambda_function.this.function_name
  function_version = aws_lambda_function.this.version
}

# kms_key_arn is set on aws_lambda_function.this (env var encryption) and on the CloudWatch log
# group (CKV_AWS_158). AWSLambdaBasicExecutionRole does NOT include kms:Decrypt or
# kms:GenerateDataKey*, so without an explicit grant the Lambda runtime will fail to decrypt
# environment variables the moment the CMK is activated.
#
# This policy grants the minimum required KMS actions scoped to the exact key ARN, satisfying
# CKV_AWS_356 (no wildcard resource). The aws_kms_grant.lambda resource in the kms_key module
# is an alternative mechanism but is not wired from any environment — this inline policy is the
# active path.
resource "aws_iam_role_policy" "kms_decrypt" {
  count = var.has_kms_key ? 1 : 0
  name  = "${var.function_name}-kms-decrypt"
  role  = aws_iam_role.this.id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Sid    = "KMSDecryptEnvVarsAndLogs"
        Effect = "Allow"
        Action = [
          "kms:Decrypt",
          "kms:GenerateDataKey*",
          "kms:DescribeKey"
        ]
        Resource = var.kms_key_arn
      }
    ]
  })
}
