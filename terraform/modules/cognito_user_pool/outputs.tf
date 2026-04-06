output "user_pool_id" {
  value = aws_cognito_user_pool.this.id
}

output "user_pool_arn" {
  value = aws_cognito_user_pool.this.arn
}

output "app_client_id" {
  value = aws_cognito_user_pool_client.mobile.id
}

output "cognito_domain" {
  value       = try(aws_cognito_user_pool_domain.this[0].domain, null)
  description = "Cognito hosted UI domain name"
}

output "cognito_domain_aws_account_id" {
  value       = try(aws_cognito_user_pool_domain.this[0].aws_account_id, null)
  description = "AWS account ID for Cognito domain"
}