resource "aws_kms_key" "this" {
  description             = var.description
  deletion_window_in_days = var.deletion_window_in_days
  enable_key_rotation     = true

  tags = var.tags
}

resource "aws_kms_alias" "this" {
  name          = "alias/${var.name}"
  target_key_id = aws_kms_key.this.key_id
}

# Grant Lambda execution role access to the key
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
