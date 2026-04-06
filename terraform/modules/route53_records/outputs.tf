output "api_record_fqdn" {
  value       = try(aws_route53_record.api_gateway[0].fqdn, null)
  description = "FQDN of the API Gateway A record"
}

output "api_record_name" {
  value       = try(aws_route53_record.api_gateway[0].name, null)
  description = "Name of the API Gateway A record"
}

output "additional_records" {
  value       = { for name, record in aws_route53_record.additional : name => record.fqdn }
  description = "FQDNs of additional Route53 records"
}
