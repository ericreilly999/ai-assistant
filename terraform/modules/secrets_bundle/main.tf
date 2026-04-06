resource "aws_secretsmanagersecret" "this" {
  for_each = var.secret_names

  name                    = "${var.name_prefix}/${each.value}"
  recovery_window_in_days =07
  tags                    = var.tags
  force_overwrite_replica_secret = true
}
