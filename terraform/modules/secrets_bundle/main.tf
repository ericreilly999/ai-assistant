resource "aws_secretsmanager_secret" "this" {
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
