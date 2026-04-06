output "function_name" {
  value = aws_lambda_function.this.function_name
}

output "function_arn" {
  value = aws_lambda_function.this.arn
}

output "invoke_arn" {
  value = aws_lambda_function.this.invoke_arn
}

output "alias_arn" {
  value       = aws_lambda_alias.live.arn
  description = "The ARN of the live alias"
}

output "alias_name" {
  value       = aws_lambda_alias.live.name
  description = "The name of the live alias"
}
