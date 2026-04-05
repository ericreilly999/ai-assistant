output "guardrail_id" {
  description = "Bedrock guardrail identifier."
  value       = aws_bedrock_guardrail.this.guardrail_id
}

output "guardrail_arn" {
  description = "Bedrock guardrail ARN."
  value       = aws_bedrock_guardrail.this.guardrail_arn
}

output "guardrail_version" {
  description = "Published guardrail version number."
  value       = aws_bedrock_guardrail_version.this.version
}

