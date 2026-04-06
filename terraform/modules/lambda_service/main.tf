data "aws_iam_policy_document" "assume_role" {
  statement {
    actions = ["sts:AssumeRole"]

    principals {
      type            = "Service"
      identifiers     = ["lambda.amazonaws.com"]
    }
  }
}

resource "aws_iam_role" "this" {
  name                   = "${var.function_name}-role"
  assume_role_policy     = data.aws_iam_policy_document.assume_role.json
  tags                   = var.tags
}

resource "aws_iam_role_policy_attachment" "basic" {
  role           = aws_iam_role.this.name
  policy_arn     = "arn:aws:iam::aws:policy/service-role/AWSLambdaBasicExecutionRole"
}

resource "aws_iam_role_policy_attachment" "managed" {
  for_each       = var.managed_policy_arns
  role           = aws_iam_role.this.name
  policy_arn     = each.value
}

resource "aws_iam_role_policy" "additional" {
  count  = var.has_additional_policy ? 1 : 0
  name   = "${var.function_name}-additional"
  role   = aws_iam_role.this.id
  policy = var.additional_policy_json
}

resource "aws_cloudwatch_log_group" "this" {
  name               = "/aws/lambda/${var.function_name}"
  retention_in_days  = 14
  tags               = var.tags
}

resource "aws_lambda_function" "this" {
  function_name      = var.function_name
  role               = aws_iam_role.this.arn
  runtime            = var.runtime
  handler            = var.handler
  filename           = var.filename
  source_code_hash   = var.source_code_hash
  timeout            = var.timeout
  memory_size        = var.memory_size
  publish            = true

  environment {
    variables = var.environment_variables
  }

  depends_on = [aws_cloudwatch_log_group.this]
  tags               = var.tags
}

# Create an alias pointing to the latest version for stable references
resource "aws_lambda_alias" "live" {
  name              = "live"
  description       = "Live alias pointing to the latest version of ${var.function_name}"
  function_name     = aws_lambda_function.this.function_name
  function_version  = aws_lambda_function.this.version
}
