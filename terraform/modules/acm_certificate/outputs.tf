output "certificate_arn" {
  value       = aws_acm_certificate.this.arn
  description = "ARN of the ACM certificate"
}

output "certificate_id" {
  value       = aws_acm_certificate.this.id
  description = "The ACM certificate ID"
}

output "domain_name" {
  value       = aws_acm_certificate.this.domain_name
  description = "The primary domain name of the certificate"
}

output "certificate_validation_arn" {
  value       = var.validate_certificate ? aws_acm_certificate_validation.this[0].certificate_arn : null
  description = "ARN of the validated certificate (null if validation not enabled)"
}
