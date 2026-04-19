resource "aws_secretsmanager_secret" "this" {
  # checkov:skip=CKV2_AWS_57:Automatic rotation is not enabled — these secrets are static
  # OAuth client credentials (Google, Microsoft) and a Plaid API key that are issued by
  # third-party identity providers. Rotation requires a provider-specific Lambda rotator
  # and coordinated credential re-issuance with each provider; this is tracked as a
  # post-MVP security hardening task and does not apply to dev placeholder values.
  for_each = var.secret_names

  name                           = "${var.name_prefix}/${each.value}"
  kms_key_id                     = var.kms_key_arn
  recovery_window_in_days        = 0
  force_overwrite_replica_secret = true
  tags                           = var.tags
}

# Create secret versions with placeholder values for dev environment.
# In production, these should be rotated with real OAuth credentials.
resource "aws_secretsmanager_secret_version" "this" {
  for_each = var.secret_names

  secret_id = aws_secretsmanager_secret.this[each.value].id
  secret_string = jsonencode({
    "${replace(each.value, "-", "_")}_id"     = "dev-placeholder-${each.value}-id"
    "${replace(each.value, "-", "_")}_secret" = "dev-placeholder-${each.value}-secret"
  })
}
