# DynamoDB table used as a durable OAuth token store.
# Lambda writes provider tokens here (keyed by provider name) so that tokens
# survive across Lambda container instances — the previous /tmp/dev_tokens.json
# approach was container-local and not shared.

resource "aws_dynamodb_table" "oauth_tokens" {
  # checkov:skip=CKV_AWS_28: Point-in-time recovery is intentionally disabled.
  # This table holds ephemeral dev OAuth scratch tokens that can be re-acquired
  # through a new OAuth flow at any time. PITR cost is not justified for dev.

  # checkov:skip=CKV2_AWS_16: Auto-scaling is not required here. The table uses
  # PAY_PER_REQUEST billing which handles capacity automatically without needing
  # a separate auto-scaling policy resource.

  name         = "ai-assistant-dev-tokens"
  billing_mode = "PAY_PER_REQUEST"
  hash_key     = "provider"

  attribute {
    name = "provider"
    type = "S"
  }

  server_side_encryption {
    enabled = true
    # Use the AWS-managed DynamoDB service key (aws/dynamodb). A CMK is not
    # required here — this is transient dev OAuth data with no compliance
    # obligations. CMK overhead (cost + ops) is not warranted.
  }

  tags = local.tags
}
