output "api_endpoint" {
  value = module.api.api_endpoint
}

output "user_pool_id" {
  value = module.auth.user_pool_id
}

output "user_pool_client_id" {
  value = module.auth.app_client_id
}

output "lambda_function_name" {
  value = module.lambda.function_name
}

output "secret_arns" {
  value = module.secrets.secret_arns
}
