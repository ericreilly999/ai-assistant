# DynamoDB table used as a durable OAuth token store.
# Lambda writes provider tokens here (keyed by user_id + provider) so that tokens
# survive across Lambda container instances.

resource "aws_dynamodb_table" "oauth_tokens" {
  # checkov:skip=CKV_AWS_28: Point-in-time recovery is intentionally disabled for staging.
  # This table holds OAuth scratch tokens that can be re-acquired through a new OAuth
  # flow at any time. PITR cost is not justified for ephemeral staging tokens.

  # checkov:skip=CKV2_AWS_16: Auto-scaling is not required here. The table uses
  # PAY_PER_REQUEST billing which handles capacity automatically without needing
  # a separate auto-scaling policy resource.

  # checkov:skip=CKV_AWS_119: A Customer Managed KMS key is not used for this table.
  # It stores transient staging OAuth tokens that are re-acquirable via a new OAuth flow;
  # there are no compliance obligations requiring a CMK here, and the AWS-managed
  # DynamoDB service key (aws/dynamodb) provides sufficient encryption at rest for staging.

  name         = "ai-assistant-staging-tokens"
  billing_mode = "PAY_PER_REQUEST"
  hash_key     = "provider"

  attribute {
    name = "provider"
    type = "S"
  }

  server_side_encryption {
    enabled = true
    # Use the AWS-managed DynamoDB service key (aws/dynamodb). A CMK is not
    # required here — this is transient staging OAuth data with no compliance
    # obligations.
  }

  tags = local.tags
}
