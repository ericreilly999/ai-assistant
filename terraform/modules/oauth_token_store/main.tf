resource "aws_dynamodb_table" "this" {
  # checkov:skip=CKV_AWS_28: Point-in-time recovery is intentionally disabled.
  # This table holds ephemeral OAuth scratch tokens that can be re-acquired through
  # a new OAuth flow at any time. PITR cost is not justified for re-acquirable tokens.

  # checkov:skip=CKV2_AWS_16: Auto-scaling is not required here. The table uses
  # PAY_PER_REQUEST billing which handles capacity automatically without needing
  # a separate auto-scaling policy resource.

  name         = "${var.name_prefix}-tokens"
  billing_mode = "PAY_PER_REQUEST"
  hash_key     = "pk"

  attribute {
    name = "pk"
    type = "S"
  }

  ttl {
    attribute_name = "expires_at"
    enabled        = true
  }

  server_side_encryption {
    enabled           = true
    kms_master_key_id = var.kms_key_arn
  }

  tags = var.tags
}
